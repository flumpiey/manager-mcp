# manager-mcp

[MCP](https://modelcontextprotocol.io/) server for self-hosted
[Manager.io](https://www.manager.io/) bookkeeping. Default is read-only; optional
scoped writes via `MANAGER_MCP_WRITE_SCOPES` / `MANAGER_MCP_DELETE_SCOPES`.

## Requirements

- Python >= 3.10
- Reachable Manager.io API (`MANAGER_API_URL` + `MANAGER_API_KEY`)

## Run (stdio MCP — no global install)

This is a **Python** package. The `npx` equivalent is **`uvx`** (ships with [uv](https://docs.astral.sh/uv/)).
Transport is **stdio** by default (`manager-mcp` → `mcp.run()`).

### Zero-install from this repo (`uvx --from`)

```bash
uvx --from E:/Development/manager-mcp manager-mcp
```

Cursor / Claude Desktop / any MCP host — paste into MCP config:

```json
{
  "mcpServers": {
    "manager": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "E:/Development/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

Optional scoped writes: `"MANAGER_MCP_WRITE_SCOPES": "quotes"` and optionally
`"MANAGER_MCP_DELETE_SCOPES": "quotes"`.

### Local editable (dev)

```bash
uv sync --extra dev
uv run manager-mcp
```

```json
{
  "mcpServers": {
    "manager": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "E:/Development/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:55667/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

### After publishing to PyPI

```bash
uvx manager-mcp
```

```json
"args": ["manager-mcp"]
```

`npx` only runs npm packages — skip unless you add a Node wrapper later.

## Environment

| Variable | Required | Notes |
|----------|----------|-------|
| `MANAGER_API_URL` | yes | Opaque base URL (include `/api2` when needed) |
| `MANAGER_API_KEY` | yes | Sent as `X-API-KEY`; never logged |
| `MANAGER_MCP_WRITE_SCOPES` | no | Comma-separated domains for create/update (e.g. `quotes,parties`). Empty = no writes. |
| `MANAGER_MCP_DELETE_SCOPES` | no | Comma-separated domains for delete only. Never implied by WRITE_SCOPES. |

Valid scopes: `quotes`, `orders`, `parties`, `items`, `sales`, `purchases`,
`banking`, `payroll`, `ledger`. No wildcards. Legacy `MANAGER_MCP_ALLOW_WRITES`
(and near-misses) hard-fail if set.

## Tools

| Tool | Purpose |
|------|---------|
| `list_resources` | Discovery + read-only boundary |
| `list_records` | Search/page curated collections |
| `get_record` | Fetch one record via `{path}-form/{key}` |
| `aged_receivables` | Outstanding / aging customers |
| `aged_payables` | Aging suppliers |
| `bank_balances` | Bank/cash **balances snapshot** |
| `trial_balance` | Trial balance |
| `profit_and_loss` | P&L |
| `balance_sheet` | Balance sheet |
| `tax_summary` | Tax summary |
| `create_*` / `update_*` / `delete_*` | Scoped mutations when scopes are set (see below) |

**Write tools (opt-in):** registered only for resources in enabled scopes.
Examples with `MANAGER_MCP_WRITE_SCOPES=quotes` and
`MANAGER_MCP_DELETE_SCOPES=quotes`: `create_sales_quote`, `update_sales_quote`,
`delete_sales_quote`, plus purchase twins. Other scopes follow the same pattern
(`create_customer`, `create_sales_order`, `create_journal_entry`, …). Bodies are
opaque Manager JSON; prefer GET form → modify → PUT. Client denylist blocks
tokens, tax/currency, COA account forms, email templates, etc.

**Bank dual path (intentional):** `bank_balances` answers “what are my balances?”;
`list_records`/`get_record` on `bank_accounts` answers “find account X and show
detail.”

Collections: `customers`, `suppliers`, `sales_invoices`, `purchase_invoices`,
`chart_of_accounts`, `bank_accounts`.

## Agent Skill

Companion skill: [`skills/manager-accounting/SKILL.md`](skills/manager-accounting/SKILL.md).

## Tests / CI

Offline only (respx). No live Manager required:

```bash
uv run ruff check src tests
uv run pytest
```

GitHub Actions matrix: Python 3.10 and 3.12.

## Caveats

- One process ↔ one `MANAGER_API_URL`. Multi-instance routing is out of scope.
- Multi-business disambiguation on a shared host is **unverified** — do not claim
  multi-business support until validated against a live multi-business setup.
- Vendored `src/manager_mcp/spec/api2.json` is provenance only; runtime always
  hits the live URL.

## License

MIT — see [LICENSE](LICENSE).
