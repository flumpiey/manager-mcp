<p align="center">
  <a href="https://www.manager.io/">
    <img src="docs/manager-icon.svg" alt="Manager.io" width="72" height="72">
  </a>
</p>

# manager-mcp

<!-- mcp-name: io.github.flumpiey/manager-mcp -->

**MCP server for self-hosted [Manager.io](https://www.manager.io/): ask your AI about invoices, balances, and books.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-stdio-green.svg)](https://modelcontextprotocol.io/)
[![CI](https://github.com/flumpiey/manager-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/flumpiey/manager-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/manager-mcp.svg)](https://pypi.org/project/manager-mcp/)

## What is Manager.io?

[Manager.io](https://www.manager.io/) is free, self-hosted accounting software for Windows, macOS, and Linux (also available as [Cloud Edition](https://www.manager.io/cloud-edition)). It covers sales, purchases, banking, payroll, and the full ledger, with an HTTP API (`/api2`) for automation.

This project wires that API into the [Model Context Protocol](https://modelcontextprotocol.io/) so Cursor, Claude, VS Code Copilot, and other MCP hosts can query your live books in natural language.

Useful Manager.io links:

- [Download](https://www.manager.io/download)
- [Guides](https://www.manager.io/guides)
- [Forum](https://forum.manager.io)
- [Releases](https://www.manager.io/releases)

## What this server does

Default is **read-only**. You get:

- **10 read tools** - discovery, six searchable collections, seven report shortcuts
- **Task tools (opt-in)** - intent-shaped writes such as `record_customer_payment`, `issue_sales_invoice`, `record_customer_deposit` (register when matching write scopes are set)
- **Deprecated CRUD tools** - per-resource `create_*` / `update_*` / `delete_*` still register under scopes until **0.3.0**; prefer task tools
- **`raw` escape hatch** - restores the full CRUD set for advanced use
- **Hard denylist** - access tokens, chart of accounts forms, tax/currency, email templates, and similar high-risk paths stay blocked even when writes are on

Transport is **stdio**. No HTTP server. No global install required if you use [`uv`](https://docs.astral.sh/uv/) / `uvx`.

## Branding / icons

- **stdio hosts (Cursor, Claude Desktop via `mcp.json`):** the server advertises Manager branding in MCP `serverInfo.icons` (embedded PNG data URI, plus a GitHub raw HTTPS fallback).
- **Cursor plugin:** [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) uses [`docs/manager-icon.svg`](docs/manager-icon.svg).
- **Claude Desktop Extension:** pack [`mcpb/`](mcpb/) (includes `icon.png`). See Installation → Claude Desktop below.
- **Claude.ai remote connectors:** Claude.ai ignores `serverInfo.icons` and uses the **root-domain favicon** of the connector URL. If you host a remote MCP later, serve [`docs/favicon.ico`](docs/favicon.ico) at the registrable domain root (e.g. `https://acme.com/favicon.ico` for `https://mcp.acme.com/...`).

## Requirements

- Python ≥ 3.10 (pulled in automatically by `uvx`)
- [uv](https://docs.astral.sh/uv/) (provides `uvx`)
- A reachable Manager.io API: `MANAGER_API_URL` + `MANAGER_API_KEY`

### Access token

1. In Manager, open **Settings → Access Tokens**.
2. Create a token and copy the value into `MANAGER_API_KEY`.
3. Set `MANAGER_API_URL` to your API base (desktop often `http://127.0.0.1:55667/api2`).

`manager-mcp` sends the token as the `X-API-KEY` header. Full walkthrough: [Access Tokens](https://www.manager.io/guides/access-tokens).

## Quick start

Run the [PyPI](https://pypi.org/project/manager-mcp/) package with [`uvx`](https://docs.astral.sh/uv/guides/tools/):

```bash
uvx manager-mcp
```

Paste a client config below, set `MANAGER_API_URL` / `MANAGER_API_KEY`, restart the host, then ask: *“Who owes me money?”* or *“Show bank balances.”*

From a git clone (dev): `uvx --from git+https://github.com/flumpiey/manager-mcp manager-mcp` or `uv run --directory /path/to/manager-mcp manager-mcp`.

## Installation

Configs below pull [`manager-mcp`](https://pypi.org/project/manager-mcp/) from PyPI. Leave write-scope env vars unset for read-only.

<details>
<summary><strong>Cursor</strong></summary>

**Plugin (Configure UI for URL, key, and scopes):** this repo is a Cursor plugin via [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) + root [`mcp.json`](mcp.json).

1. Symlink or copy the clone to `~/.cursor/plugins/local/manager-mcp` (Windows: `%USERPROFILE%\.cursor\plugins\local\manager-mcp`).
2. Reload the window.
3. Open **Plugins → Configure** on `manager-mcp`. Set **Manager API URL** and **Manager API key**. Leave **Write scopes** / **Delete scopes** empty for read-only, or paste a CSV such as `quotes` or `quotes,orders`.
4. Confirm the `manager` MCP server is enabled under Customize / MCP.

Marketplace listing is a separate submit at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).

**Manual `mcp.json`:** project [`.cursor/mcp.json`](.cursor/mcp.json) or user-wide `~/.cursor/mcp.json`.

From PyPI:

```json
{
  "mcpServers": {
    "manager": {
      "type": "stdio",
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Local editable (dev):

```json
{
  "mcpServers": {
    "manager": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Optional scoped writes in the `env` block:

```json
"MANAGER_MCP_WRITE_SCOPES": "quotes",
"MANAGER_MCP_DELETE_SCOPES": "quotes"
```

Restart Cursor after saving. Confirm `manager` under MCP settings.

</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

**Desktop Extension (`.mcpb`):** download [`mcpb.mcpb`](https://github.com/flumpiey/manager-mcp/releases/latest/download/mcpb.mcpb) from [GitHub Releases](https://github.com/flumpiey/manager-mcp/releases). Use v0.2.5 or later.

1. Open Claude Desktop → **Settings → Extensions**.
2. Open **Advanced settings** → **Install Extension…**
3. Select `mcpb.mcpb`. Review permissions, enter **Manager API URL** and **Manager API key**, then click **Install**.
4. Leave **Write scopes** and **Delete scopes** empty for read-only.
5. Restart Claude Desktop if tools do not appear.

Build your own bundle from a clone:

```bash
npx @anthropic-ai/mcpb pack mcpb
```

On Windows, double-click often does nothing and dragging the file into chat attaches it to the conversation instead of installing it. Use **Install Extension…** in Settings.

**Manual `mcp.json` config:** edit the Claude Desktop config, then restart the app.

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "manager": {
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Local clone:

```json
{
  "mcpServers": {
    "manager": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Claude Code</strong></summary>

Add via CLI:

```bash
claude mcp add manager --env MANAGER_API_URL=http://127.0.0.1:55667/api2 --env MANAGER_API_KEY=your-token -- uvx manager-mcp
```

Or edit `~/.claude.json` / project MCP config:

```json
{
  "mcpServers": {
    "manager": {
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>VS Code / GitHub Copilot</strong></summary>

Create [`.vscode/mcp.json`](.vscode/mcp.json) in the project root:

```json
{
  "servers": {
    "manager": {
      "type": "stdio",
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Local editable:

```json
{
  "servers": {
    "manager": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Reload the window. Open Copilot Chat and confirm the `manager` tools are available.

</details>

<details>
<summary><strong>Windsurf</strong></summary>

Edit `~/.codeium/windsurf/mcp_config.json` (macOS/Linux) or the Windsurf MCP settings UI:

```json
{
  "mcpServers": {
    "manager": {
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Restart Windsurf after saving.

</details>

<details>
<summary><strong>Zed</strong></summary>

Add under `context_servers` in Zed `settings.json` (Agent Panel → settings also works):

```json
{
  "context_servers": {
    "manager": {
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Cline</strong></summary>

Edit the Cline MCP settings file (`cline_mcp_settings.json` via the Cline MCP UI):

```json
{
  "mcpServers": {
    "manager": {
      "command": "uvx",
      "args": ["manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Continue</strong></summary>

In `.continue/config.yaml`:

```yaml
mcpServers:
  - name: manager
    command: uvx
    args:
      - manager-mcp
    env:
      MANAGER_API_URL: http://127.0.0.1:55667/api2
      MANAGER_API_KEY: your-token
```

</details>

<details>
<summary><strong>Generic / any stdio MCP host</strong></summary>

Any host that can spawn a stdio MCP server:

| Field | Value |
|-------|-------|
| Command | `uvx` |
| Args | `manager-mcp` |
| Env | `MANAGER_API_URL`, `MANAGER_API_KEY` (+ optional write scopes) |

```bash
uvx manager-mcp
```

Dev from a clone: `uv run --directory /path/to/manager-mcp manager-mcp`.

`npx` only runs npm packages. This is a Python package; use `uvx`.

</details>

## Environment

| Variable | Required | Notes |
|----------|----------|-------|
| `MANAGER_API_URL` | yes | Opaque base URL (include `/api2` when needed) |
| `MANAGER_API_KEY` | yes | Sent as `X-API-KEY`; never logged |
| `MANAGER_MCP_WRITE_SCOPES` | no | Comma-separated domains for create/update. Empty = no writes. |
| `MANAGER_MCP_DELETE_SCOPES` | no | Comma-separated domains for delete only. Never implied by WRITE_SCOPES. |

Valid scopes: `quotes`, `orders`, `parties`, `items`, `sales`, `purchases`, `banking`, `payroll`, `ledger`, `raw`. No wildcards (`*`, `all`).

**Recommended** (covers most bookkeeping without 82 tools):

```json
"MANAGER_MCP_WRITE_SCOPES": "banking,sales,parties",
"MANAGER_MCP_DELETE_SCOPES": "sales,banking"
```

Default with no scopes: **10 tools**. All nine domain scopes plus every CRUD verb: up to **82 tools**. Use `raw` only when you need the full CRUD escape hatch.

Legacy `MANAGER_MCP_ALLOW_WRITES` / `ALLOW_WRITES` / `MANAGER_MCP_WRITES` hard-fail if set. Use the scoped vars instead.

See [`.env.example`](.env.example). Prefer a secret manager for the API key in production configs.

## Write scopes and task tools

When a scope is listed in `MANAGER_MCP_WRITE_SCOPES`, the server registers **task tools** for that domain plus deprecated CRUD twins. `MANAGER_MCP_DELETE_SCOPES` enables `void_document` and `delete_*` per domain.

### Task tools (preferred)

| Tool | Scopes | Purpose |
|------|--------|---------|
| `create_customer`, `create_supplier` | parties | Single-resource party setup |
| `issue_sales_invoice` | sales | Issue invoice with inline lines |
| `issue_purchase_invoice` | purchases | Issue purchase invoice |
| `issue_quote` | quotes | Issue sales or purchase quote |
| `convert_quote_to_invoice` | quotes + sales | Convert quote to invoice |
| `record_customer_payment` | banking | Receipt + invoice allocation |
| `record_supplier_payment` | banking | Payment + invoice allocation |
| `record_expense` | payroll and/or purchases | Expense claim or purchase invoice |
| `transfer_between_accounts` | banking | Inter-account transfer |
| `post_journal_entry` | ledger | Generic journal entry |
| `void_document` | matching delete scope | Void by resource name + key |
| `record_customer_deposit` | banking | Deposit before invoice exists |
| `issue_deposit_invoice` | quotes | Deposit document (quote) |
| `apply_deposit_to_invoice` | ledger | Apply deposit via journal |

Bodies for composite tools use Manager-native JSON where noted. Clone `get_record` templates; do not invent field names.

### Deprecated CRUD (0.2.0, removed 0.3.0)

Per-resource `create_*` / `update_*` / `delete_*` still register when their domain scope is enabled. Descriptions are prefixed `[DEPRECATED in 0.2.0; use task tools]` except `create_customer` / `create_supplier`. Set `raw` in `MANAGER_MCP_WRITE_SCOPES` to register CRUD without deprecation prefixes.

| Scope | Resources (CRUD when enabled) |
|-------|-------------------------------|
| `quotes` | sales_quotes, purchase_quotes |
| `orders` | sales_orders, purchase_orders |
| `parties` | customers, suppliers |
| `items` | inventory_items, non_inventory_items |
| `sales` | sales_invoices, credit_notes, delivery_notes |
| `purchases` | purchase_invoices, debit_notes, goods_receipts |
| `banking` | receipts, payments, inter_account_transfers, bank_accounts |
| `payroll` | employees, payslips, expense_claims |
| `ledger` | journal_entries, depreciation_entries, amortization_entries |

Example with recommended scopes only:

```json
"MANAGER_MCP_WRITE_SCOPES": "banking,sales,parties",
"MANAGER_MCP_DELETE_SCOPES": "sales"
```

**Denylist (always blocked):** access-token forms, chart-of-accounts / `*-account-form` (except bank-or-cash), bank reconciliation, customer portal, starting balances, tax codes, exchange rates, currencies, custom fields/buttons, themes, email templates/settings.

## Customer deposit workflow

A **deposit is not revenue**. Money received before delivery must not be booked to an income account. Confirm tax/VAT treatment with your accountant.

1. Ensure a **Customer deposits** bank/cash account exists in Manager (Settings → Bank and Cash Accounts).
2. `record_customer_deposit` - posts cash to that account. If the account is missing, the tool returns `precondition_failed` with exact setup steps (Option A: guide only, no auto-create).
3. `issue_deposit_invoice` (optional) - quote styled as a deposit document for the customer.
4. `issue_sales_invoice` when the real invoice is raised.
5. `apply_deposit_to_invoice` - journal entry moving deposit balance to the invoice (clone an existing journal via `get_record`).

Required scopes: `banking`, `quotes` (deposit doc), `ledger` (apply), `sales` (final invoice via MCP).

## Migration from 0.1.x

- **0.2.0**: Task tools added; CRUD tools deprecated but still present under scopes.
- **0.3.0**: CRUD tools removed (except `create_customer` / `create_supplier`). Use task tools or `raw` scope.
- Update `MANAGER_MCP_WRITE_SCOPES` to the recommended narrow set above instead of enabling all domains.

## Tools

### Read tools

| Tool | Purpose | Period (`from_date` / `to_date`) |
|------|---------|----------------------------------|
| `list_resources` | Discovery; reports `read_only` + live write/delete scopes | n/a |
| `list_records` | Search/page a curated collection | n/a |
| `get_record` | Fetch one record via `{path}-form/{key}` | n/a |
| `aged_receivables` | Outstanding / aging customers | Accepted; may be unsupported on this view |
| `aged_payables` | Aging suppliers | Accepted; may be unsupported on this view |
| `bank_balances` | Bank/cash **balances snapshot** | Accepted; may be unsupported on this view |
| `trial_balance` | Trial balance | Forwarded as `fromDate` / `toDate` |
| `profit_and_loss` | P&L | Forwarded as `fromDate` / `toDate` |
| `balance_sheet` | Balance sheet | Forwarded as `fromDate` / `toDate` |
| `tax_summary` | Tax summary | Accepted; may be unsupported on this view |

Collections for `list_records` / `get_record`: `customers`, `suppliers`, `sales_invoices`, `purchase_invoices`, `chart_of_accounts`, `bank_accounts`.

`chart_of_accounts` is list/search only (no single-form GET).

**Bank dual path (intentional):** `bank_balances` answers “what are my balances?”; `list_records` / `get_record` on `bank_accounts` answers “find account X and show detail.”

### Write tools (deprecated)

Registered only for resources in enabled scopes. Prefer task tools above.

| Pattern | Requires | Notes |
|---------|----------|-------|
| `create_{stem}` | write scope | Deprecated in 0.2.0 |
| `update_{stem}` | write scope | Deprecated in 0.2.0 |
| `delete_{stem}` | delete scope | Deprecated in 0.2.0; use `void_document` |

## Agent Skill

Companion skill: [`skills/manager-accounting/SKILL.md`](skills/manager-accounting/SKILL.md).

The Cursor plugin discovers this skill from `skills/`. Without the plugin, copy or symlink that folder into your agent skills path. It tells the model to call `list_resources` first, verify after writes, and which report tools to prefer.

## Development

```bash
uv sync --extra dev
uv run manager-mcp
```

Offline tests only (respx). No live Manager required:

```bash
uv run ruff check src tests
uv run pytest
```

GitHub Actions matrix: Python 3.10 and 3.12.

## Caveats

- One process ↔ one `MANAGER_API_URL`. Multi-instance routing is out of scope.
- Multi-business disambiguation on a shared host is **unverified**. Do not claim multi-business support until validated against a live multi-business setup.
- Vendored `src/manager_mcp/spec/api2.json` is provenance only; runtime always hits the live URL.
- ChatGPT Apps need a hosted HTTP MCP endpoint. This package is stdio-only.

## License

MIT. See [LICENSE](LICENSE).
