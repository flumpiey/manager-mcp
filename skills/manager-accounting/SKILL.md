---
name: manager-accounting
description: >-
  Use when the user asks about Manager.io books, balances, customers who owe
  money, payables, bank, trial balance, P&L, balance sheet, tax, or scoped
  create/update/delete of Manager records. Always call list_resources first —
  trust read_only / write_scopes / delete_scopes from the live server.
---

# Manager.io accounting

Pairs with the **manager-mcp** MCP server.

## Discovery first

1. Call `list_resources`.
2. Trust its `read_only`, `write_scopes`, `delete_scopes`, and `boundary`.
3. Use only collections named in that response for `list_records` / `get_record`
   (includes `receipts`, `payments`, quotes, etc. when listed — not a fixed six).

## Boundary

- Empty scopes → read-only tool set (no `create_*` / `update_*` / `delete_*`).
- Mutations need `MANAGER_MCP_WRITE_SCOPES` (create/update) and/or
  `MANAGER_MCP_DELETE_SCOPES` (delete). Delete is never implied by write.
- Never attempt access-token, chart-of-accounts account forms, tax/currency
  minting, starting balances, or other denylisted paths.

## Config

- `MANAGER_API_URL` — opaque base URL (include `/api2` when required)
- `MANAGER_API_KEY` — `X-API-KEY`; never echo
- Scope CSVs must match between local `.env` and the MCP host `env` block
- If a tool says Manager is not reachable: tell the user to open Manager
  (API enabled) and retry — do not treat it as an MCP server crash

## Verify after write

For any `create_*` / `update_*`:

1. Prefer `get_record` on a **similar** existing row as a body template.
2. Mutate.
3. `get_record` the returned `Key` before treating the change as done.
4. If wrong and delete scope is enabled, `delete_*` and retry.

## Banking cheat-sheet (`banking` scope)

- MCP **rejects** empty `{}`, unknown names (`BankAccount`, etc.), and non-int
  `PaidBy` before POST — clone a `get_record` template.
- Receipts: `ReceivedIn`, `Customer`, `Date`, `PaidBy` (int), `ExchangeRate`,
  `Lines` with `Amount`, `AccountsReceivableCustomer`,
  `AccountsReceivableSalesInvoice` (and `Account` for fees/FX).
- Payments: `PaidFrom`, `Supplier`, `Date`, `Lines` (AP analogues).
- FX: AR `Amount` is base currency; Manager uses the **invoice** rate to clear
  USD — set AR in invoice-rate ZAR (or add an FX line), not bank-net alone.
- After create, check tool `warnings` (persistence diff).

## Read tools

- `list_resources`, `list_records`, `get_record`
- Reports: `aged_receivables`, `aged_payables`, `bank_balances`,
  `trial_balance`, `profit_and_loss`, `balance_sheet`, `tax_summary`

`bank_balances` (snapshot) and `bank_accounts` (collection) are both intentional.
