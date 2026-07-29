<p align="center">
  <a href="https://www.manager.io/">
    <img src="docs/manager-icon.svg" alt="Manager.io" width="72" height="72">
  </a>
</p>

# manager-mcp

**MCP server for self-hosted [Manager.io](https://www.manager.io/) — ask your AI about invoices, balances, and books.**

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

- **10 read tools** — discovery, six searchable collections, seven report shortcuts
- **Optional scoped writes** — 23 resource types across 9 domains (`quotes`, `orders`, `parties`, …), enabled only when you set env scopes
- **Hard denylist** — access tokens, chart of accounts forms, tax/currency, email templates, and similar high-risk paths stay blocked even when writes are on

Transport is **stdio**. No HTTP server. No global install required if you use [`uv`](https://docs.astral.sh/uv/) / `uvx`.

## Branding / icons

- **stdio hosts (Cursor, Claude Desktop via `mcp.json`):** the server advertises Manager branding in MCP `serverInfo.icons` (embedded PNG data URI, plus a GitHub raw HTTPS fallback).
- **Cursor plugin:** [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) uses [`docs/manager-icon.svg`](docs/manager-icon.svg).
- **Claude Desktop Extension:** pack [`mcpb/`](mcpb/) (includes `icon.png`) — see Installation → Claude Desktop below.
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

**Desktop Extension (`.mcpb`, shows branded icon):** from a clone:

```bash
npx @anthropic-ai/mcpb pack mcpb
```

Install the resulting `.mcpb` (double-click, drag onto Claude Desktop, or Settings → Extensions → Install Extension). Enter API URL and key when prompted; leave write/delete scopes empty for read-only. Requires [`uv`](https://docs.astral.sh/uv/) on PATH (`mcp_config` runs `uvx`).

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

Valid scopes: `quotes`, `orders`, `parties`, `items`, `sales`, `purchases`, `banking`, `payroll`, `ledger`. No wildcards (`*`, `all`).

Legacy `MANAGER_MCP_ALLOW_WRITES` / `ALLOW_WRITES` / `MANAGER_MCP_WRITES` hard-fail if set — use the scoped vars instead.

See [`.env.example`](.env.example). Prefer a secret manager for the API key in production configs.

## Write scopes

When a scope is listed in `MANAGER_MCP_WRITE_SCOPES`, the server registers `create_*` and `update_*` for every implemented resource in that domain. `MANAGER_MCP_DELETE_SCOPES` registers `delete_*` separately.

| Scope | Resources | Tools (when enabled) |
|-------|-----------|----------------------|
| `quotes` | sales_quotes, purchase_quotes | `create/update/delete_sales_quote`, `…_purchase_quote` |
| `orders` | sales_orders, purchase_orders | `create/update/delete_sales_order`, `…_purchase_order` |
| `parties` | customers, suppliers | `create/update/delete_customer`, `…_supplier` |
| `items` | inventory_items, non_inventory_items | `create/update/delete_inventory_item`, `…_non_inventory_item` |
| `sales` | sales_invoices, credit_notes, delivery_notes | `create/update/delete_sales_invoice`, `…_credit_note`, `…_delivery_note` |
| `purchases` | purchase_invoices, debit_notes, goods_receipts | `create/update/delete_purchase_invoice`, `…_debit_note`, `…_goods_receipt` |
| `banking` | receipts, payments, inter_account_transfers | `create/update/delete_receipt`, `…_payment`, `…_inter_account_transfer` |
| `payroll` | employees, payslips, expense_claims | `create/update/delete_employee`, `…_payslip`, `…_expense_claim` |
| `ledger` | journal_entries, depreciation_entries, amortization_entries | `create/update/delete_journal_entry`, `…_depreciation_entry`, `…_amortization_entry` |

Bodies are opaque Manager-native JSON. Prefer **GET form → modify → PUT** (full-document replace). Example with only quotes enabled:

```json
"MANAGER_MCP_WRITE_SCOPES": "quotes",
"MANAGER_MCP_DELETE_SCOPES": "quotes"
```

→ `create_sales_quote`, `update_sales_quote`, `delete_sales_quote`, plus purchase twins.

**Denylist (always blocked):** access-token forms, chart-of-accounts / `*-account-form`, bank reconciliation, customer portal, starting balances, tax codes, exchange rates, currencies, custom fields/buttons, themes, email templates/settings.

## Tools

### Read tools

| Tool | Purpose | Period (`from_date` / `to_date`) |
|------|---------|----------------------------------|
| `list_resources` | Discovery; reports `read_only` + live write/delete scopes | — |
| `list_records` | Search/page a curated collection | — |
| `get_record` | Fetch one record via `{path}-form/{key}` | — |
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

### Write tools (opt-in)

Registered only for resources in enabled scopes. Pattern:

| Pattern | Requires | Notes |
|---------|----------|-------|
| `create_{stem}` | write scope | POST form path; 201 includes `Key` |
| `update_{stem}` | write scope | PUT `{form}/{key}`; full document replace |
| `delete_{stem}` | delete scope | DELETE `{form}/{key}`; write scope alone is not enough |

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
- Multi-business disambiguation on a shared host is **unverified** — do not claim multi-business support until validated against a live multi-business setup.
- Vendored `src/manager_mcp/spec/api2.json` is provenance only; runtime always hits the live URL.
- ChatGPT Apps need a hosted HTTP MCP endpoint. This package is stdio-only.

## License

MIT — see [LICENSE](LICENSE).
