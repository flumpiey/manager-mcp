---
name: manager-accounting
description: >-
  Use when the user asks about Manager.io books, bookkeeping balances, customers
  who owe money, payables, bank balances, trial balance, P&L, balance sheet, or
  tax summary. Read-only only — never create, edit, post, or delete records.
---

# Manager.io accounting (read-only)

This skill pairs with the **manager-mcp** MCP server.

## Boundary

- Default is **read-only**. Mutations require `MANAGER_MCP_ALLOW_WRITES=1`
  (or `true`/`yes`/`on`), which exposes the `api_write` tool.

## Config

- `MANAGER_API_URL` — opaque instance base URL (include `/api2` when required)
- `MANAGER_API_KEY` — access token (`X-API-KEY`); never echo secrets

## Tools

- `list_resources` — curated capabilities + read-only boundary
- `list_records` / `get_record` — six collections (incl. `bank_accounts` drill-in)
- Report shortcuts: `aged_receivables`, `aged_payables`, `bank_balances`,
  `trial_balance`, `profit_and_loss`, `balance_sheet`, `tax_summary`

`bank_balances` (snapshot) and `bank_accounts` (collection) are both intentional.
