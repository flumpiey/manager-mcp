# Quickstart Validation: Manager.io Read-Only MCP Server

## Prerequisites

- Python 3.10+
- Reachable Manager.io instance (manual acceptance only)
- `MANAGER_API_URL` (include `/api2`, e.g. `http://127.0.0.1:55667/api2`)
- `MANAGER_API_KEY` (prefer secret manager; see `.env.example`)

## Install (local editable)

```bash
pip install -e ".[dev]"
# or: uv sync
```

## Automated (offline CI)

```bash
ruff check .
pytest
```

Expect: all tests green with **respx** mocks only — no live Manager.

Must include:

- Client GET-only / missing env errors
- Resource resolve allowlist
- Write-flag hard-fail (`MANAGER_MCP_ALLOW_WRITES` + near-misses)
- Tool set has no mutate verbs
- `list_records` truncation metadata / `get_record` path shape

## Manual MCP acceptance

1. Export `MANAGER_API_URL` and `MANAGER_API_KEY` (write flags **unset**).
2. Run `manager-mcp` (or configure MCP client with that command).
3. Call `list_resources` → curated list + read-only boundary.
4. `aged_receivables` / outstanding question path → matches books.
5. `bank_balances` then `list_records`/`get_record` on `bank_accounts` → both work.
6. Set `MANAGER_MCP_ALLOW_WRITES=1` and restart → process **fails loudly**.
7. Confirm skill: `skills/manager-accounting/SKILL.md` mentions Manager.io and read-only.

## Config failure checks

| Condition | Expected |
|-----------|----------|
| Missing URL or key | Clear config error |
| Truthy write env / near-miss | Startup/guard hard-fail |
| Bad token | Auth error, key not echoed |

## References

- Tools: [contracts/mcp-tools.md](./contracts/mcp-tools.md)
- Entities: [data-model.md](./data-model.md)
- Decisions: [research.md](./research.md)
