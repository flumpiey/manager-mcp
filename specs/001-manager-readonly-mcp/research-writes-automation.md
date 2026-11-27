# Research: Scoped writes — automation (custom buttons)

**Instance**: Malva Dev (`TEST_MANAGER_API_URL`, 2026-10-29). Paths from live OpenAPI + probes.

## API surface (v1)

| Operation | API | Path |
| ----------- | ----- | ------ |
| List | API2 | `GET /custom-buttons` → envelope key `customButtons` |
| Create | API2 | `POST /custom-button-form` |
| Read form | API2 | `GET /custom-button-form/{key}` |
| Update | API2 | `PUT /custom-button-form/{key}` |
| Delete | API2 | `DELETE /custom-button-form/{key}` |

OpenAPI on `{base}/api2` lists only the paths above. **No invoke / run / execute endpoint** was found for custom buttons on this build.

API4 `POST /api4/custom-button` exists in Manager docs but requires a `business` query parameter or `Manager-Business` header on this instance; MCP v1 uses **API2 form CRUD only** (same `X-API-KEY` as other writes).

## Form header keys (verified)

Observed on `GET /custom-button-form/{key}` after POST:

| Key | Notes |
| ----- | -------- |
| `Key`, `id`, `UniqueName` | Identity |
| `Name` | Button name |
| `text` | Display text (POST `Text` / `Name` influence stored `text`) |
| `Placement` | e.g. `"form"` |
| `Inactive` | Boolean |
| `Endpoint` | URL (POST lowercase `endpoint` persists as `Endpoint`) |
| `Html` | Markup (POST lowercase `html` → `Html`) |
| `TaxCodeEnabled`, `ProjectEnabled` | Flags on GET clones |

MCP accepts common lowercase aliases on create/update and normalises to Manager-native names before POST/PUT.

## Invoke / “use”

Custom buttons that call external URLs run in the **Manager desktop / browser** context when a user clicks them. There is **no** documented API2 POST to execute a button server-side on Malva Dev. Agents should:

- Manage definitions via `create_custom_button` / `update_custom_button` when `automation` scope is enabled.
- Rely on users or extensions to click buttons in Manager, or call the button’s `Endpoint` directly outside MCP (with appropriate auth and safety review).

## MCP hardening

1. `automation` scope required for any `custom-button` mutation (scope-gated denylist).
2. `custom-field` definition paths remain globally denylisted.
3. Unknown form keys rejected before POST; GET-after-write warnings via `diff_persisted`.

## Agent workflow

1. `list_resources` → confirm `automation` in effective write scopes for mutations.
2. `list_records(resource="custom_buttons")` → existing buttons.
3. `get_record` on a template button before create/update.
4. `create_custom_button` / `update_custom_button`; read `warnings` in the tool result.
