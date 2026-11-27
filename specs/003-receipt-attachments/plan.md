# Implementation Plan: Receipt Attachments

**Branch**: `003-receipt-attachments` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

## Summary

Add one write tool, `attach_receipt_to_purchase_invoice`, that decodes base64 content, checks size and invoice, and posts the file as multipart form data to Manager's internal `new-attachment` route with HTTP Basic login. The URL builder is carried from PR #4. The upload goes through `ManagerClient`, which runs the existing `WritePolicy.authorize` check against the invoice's form path before sending.

## Technical Context

**Language/Version**: Python 3.10 to 3.14
**Primary Dependencies**: httpx (installed); no new dependency
**Testing**: pytest + respx offline
**Constraints**: 10 MB decoded cap; no read-back exists on Manager 26.8.4.3664

## Constitution Check

| Principle | Status |
| --- | --- |
| I. Read-only by default | PASS: registered only with `purchases`; upload calls `authorize` |
| II. Curated tool surface | PASS: one tool |
| III. Secrets via environment only | PASS: `MANAGER_UI_USERNAME`, `MANAGER_UI_PASSWORD`; never logged or echoed |
| IV. Offline-testable | PASS: respx tests for every branch |
| V. Open-source baseline | PASS: README and `.env.example` placeholders |

## Design

- `src/manager_mcp/attachments.py` (new): `action_url()` carried from PR #4 (`_action_url`).
- `src/manager_mcp/client.py`: `upload_attachment(invoice_key, file_name, data)`. It validates the key as a UUID, calls `policy.authorize("POST", "/purchase-invoice-form/<key>")`, reads the business name from the `/purchase-invoices` envelope, posts multipart with Basic auth and no redirects, and raises `ManagerApiError` on 3xx, 4xx, 5xx or HTML.
- `src/manager_mcp/task_tools.py`: `attach_receipt_to_purchase_invoice` (base64 decode with validation, size cap, invoice GET, upload, `unverified` envelope).
- `src/manager_mcp/server.py`: register under `purchases`.

## Project Structure

```text
src/manager_mcp/attachments.py   new
src/manager_mcp/client.py        upload_attachment
src/manager_mcp/task_tools.py    attach_receipt_to_purchase_invoice
src/manager_mcp/server.py        registration
tests/test_attachments.py        new
```

## Research

- R1: `GET /api2/attachments` returns 200 with an empty body on 26.8.4.3664; read-back is impossible (sandbox probe, 2026-11-27).
- R2: `/api2/attachment-form` keeps only `Name` and `Object`; no JSON field carries file content (sandbox probe).
- R3: The internal route answers 302 to `/` without a Manager user login, and 200 with one; the file appeared in the Attachments tab (confirmed by the user, 2026-11-27).
- R4: URL format: `<root>/new-attachment?<base64url of business name and invoice key>`, as built by PR #4's `_action_url` with field tag `\x0a`.

## Complexity Tracking

None.
