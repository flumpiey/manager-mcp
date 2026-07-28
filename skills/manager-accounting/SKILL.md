---
name: manager-accounting
description: >-
  Use when the user asks about Manager.io books, balances, customers who owe
  money, payables, bank, deposits, deposit invoices, trial balance, P&L,
  balance sheet, tax, or scoped create/update/delete. Always call
  list_resources first — trust read_only / write_scopes / delete_scopes.
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
- Never attempt access-token, chart-of-accounts / control-account forms,
  tax/currency minting, starting balances, or other denylisted paths.
- Bank/cash accounts (`create_bank_account`) are allowed when `banking` is in
  WRITE_SCOPES — still never create COA control accounts.

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

## Deposit invoice workflow (follow this)

Use when the user takes a **deposit** (quote styled as deposit invoice),
receives cash into a **deposit** bank/cash account, then later allocates it to
a sales invoice via **journal entry**.

Required scopes: `quotes`, `banking`, `ledger` (add `sales` if creating the
final invoice via MCP).

### 0. Resolve deposit account (mandatory first)

1. `list_records(resource="bank_accounts", term="deposit")` (also try
   "customer deposit", "deposits").
2. If none found: tell the user no deposit account is set up, recommend creating
   one (e.g. Name `Customer deposits`), and if `banking` ∈ write_scopes call
   `create_bank_account` with `{ "Name": "Customer deposits" }` (or the name
   they choose). Verify with `get_record` / list.
3. Keep the deposit account `Key` — it is `ReceivedIn` on the receipt.

### 1. Deposit invoice (quote)

1. Clone a sales quote template via `get_record` when possible.
2. `create_sales_quote` (or update) with title/description clearly
   **Deposit invoice** (and customer, amount, dates as needed).
3. This is still a **quote** in Manager — not a sales invoice.

### 2. Receive the deposit

1. `create_receipt` with:
   - `ReceivedIn` = deposit account key from step 0
   - `Customer`, `Date`, `PaidBy` (int), `Lines` (clone template; do not invent keys)
2. Check tool `warnings`. Do **not** clear the final sales invoice here unless
   the user is applying the deposit that way.

### 3. Final invoice + allocate deposit

1. Ensure the sales invoice exists (`create_sales_invoice` or user-created).
2. Clone an existing journal that allocates deposits (if any) via `get_record`
   on `journal_entries`.
3. `create_journal_entry`: move balance **out of** the deposit account and onto
   the invoice / AR (same shape as the user’s books — clone, don’t guess).
4. Verify invoice balance / deposit account with reads.

### 4. If scopes missing

If `quotes` / `banking` / `ledger` are not in `write_scopes`, tell the user
which env scopes to enable — do not invent a workaround.

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
