# Contracts: Remote HTTP Access and Read Surfaces

## Environment (HTTP mode)

| Name | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MANAGER_MCP_TRANSPORT` | no | `stdio` | `stdio` or `http`; any other value stops start-up |
| `MANAGER_MCP_HTTP_HOST` | no | `127.0.0.1` | Bind address |
| `MANAGER_MCP_HTTP_PORT` | no | `8080` | Bind port |
| `MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID` | http | none | Google OAuth client ID |
| `MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET` | http | none | Google OAuth client secret |
| `MANAGER_MCP_OAUTH_BASE_URL` | http | none | Public HTTPS URL of the proxy in front of the server |
| `MANAGER_MCP_ALLOWED_EMAILS` | http | none | Comma-separated allowlist, case-insensitive |

## HTTP routes

- `GET /health`: unauthenticated, returns `{"status": "ok"}` and nothing else.
- `/mcp`: Streamable HTTP, requires a FastMCP-issued token from the Google sign-in flow.

## Tool: `search_line_items` (read-only)

Input: `term` (string, required), `max_documents` (int, default 50, clamped to 1..50).

Output:

```json
{
  "term": "widget",
  "matches": [
    {"resource": "sales_invoices", "key": "<guid>", "lines": ["<matching line text>"]}
  ],
  "documents_scanned": 12,
  "truncated": false
}
```

## Collections

`payment_rules` and `receipt_rules` in `list_records` (no `get_record` form, no write tools).

## Annotations

Every read-only tool declares `readOnlyHint: true`.
