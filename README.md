# manager-mcp

Read-only [MCP](https://modelcontextprotocol.io/) server for self-hosted
[Manager.io](https://www.manager.io/) bookkeeping. Curated GET tools only — no
create/update/delete.

## Requirements

- Python >= 3.10
- Reachable Manager.io API (`MANAGER_API_URL` + `MANAGER_API_KEY`)

## Install / run

```bash
uv sync --extra dev
export MANAGER_API_URL="http://127.0.0.1:8080/api2"
export MANAGER_API_KEY="your-token"
uv run manager-mcp
```

### MCP client config (example)

```json
{
  "mcpServers": {
    "manager": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/manager-mcp", "manager-mcp"],
      "env": {
        "MANAGER_API_URL": "http://127.0.0.1:8080/api2",
        "MANAGER_API_KEY": "your-token"
      }
    }
  }
}
```

## Environment

| Variable | Required | Notes |
|----------|----------|-------|
| `MANAGER_API_URL` | yes | Opaque base URL (include `/api2` when needed) |
| `MANAGER_API_KEY` | yes | Sent as `X-API-KEY`; never logged |
| `MANAGER_MCP_ALLOW_WRITES` | no | Opt-in writes: `1`/`true`/`yes`/`on` registers `api_write` (POST/PUT/PATCH/DELETE). Unset → read-only. |

Truthy values (case-insensitive): `1`, `true`, `yes`, `on`. Anything else (or
unset) keeps the server read-only.

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
| `api_write` | POST/PUT/PATCH/DELETE (only if `MANAGER_MCP_ALLOW_WRITES` enabled) |

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
