# Feature Specification: Receipt Attachments

**Feature Branch**: `003-receipt-attachments`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "Let an agent attach a receipt file to an existing purchase invoice. Take over the attachment part of PR #4 (gregsteel): base64 upload only, behind the purchases write scope, with a size cap. Manager 26.8.4.3664 cannot list attachments over its API, so uploads are reported as unverified."

## Clarifications

### Session 2026-11-27

- Q: Which file sources are allowed? A: Base64 content in the tool call only. No server file paths and no URL fetch (both let a prompt-injected request read server files or internal addresses).
- Q: Manager's attachment list returns an empty body on 26.8.4.3664, so an upload cannot be read back. Ship anyway? A: Yes. The tool reports the upload as unverified and tells the user to check the invoice's Attachments tab.
- Q: Which attachment mechanism? A: The general Attachments list only. PR #4's second path, the single legacy Image field, re-posted the whole invoice form and could overwrite concurrent edits; it is dropped.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Attach a receipt to a purchase invoice (Priority: P1)

A user gives an agent a receipt file and names the purchase invoice it belongs to. The agent attaches the file to that invoice in one call.

**Why this priority**: It closes the loop between capturing an expense and its evidence in the books.

**Independent Test**: With the purchases write scope and a Manager user login configured, attach a small file to a purchase invoice, then open the invoice's Attachments tab in Manager and see the file.

**Acceptance Scenarios**:

1. **Given** the purchases write scope and a Manager user login, **When** the agent attaches a valid file to an existing purchase invoice, **Then** Manager accepts it and the tool reports the upload as unverified, with a pointer to the Attachments tab.
2. **Given** the purchases scope is not enabled, **When** tools are listed, **Then** the attachment tool does not exist, and a direct upload attempt is refused.
3. **Given** no Manager user login is configured, **When** the agent attempts an upload, **Then** the tool fails with an error that names the two missing settings.
4. **Given** the invoice key is not a valid key or the invoice does not exist, **When** the agent attempts an upload, **Then** the tool fails before sending the file.
5. **Given** Manager redirects or answers with an error page, **When** the upload completes, **Then** the tool fails and reports the observed status and redirect target, without guessing a cause and without echoing credentials.

---

### Edge Cases

- Content that is not valid base64: refuse before any request.
- A file larger than 10 MB after decoding: refuse before any request.
- An empty file or an empty file name: refuse.
- A file name with path separators: use the final name only.
- The Manager user login is wrong: Manager redirects; report the redirect, never the password.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory for this project)*

- Read-only by default: the tool exists only with the purchases write scope.
- Secrets from environment variables only: the Manager user login.
- Offline-testable: the upload is tested with mocked HTTP.

### Functional Requirements

- **FR-001**: The system MUST provide a tool that attaches a file, given as base64 content plus a file name, to an existing purchase invoice.
- **FR-002**: The tool MUST be registered only when the purchases write scope is enabled, and every upload MUST pass the same write-scope check as other purchase invoice writes.
- **FR-003**: The tool MUST refuse content that is not valid base64, is empty, or exceeds 10 MB after decoding, before any request is sent.
- **FR-004**: The tool MUST check that the invoice exists before uploading.
- **FR-005**: The tool MUST authenticate the upload with a Manager user login taken from environment settings, and MUST fail with a clear error when the login is not set.
- **FR-006**: The tool MUST treat a redirect, an error status or an HTML response as a failure, and report the observed status and redirect target only.
- **FR-007**: A successful upload MUST be reported as unverified, with a warning that Manager offers no API read-back and a pointer to the invoice's Attachments tab.
- **FR-008**: The system MUST NOT accept server file paths or URLs as a file source.

### Key Entities

- **Attachment upload**: invoice key, file name, file content, content type guessed from the name.
- **Manager user login**: username and password of a Manager user with access to the business.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A file attached through the tool appears in the invoice's Attachments tab in Manager.
- **SC-002**: With the purchases scope off, no configuration exposes the attachment tool.
- **SC-003**: Invalid content, oversize content and unknown invoices are refused with zero requests to the upload route.
- **SC-004**: No error or log line contains the Manager user password.

## Assumptions

- The upload route is internal to Manager and was confirmed on 26.8.4.3664 (self-hosted) and 26.8.27.0 (PR #4); a Manager update can change it.
- The Manager user is a dedicated, least-privilege user for the server.
- Attachments go to purchase invoices only in this version.

## Out of Scope

- Reading, listing or deleting attachments (no working API list on 26.8.4.3664).
- The legacy Image field, server file paths, URL fetch, other document types.

## Credit

Upload route, URL encoding and the attachment tool design: PR #4 by gregsteel, which ported the URL encoding from python-manager-api.
