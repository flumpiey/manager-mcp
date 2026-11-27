# Quickstart: validate Remote HTTP Access and Read Surfaces

## Offline

```bash
uv run ruff check src tests
uv run pytest
```

Expected: all pass, including `tests/test_http_auth.py` (missing settings stop start-up, loopback default, 24-hour expiry, allowlist and unverified-email refusal, httpx logger at WARNING).

## Live read surfaces (sandbox business)

```bash
uv run pytest -m integration tests/integration/test_line_search.py
```

Expected: an invoice created with a unique line description is found by `search_line_items`, and the header `term` search does not find it.

## HTTP mode smoke (local, no Google round trip)

```bash
MANAGER_MCP_TRANSPORT=http MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID=<client-id> MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET=<client-secret> MANAGER_MCP_OAUTH_BASE_URL=https://<host> MANAGER_MCP_ALLOWED_EMAILS=<you@example.com> MANAGER_API_URL=<url> MANAGER_API_KEY=<key> uv run manager-mcp
curl -s http://127.0.0.1:8080/health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/mcp
```

Expected: `{"status":"ok"}`, then `401` for the unauthenticated MCP request. Unset `MANAGER_MCP_ALLOWED_EMAILS` and the server must exit with an error naming it.

## Not covered offline

A full Google sign-in with a real account; run it once by hand against a deployed instance before release.
