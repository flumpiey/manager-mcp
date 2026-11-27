# Changelog

All notable changes to this project are documented in this file.

## [0.2.7] - 2026-10-29

### Added

- `automation` write/delete scope for custom buttons (API2 `/custom-buttons`,
  `/custom-button-form`) with field validation and persistence warnings.

### Changed

- Custom button paths are no longer globally denylisted; they require the
  `automation` scope instead. Custom field definition paths remain blocked.
- `record_customer_deposit` matches a bank/cash account named exactly
  "Customer deposits" (was: any name containing "deposit").
- `record_expense` raises when `via` names a route whose scope is missing,
  and rejects unknown `via` values.
- Write errors raise instead of returning `partial` with no key. A failed
  read-back after a save returns a warning with the saved key.

### Fixed

- `record_supplier_payment` sent `Payee=1` (customer) by default; now `2`.
- Supplier payments resolve Accounts payable from the chart of accounts first,
  and only reuse a past payment line that carries `AccountsPayableSupplier`.
- Record keys containing `.`, `..`, `%` or `\` path segments are rejected
  before any request.
- `server.json` and the mcpb manifest now carry the package version.

### Removed

- Unused API4 client helper (`MANAGER_API4_URL`, `MANAGER_BUSINESS_NAME`).
- One-off probe and smoke scripts under `scripts/`.

## [0.2.6] - 2026-08-03

### Fixed

- Claude Desktop runtime: use `uv tool run manager-mcp` in mcpb mcp_config.
  Claude maps `server.type: uv` to `uv.exe` and was running `uv manager-mcp`
  instead of `uvx manager-mcp`.

## [0.2.5] - 2026-08-03

### Fixed

- Claude Desktop extension install on Windows: drop manager-mcp from mcpb
  pyproject dependencies (install ran uv sync and failed on cffi without win
  wheels). Runtime still uses uvx; add mcpb/.mcpbignore for .venv and uv.lock.

## [0.2.4] - 2026-08-03

### Fixed

- Claude Desktop extension: migrate MCPB to manifest 0.4 / `uv` server type and drop
  system Python runtime check (uses `uvx`; only requires `uv` on PATH)

## [0.2.3] - 2026-08-03

### Added

- Claude Desktop extension pack (`mcpb.mcpb`) for one-click install via Claude Desktop
- Serena project config (`.serena/`) for symbol-aware agent editing

### Changed

- Refactor: reduce complexity from ponytail audit (-56 lines)

### Fixed

- CI: resolve ruff lint failures from refactor commit (F401, I001, E501)

## [0.2.0] - 2026-07-29

### Added

- 13 intent-shaped task tools replacing generated CRUD as the recommended write path
- Customer deposit workflow (`record_customer_deposit`, `issue_deposit_invoice`, `apply_deposit_to_invoice`)
- `PreconditionResult` pattern for structured setup guidance when instance preconditions fail
- `raw` escape-hatch scope restoring the full CRUD set for advanced use
- `server.json` for MCP Registry discoverability
- Explicit `[tool.hatch.build.targets.sdist]` include list
- Live sandbox integration test suite (`pytest -m integration`, `TEST_MANAGER_API_*` env vars)

### Changed

- `pyproject.toml` description reflects read-first with opt-in scoped writes
- `skills/manager-accounting/SKILL.md`: task tool guidance, deposit is-not-revenue statement
- `README.md`: task tool table, deposit docs, recommended scope config, migration notice

### Deprecated

- All per-resource CRUD `create_*` / `update_*` / `delete_*` tools except `create_customer` and `create_supplier`. Removal target: **0.3.0**.

## [0.1.1] - 2026-07-28

### Fixed

- Banking write hardening, persistence warnings, and scope registration fixes

## [0.1.0] - 2026-07-28

### Added

- Initial release: 10 read tools, 72 scoped CRUD write tools, denylist, agent skill
