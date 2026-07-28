---
name: manager-accounting
description: >-
  Use when the user asks about Manager.io books, bookkeeping balances, customers
  who owe money, payables, bank balances, trial balance, P&L, balance sheet, or
  tax summary. Default is read-only; only use create/update/delete tools when
  the server has scoped write/delete envs enabled.
---

# Manager.io accounting

This skill pairs with the **manager-mcp** MCP server.

## Boundary

- Default is **read-only**.
- Mutations require `MANAGER_MCP_WRITE_SCOPES` and/or `MANAGER_MCP_DELETE_SCOPES`
  (comma-separated domains such as `quotes`). Delete is never implied by write.
- Never attempt access-token, chart-of-accounts, or other denylisted mutations.

## Config

- `MANAGER_API_URL` — opaque instance base URL (include `/api2` when required)
- `MANAGER_API_KEY` — access token (`X-API-KEY`); never echo secrets
- `MANAGER_MCP_WRITE_SCOPES` / `MANAGER_MCP_DELETE_SCOPES` — optional

## Tools

- `list_resources` — curated capabilities + read-only boundary
- `list_records` / `get_record` — six collections (incl. `bank_accounts` drill-in)
- Report shortcuts: `aged_receivables`, `aged_payables`, `bank_balances`,
  `trial_balance`, `profit_and_loss`, `balance_sheet`, `tax_summary`
- When scopes enabled: `create_*` / `update_*` / `delete_*` for implemented domains

`bank_balances` (snapshot) and `bank_accounts` (collection) are both intentional.
