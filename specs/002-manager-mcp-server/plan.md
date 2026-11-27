# Implementation Plan: Remote HTTP Access and Read Surfaces

**Branch**: `002-manager-mcp-server` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-manager-mcp-server/spec.md`

## Summary

Carry the HTTP transport, Google sign-in allowlist, line-item search, rules collections, read-only annotations and container packaging from PR #4 (gregsteel) across as a credited commit, then harden them: loopback bind by default, 24-hour tokens, verified-email check, no secrets in logs, capped search over six document types, a fixed search test and a non-root container. Bank feeds, the setup UI and attachments stay out (attachments go to 003).

## Technical Context

**Language/Version**: Python 3.10 to 3.14 (CI 3.10 and 3.12)
**Primary Dependencies**: fastmcp 3.4.5 (installed; `GoogleProvider`, `custom_route`, Streamable HTTP), httpx
**Storage**: none added; FastMCP's default encrypted OAuth client store in the platform data directory
**Testing**: pytest + respx offline; integration suite (`-m integration`) against the sandbox business
**Target Platform**: stdio (unchanged) and a container behind a TLS reverse proxy
**Project Type**: single Python package (MCP server)
**Performance Goals**: line-item search at most 50 form reads per call
**Constraints**: no new dependency beyond the lockfile (`tzdata` from PR #4 is not needed in Part 1)
**Scale/Scope**: single tenant, a handful of allowlisted users

## Constitution Check

| Principle | Status |
| --- | --- |
| I. Read-only by default | PASS: no write path added; rules collections have no write tools |
| II. Curated tool surface | PASS: one new tool (`search_line_items`), two curated collections |
| III. Secrets via environment only | PASS: OAuth settings from env; FR-006 adds log suppression |
| IV. Offline-testable network boundaries | PASS: auth config, search and health tested with respx and env dicts |
| V. Open-source baseline | PASS: README and `.env.example` updated with placeholders only |
| VI. (governance) | PASS |

Post-design re-check: PASS, no violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-manager-mcp-server/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/tools.md
└── tasks.md
```

### Source Code (repository root)

```text
src/manager_mcp/
├── http_auth.py        # new (from PR #4): transport config, allowlisted Google provider
├── server.py           # health route, search_line_items, read annotations, main() wiring
└── resources.py        # payment_rules, receipt_rules collections
tests/
├── test_http_auth.py   # new (from PR #4) plus hardening cases
├── test_server_tools.py
├── test_resources.py
└── integration/test_line_search.py   # new: live search on a created invoice
Dockerfile, .dockerignore, .env.example, README.md, CHANGELOG.md
```

**Structure Decision**: keep the existing single-package layout; one new module (`http_auth.py`).

## Complexity Tracking

None.
