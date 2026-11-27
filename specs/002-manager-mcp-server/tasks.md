# Tasks: Remote HTTP Access and Read Surfaces

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [contracts/tools.md](contracts/tools.md)

## Phase 1: Carry the original work (credit)

- [ ] T001 Commit PR #4's Part 1 files as gregsteel's authorship: `src/manager_mcp/http_auth.py`, `tests/test_http_auth.py`, `Dockerfile`, `.dockerignore`, and the PR #4 hunks for the health route, `search_line_items`, read annotations and rules collections in `src/manager_mcp/server.py`, `src/manager_mcp/resources.py`, `tests/test_server_tools.py`, `tests/test_resources.py`; HTTP settings in `.env.example`

## Phase 2: User Story 1, remote sign-in (P1)

- [ ] T002 [US1] Default bind host to `127.0.0.1` in `src/manager_mcp/http_auth.py` (FR-004)
- [ ] T003 [US1] Set token expiry to 86400 s in `src/manager_mcp/http_auth.py` (FR-005)
- [ ] T004 [US1] Refuse tokens with unverified email in `AllowlistedGoogleProvider.verify_token` (FR-003)
- [ ] T005 [US1] Require the client secret in HTTP mode (FR-002, R5)
- [ ] T006 [US1] Keep `httpx` and `httpcore` loggers at WARNING in HTTP mode; no INFO `basicConfig` (FR-006)
- [ ] T007 [US1] Tests in `tests/test_http_auth.py` for T002 to T006
- [ ] T008 [US1] Dockerfile: non-root user, `MANAGER_MCP_HTTP_HOST=0.0.0.0` inside the image only, no secrets (FR-011)

## Phase 3: User Story 2, line-item search (P2)

- [ ] T009 [US2] `search_line_items` over six document types, both key spellings and both description fields, 50-document cap, `truncated` flag (FR-008)
- [ ] T010 [US2] Fix the PR #4 unit test and add a cap test in `tests/test_server_tools.py`
- [ ] T011 [US2] Live test `tests/integration/test_line_search.py`: create a purchase invoice with a unique line, find it, header search does not

## Phase 4: User Story 3, rules (P3)

- [ ] T012 [US3] Rules collections use the confirmed `paymentRules` and `receiptRules` keys; drop the "guess" comment (FR-009)
- [ ] T013 [US3] Test that no scope registers a write tool for either collection

## Phase 5: Polish

- [ ] T014 Every read-only tool declares `readOnlyHint: true`; test it (FR-010)
- [ ] T015 README: HTTP mode section, settings table, tool table rows, reverse proxy and loopback guidance; CHANGELOG `[Unreleased]`
- [ ] T016 Gates: `uv run ruff check src tests`, `uv run pytest`, `uv run pytest -m integration`, quickstart HTTP smoke

## Dependencies

T001 first. Phases 2 to 4 are independent after T001. T014 to T016 last.
