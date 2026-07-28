# Contract: MCP Tools (`manager-mcp`)

Transport: MCP stdio via console script `manager-mcp`. All tools are **read-only**.

## Safety (non-tool)

On server init / first tool registration path:

- If `MANAGER_MCP_ALLOW_WRITES`, `ALLOW_WRITES`, or `MANAGER_MCP_WRITES` is
  set: **raise** when the trimmed value is non-empty. Explicit truthy set
  (case-insensitive): `1`, `true`, `yes`, `on`. Any other non-empty value also
  fails closed (do not start serving tools). Empty or unset → allow start.
- Registered tool names MUST NOT include create/update/delete/post/put/patch
  semantics (regression-tested).

## `list_resources`

**Input**: none (or empty object)

**Output**:

- `resources`: array of `{ name, kind, description, path? }`
- `read_only`: `true`
- `boundary`: string stating no create/edit/post/delete

## `list_records`

**Input**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `resource` | string | yes | Allowlist collection name |
| `term` | string | no | Search |
| `sort_by` | string | no | Maps to `sortBy` |
| `sort_by_desc` | bool | no | Maps to `sortByDesc` |
| `skip` | int | no | Default 0 |
| `page_size` | int | no | Default chosen in impl; capped reasonably |

**Output**: `CollectionPage` shape — `items` plus booleans `truncated` and/or
`has_more` (FR-011); agent uses these to decide whether to request another page

**Errors**: unknown resource; auth; connectivity; config missing

## `get_record`

**Input**:

| Field | Type | Required |
|-------|------|----------|
| `resource` | string | yes |
| `key` | string (GUID) | yes |

**Behavior**: `GET {base}/{collection-path}-form/{key}` per Manager sibling pattern.

**Errors**: not found; unknown resource; auth; connectivity

## Report shortcuts

Shared optional inputs (only forwarded if that report’s `date_params` non-empty):

| Field | Type | Notes |
|-------|------|-------|
| date/period fields | string | Exact names from OpenAPI for that path; omit ⇒ current/default |

| Tool | Manager role |
|------|----------------|
| `aged_receivables` | Receivables aging / outstanding |
| `aged_payables` | Payables aging |
| `bank_balances` | Bank/cash balances snapshot (intentional dual with `bank_accounts` collection) |
| `trial_balance` | Trial balance |
| `profit_and_loss` | P&L |
| `balance_sheet` | Balance sheet |
| `tax_summary` | Tax summary |

**Output**: snapshot body + `period_applied` / `period_unsupported_notice` as in data-model.

**Errors**: auth; connectivity; unavailable path; never require saved-report GUID

## Env contract

| Name | Required |
|------|----------|
| `MANAGER_API_URL` | yes |
| `MANAGER_API_KEY` | yes |
| `MANAGER_MCP_ALLOW_WRITES` | must be unset/false |
| `ALLOW_WRITES` | must be unset/false |
| `MANAGER_MCP_WRITES` | must be unset/false |

## Non-goals (contract)

- No tools for POST/PUT/PATCH/DELETE
- No saved-report GUID parameter
- No multi-instance selection
