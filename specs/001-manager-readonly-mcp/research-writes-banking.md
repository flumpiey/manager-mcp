# Research: Scoped writes — banking (receipts / payments)

**Instance**: Malva dev. Top-level receipt fields verified live 2026-07-28
(`list` + `get` form). Full `Lines[]` key inventory deferred when API was down;
agents must clone a template via `get_record`.

## Paths (OpenAPI + list GET 200)

| Resource | List | Form |
|----------|------|------|
| receipts | `GET /receipts` (`receipts`) | `POST /receipt-form`; `GET/PUT/DELETE /receipt-form/{key}` |
| payments | `GET /payments` (`payments`) | `POST /payment-form`; `GET/PUT/DELETE /payment-form/{key}` |

No PATCH on forms (same as quotes).

## Receipt form — top-level keys (VERIFIED)

`AmountsAreTaxExclusive`, `Customer`, `Date`, `Description`, `HasLineNumber`,
`Key`, `Lines`, `PaidBy`, `ReceivedIn`, `Reference`, `TaxCodeEnabled`,
`UniqueName`, `id`, `text`, plus custom-field / theme / project flags.

Notable:

- **`ReceivedIn`** — bank/cash account key (where money landed).
- **`Customer`** — payer.
- **`Lines`** — allocation lines (clear invoices / P&amp;L / bank charges).
- **`Date`**, **`Description`**, **`Reference`**, **`PaidBy`**.

## Receipt `Lines[]` (TEMPLATE-REQUIRED)

Do **not** invent line keys. Workflow:

1. `list_records` / `get_record` on a similar receipt.
2. Copy `Lines` shape; swap Account / Amount / invoice links as needed.
3. Multi-currency / FX: copy any rate or foreign-amount fields from that
   template (or from the sales invoice being cleared). Manager posts FX to
   gains/losses when the receipt rate differs from the invoice rate.

## Payments (symmetric)

List/form paths verified in OpenAPI path matrix. Expect `PaidFrom` (bank) and
supplier/payee fields instead of `ReceivedIn`/`Customer`. Same clone-from-
template rule for `Lines`.

## Agent workflow (required)

1. `list_resources` → confirm `banking` ∈ `write_scopes`.
2. `get_record(resource="receipts", key=…)` (or payments) as template.
3. `create_receipt` / `create_payment` with Manager-native JSON body.
4. `get_record` on the new `Key` before treating the post as done.
5. On mistake: `delete_receipt` only if `banking` ∈ `delete_scopes`.

## Denylist

Do not POST bank-or-cash **account** forms, starting balances, reconciliation,
or COA account forms — client denylist.
