# Vendored OpenAPI provenance

`api2.json` is a **curated provenance subset** of a live Manager.io `/api2`
OpenAPI document (validated 2026-07-28 against a desktop instance). It documents
paths that inform the allowlist in `resources.py`.

Runtime does **not** load this file. Tools always GET the live instance configured
via `MANAGER_API_URL` / `MANAGER_API_KEY`.

## Live validation notes

- Collection forms are **singular** (`/customer-form/{key}`), not `{list}-form`.
- Bank list is `/bank-and-cash-accounts`; form is `/bank-or-cash-account-form/{key}`.
- List GETs return envelopes (`{ customers: [...], totalRecords }`), not bare arrays.
- Built-in report *forms* (`/aged-receivables-form`, etc.) require **POST** (writes).
  v1 report tools use GET-only substitutes:
  - outstanding AR/AP → `/customers`, `/suppliers`
  - bank balances → `/bank-and-cash-accounts`
  - TB / P&L / BS / tax → `*-transactions` feeds (`fromDate`/`toDate` where present)
- `chart_of_accounts` list works; there is no single COA form endpoint for `get_record`.
