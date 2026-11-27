# Feature Specification: Remote HTTP Access and Read Surfaces

**Feature Branch**: `002-manager-mcp-server`

**Created**: 2026-09-22 (original, PR #4 by gregsteel); revised 2026-11-27

**Status**: Draft

**Input**: User description: "Let a remote MCP connector reach manager-mcp over the network with authenticated HTTP transport, and add read surfaces for line-item search and payment/receipt rules. Take over PR #4 and split it: this spec covers the HTTP transport, Google sign-in with an email allowlist, line-item search, rules collections and read-only tool annotations. Receipt attachments move to 003. Bank feeds are out of scope."

## Clarifications

### Session 2026-11-27

- Q: How long does a remote sign-in token last? A: 24 hours. A removed address loses access within a day, or at once on restart.
- Q: Which documents does line-item search cover? A: Purchase and sales invoices, sales and purchase quotes, and sales and purchase orders, with one document type per call and at most 50 documents per call.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remote connector signs in and uses the server (Priority: P1)

An operator runs manager-mcp as a long-lived service behind a TLS-terminating reverse proxy, so a remote MCP connector can reach it over the network. Only people on the operator's allowlist can use it.

**Why this priority**: Without network transport, a remote connector cannot reach the server at all.

**Independent Test**: Start the server in HTTP mode with sign-in configured and one allowlisted address. Sign in with that account and call a read tool; sign in with another account and confirm refusal.

**Acceptance Scenarios**:

1. **Given** the transport is unset or stdio, **When** the server starts, **Then** it behaves exactly as today and opens no network listener.
2. **Given** HTTP mode with valid sign-in settings and a non-empty allowlist, **When** an allowlisted account with a verified email signs in, **Then** its tool calls are served.
3. **Given** the same settings, **When** an account that is not on the allowlist, or whose email is unverified, signs in, **Then** every request is refused, and the refusal does not reveal which addresses are allowed.
4. **Given** HTTP mode with any sign-in setting missing, **When** the server starts, **Then** it exits with an error that names the missing setting and serves nothing.
5. **Given** HTTP mode with no bind address set, **When** the server starts, **Then** it listens on the loopback interface only.

---

### User Story 2 - Find a transaction by line-item wording (Priority: P2)

An agent needs a document whose matching text appears only in a line description, which header search misses.

**Why this priority**: A common bookkeeping question that the current header-only search cannot answer.

**Independent Test**: Search for a word that appears only in one invoice line description and confirm that invoice is returned.

**Acceptance Scenarios**:

1. **Given** a document whose line description contains the term, **When** the agent searches line items, **Then** the document is returned with the matching line.
2. **Given** no line matches, **When** the agent searches, **Then** the result is empty, not an error.
3. **Given** a request for more documents than the per-call limit, **When** the agent searches, **Then** the search is capped at the limit and the result says more may exist.

---

### User Story 3 - See existing payment and receipt rules (Priority: P3)

An agent needs to see the auto-categorisation rules that already exist before it suggests a new one.

**Why this priority**: Read-only context that prevents duplicate or conflicting rules.

**Independent Test**: List payment rules and receipt rules on a business that has rules and confirm they are returned.

**Acceptance Scenarios**:

1. **Given** rules exist, **When** the agent lists payment rules or receipt rules, **Then** the rules are returned.
2. **Given** any scope configuration, **When** tools are registered, **Then** no create, update or delete tool exists for either rules collection.

---

### Edge Cases

- HTTP mode requested without sign-in client settings, base URL or allowlist: exit at start-up, never serve unauthenticated.
- Sign-in succeeds but the email is not allowlisted or not verified: refuse; do not list allowed addresses.
- Logs must never contain access tokens, client secrets or API keys, including in request URLs logged by the HTTP library.
- Sign-in tokens expire within a bounded time, so removing an address from the allowlist takes effect without a server restart once tokens lapse.
- Line-item search over many documents: one Manager call per document, so the per-call document count is capped.
- A rules collection returns an envelope key other than the expected one: return the items found, not an error.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory for this project)*

Specs MUST respect `.specify/memory/constitution.md`:

- Read-only by default; this spec adds no write path.
- New tools are hand-curated.
- Secrets come from environment variables only.
- Tests for network I/O are offline-mockable; no live external service as a gate.

**Feature-specific hardening**: the HTTP transport is opt-in and always authenticated; it binds to loopback unless the operator sets an address; logging never records secrets.

### Functional Requirements

- **FR-001**: The system MUST support Streamable HTTP transport when the operator selects it, in addition to the default stdio transport.
- **FR-002**: In HTTP mode the system MUST require Google sign-in client settings, a public base URL and a non-empty email allowlist, and MUST exit at start-up when any is missing.
- **FR-003**: The system MUST refuse any request from an account whose email is not on the allowlist or is not verified by the identity provider.
- **FR-004**: The HTTP listener MUST bind to the loopback interface unless the operator sets a bind address.
- **FR-005**: Issued sign-in tokens MUST expire within 24 hours.
- **FR-006**: The system MUST NOT write access tokens, client secrets or API keys to logs, including URLs logged by the HTTP client library.
- **FR-007**: The system MUST expose an unauthenticated health check that reveals no configuration or business data.
- **FR-008**: The system MUST provide a read-only line-item search over purchase and sales invoices, quotes and orders, one document type per call, that matches the term against line descriptions, capped at 50 documents per call.
- **FR-009**: The system MUST expose payment rules and receipt rules as list-only collections with no write tools under any scope.
- **FR-010**: Every read-only tool MUST declare the MCP read-only annotation.
- **FR-011**: The project MUST ship container packaging that runs the server as a non-root user with no secrets in the image.

### Key Entities

- **HTTP session**: an authenticated remote connection, gated by Google sign-in plus the email allowlist.
- **Email allowlist**: the operator's list of addresses that may use the server.
- **Categorisation rule**: a payment or receipt rule; read-only here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In HTTP mode, 100% of requests from non-allowlisted or unverified accounts are refused, and allowlisted accounts are served.
- **SC-002**: With HTTP mode on and any required setting missing, the server never accepts a connection.
- **SC-003**: A log capture over a full sign-in and tool-call session contains zero tokens, secrets or keys.
- **SC-004**: Line-item search returns a document whose only match is in a line description, where header search returns nothing.
- **SC-005**: No scope configuration registers a write tool for either rules collection.
- **SC-006**: Every read-only tool reports the read-only annotation.

## Assumptions

- A reverse proxy terminates TLS in front of the server; the server does not.
- One deployment serves one business (single tenant); the allowlist is not multi-tenant access control.
- Google is the only identity provider in this version.
- The allowlist is read at start-up; changing it requires a restart, and existing tokens lapse within 24 hours (FR-005).

## Out of Scope

- Receipt attachments (see 003).
- Bank-feed ingestion, the Basiq provider and the setup web UI from PR #4 (dropped: depends on an unsupported third-party integration).
- The PR #4 change that makes `update_*` tools merge onto the existing record (separate concern).
- Non-Google identity providers and multi-tenant access.

## Credit

Original design and implementation: PR #4 by gregsteel. This spec narrows and hardens that work.
