# Tasks: Receipt Attachments

**Input**: [plan.md](plan.md), [spec.md](spec.md)

- [x] T001 Carry `_action_url` from PR #4 into `src/manager_mcp/attachments.py` (credit gregsteel)
- [x] T002 `ManagerClient.upload_attachment`: UUID check, `authorize`, business name, Basic login, no redirects, error on 3xx/4xx/5xx/HTML (FR-002, FR-005, FR-006)
- [x] T003 `attach_receipt_to_purchase_invoice` task: strict base64, empty and 10 MB checks, invoice GET, upload, `unverified` envelope (FR-001, FR-003, FR-004, FR-007, FR-008)
- [x] T004 Register the tool under `purchases` in `src/manager_mcp/server.py` (FR-002)
- [x] T005 `tests/test_attachments.py`: URL bytes, Basic header, scope refusal, missing login, bad base64, oversize, unknown invoice, redirect error without password, success envelope
- [x] T006 README tool row, settings rows and limits; `.env.example`; CHANGELOG `[Unreleased]`
- [x] T007 Gates: ruff, pytest, integration suite; one live upload by hand (an automated live test would leave attachments it cannot delete)
