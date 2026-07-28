"""FastMCP Manager.io server (stdio via `manager-mcp`). Writes via scope envs."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP
from mcp.types import Icon

from manager_mcp.client import ManagerClient
from manager_mcp.resources import all_resources, extract_items, form_path, resolve
from manager_mcp.scopes import WritePolicy
from manager_mcp.writable import WRITABLE, implemented_for_scope
from manager_mcp.write_validate import diff_persisted, validate_write_body

_PERIOD_ALIASES = {
    "from_date": "fromDate",
    "to_date": "toDate",
    "from": "fromDate",
    "to": "toDate",
}

_ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.png"
_ICON_HTTPS = (
    "https://raw.githubusercontent.com/flumpiey/manager-mcp/main/docs/icon-512.png"
)


def server_icons() -> list[Icon]:
    """Icons for initialize serverInfo (data URI + public HTTPS fallback)."""
    icons: list[Icon] = []
    if _ICON_PATH.is_file():
        b64 = base64.standard_b64encode(_ICON_PATH.read_bytes()).decode("ascii")
        icons.append(
            Icon(
                src=f"data:image/png;base64,{b64}",
                mimeType="image/png",
                sizes=["512x512"],
            )
        )
    icons.append(Icon(src=_ICON_HTTPS, mimeType="image/png", sizes=["512x512"]))
    return icons


mcp = FastMCP(
    "manager-mcp",
    website_url="https://www.manager.io/",
    icons=server_icons(),
)
_client: ManagerClient | None = None
_policy: WritePolicy | None = None
_write_tools_registered = False


def get_policy() -> WritePolicy:
    global _policy
    if _policy is None:
        _policy = WritePolicy.from_env()
    return _policy


def get_client() -> ManagerClient:
    global _client
    if _client is None:
        _client = ManagerClient.from_env(policy=get_policy())
    return _client


def reset_client() -> None:
    """Test helper: drop cached client and policy."""
    global _client, _policy, _write_tools_registered
    _client = None
    _policy = None
    _write_tools_registered = False


def _normalize_period(period: dict[str, Any], date_params: tuple[str, ...]) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for key, value in period.items():
        if value is None or value == "":
            continue
        raw[_PERIOD_ALIASES.get(key, key)] = value
    if not date_params:
        return {}
    return {key: raw[key] for key in date_params if key in raw}


async def _fetch_report(name: str, **period: Any) -> dict[str, Any]:
    desc = resolve(name)
    if desc is None or desc.kind != "report":
        raise ValueError(f"Unknown report '{name}'. Use list_resources.")
    requested = {k: v for k, v in period.items() if v is not None and v != ""}
    unsupported = bool(requested) and not desc.date_params
    forward = _normalize_period(period, desc.date_params)
    client = get_client()
    client._extra_query_keys = frozenset(desc.date_params)
    try:
        body = await client.get(desc.path, params=forward or None)
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Manager HTTP {exc.response.status_code} for {name}") from exc
    result: dict[str, Any] = {
        "report": name,
        "body": body,
        "period_applied": bool(forward),
    }
    if unsupported:
        result["period_unsupported_notice"] = (
            "Date/period selection is not available for this view in v1; "
            "returned current/default data."
        )
    return result


@mcp.tool(
    description=(
        "List curated read-only Manager.io capabilities. "
        "Create/edit/post/delete are not available."
    )
)
async def list_resources() -> dict[str, Any]:
    policy = get_policy()
    resources = [
        {
            "name": r.name,
            "kind": r.kind,
            "description": r.description,
            "path": r.path,
        }
        for r in all_resources()
    ]
    write_scopes = sorted(policy.write_scopes)
    delete_scopes = sorted(policy.delete_scopes)
    read_only = not (write_scopes or delete_scopes)
    if read_only:
        boundary = (
            "Default is read-only: no create/update/delete tools are registered. "
            "Set MANAGER_MCP_WRITE_SCOPES / MANAGER_MCP_DELETE_SCOPES to enable mutations."
        )
    else:
        boundary = (
            "Scoped writes enabled. create_*/update_* require WRITE_SCOPES; "
            "delete_* require DELETE_SCOPES. Client denylist still blocks never-writable "
            f"paths. write_scopes={write_scopes}; delete_scopes={delete_scopes}. "
            "After creating a record, verify with list_records/get_record on the same "
            "collection (e.g. receipts)."
        )
    return {
        "resources": resources,
        "read_only": read_only,
        "write_scopes": write_scopes,
        "delete_scopes": delete_scopes,
        "boundary": boundary,
    }


@mcp.tool(
    description=(
        "Search/page a curated collection. Core: customers, suppliers, sales_invoices, "
        "purchase_invoices, chart_of_accounts, bank_accounts. Also writable domains "
        "when present in discovery (e.g. receipts, payments, sales_quotes). "
        "bank_accounts is the searchable collection; use bank_balances for snapshot balances."
    )
)
async def list_records(
    resource: str,
    term: str | None = None,
    sort_by: str | None = None,
    sort_by_desc: bool | None = None,
    skip: int = 0,
    page_size: int = 50,
) -> dict[str, Any]:
    desc = resolve(resource)
    if desc is None or desc.kind != "collection":
        raise ValueError(
            f"Unknown collection '{resource}'. Use list_resources for supported names."
        )
    params: dict[str, Any] = {"skip": skip, "pageSize": page_size}
    if term is not None:
        params["term"] = term
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_by_desc is not None:
        params["sortByDesc"] = sort_by_desc
    client = get_client()
    try:
        body = await client.get(desc.path, params=params)
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Manager HTTP {exc.response.status_code}") from exc
    items = extract_items(desc, body)
    total = body.get("totalRecords") if isinstance(body, dict) else None
    if isinstance(total, int):
        has_more = skip + len(items) < total
    else:
        has_more = len(items) >= page_size
    return {
        "resource": resource,
        "items": items,
        "skip": skip,
        "page_size": page_size,
        "term": term,
        "truncated": has_more,
        "has_more": has_more,
    }


@mcp.tool(
    description=(
        "Fetch one collection record by GUID via Manager form endpoint "
        "(e.g. /customer-form/{key}). chart_of_accounts has no single form. "
        "For bank/cash account detail use resource=bank_accounts (not bank_balances)."
    )
)
async def get_record(resource: str, key: str) -> dict[str, Any]:
    path = form_path(resource, key)
    if path is None:
        raise ValueError(
            f"Unknown collection '{resource}' or form fetch unsupported. Use list_resources."
        )
    client = get_client()
    try:
        body = await client.get(path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise RuntimeError(f"Record not found: {resource}/{key}") from exc
        raise RuntimeError(f"Manager HTTP {exc.response.status_code}") from exc
    return {"resource": resource, "key": key, "body": body}


@mcp.tool(description="Aged receivables / outstanding customer balances (read-only snapshot).")
async def aged_receivables(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("aged_receivables", from_date=from_date, to_date=to_date)


@mcp.tool(description="Aged payables snapshot (read-only).")
async def aged_payables(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("aged_payables", from_date=from_date, to_date=to_date)


@mcp.tool(
    description=(
        "Bank/cash balances snapshot (read-only). "
        "For search/drill-in of individual accounts use list_records/get_record on bank_accounts."
    )
)
async def bank_balances(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("bank_balances", from_date=from_date, to_date=to_date)


@mcp.tool(description="Trial balance snapshot (read-only).")
async def trial_balance(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("trial_balance", from_date=from_date, to_date=to_date)


@mcp.tool(description="Profit and loss snapshot (read-only).")
async def profit_and_loss(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("profit_and_loss", from_date=from_date, to_date=to_date)


@mcp.tool(description="Balance sheet snapshot (read-only).")
async def balance_sheet(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("balance_sheet", from_date=from_date, to_date=to_date)


@mcp.tool(description="Tax summary snapshot (read-only).")
async def tax_summary(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    return await _fetch_report("tax_summary", from_date=from_date, to_date=to_date)


async def _persist_and_verify(
    resource_name: str,
    fields: dict[str, Any],
    body: Any,
) -> dict[str, Any]:
    w = WRITABLE[resource_name]
    result: dict[str, Any] = {"resource": resource_name, "body": body, "warnings": []}
    if not w.known_keys or not isinstance(body, dict):
        return result
    key = body.get("Key") or body.get("key")
    if not key:
        result["warnings"] = ["create/update response had no Key; could not verify"]
        return result
    persisted = await get_client().get(f"{w.form_path}/{key}")
    form = persisted if isinstance(persisted, dict) else None
    result["warnings"] = diff_persisted(w, fields, form)
    result["verified"] = persisted
    return result


def _make_create_tool(resource_name: str) -> Any:
    w = WRITABLE[resource_name]
    stem = w.tool_stem

    async def _create(fields: dict[str, Any]) -> dict[str, Any]:
        validate_write_body(w, fields, creating=True)
        body = await get_client().post(w.form_path, json=fields)
        if w.known_keys:
            return await _persist_and_verify(resource_name, fields, body)
        return {"resource": resource_name, "body": body}

    _create.__name__ = f"create_{stem}"
    notes = f" {w.create_notes}" if w.create_notes else ""
    _create.__doc__ = (
        f"Create a {stem.replace('_', ' ')} via POST {w.form_path}. "
        f"Requires {w.scope!r} in MANAGER_MCP_WRITE_SCOPES.{notes}"
    )
    return _create


def _make_update_tool(resource_name: str) -> Any:
    w = WRITABLE[resource_name]
    stem = w.tool_stem

    async def _update(key: str, fields: dict[str, Any]) -> dict[str, Any]:
        validate_write_body(w, fields, creating=False)
        path = f"{w.form_path}/{key}"
        body = await get_client().put(path, json=fields)
        if w.known_keys:
            out = await _persist_and_verify(resource_name, fields, body or {"Key": key})
            out["key"] = key
            return out
        return {"resource": resource_name, "key": key, "body": body}

    _update.__name__ = f"update_{stem}"
    _update.__doc__ = (
        f"Update a {stem.replace('_', ' ')} via PUT {w.form_path}/{{key}}. "
        f"Requires {w.scope!r} in MANAGER_MCP_WRITE_SCOPES. "
        "Prefer GET form → modify → PUT (full document replace)."
    )
    return _update


def _make_delete_tool(resource_name: str) -> Any:
    w = WRITABLE[resource_name]
    stem = w.tool_stem

    async def _delete(key: str) -> dict[str, Any]:
        path = f"{w.form_path}/{key}"
        body = await get_client().delete(path)
        return {"resource": resource_name, "key": key, "body": body}

    _delete.__name__ = f"delete_{stem}"
    _delete.__doc__ = (
        f"Delete a {stem.replace('_', ' ')} via DELETE {w.form_path}/{{key}}. "
        f"Requires {w.scope!r} in MANAGER_MCP_DELETE_SCOPES "
        "(write scope alone is not enough)."
    )
    return _delete


_WRITE_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": True,
}
_DELETE_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": True,
}


def register_write_tools() -> None:
    """Validate scope env and register create_*/update_*/delete_* for implemented scopes."""
    global _write_tools_registered
    if _write_tools_registered:
        return
    policy = get_policy()
    for scope in sorted(policy.write_scopes | policy.delete_scopes):
        for w in implemented_for_scope(scope):
            stem = w.tool_stem
            if w.scope in policy.write_scopes:
                create_fn = _make_create_tool(w.name)
                update_fn = _make_update_tool(w.name)
                mcp.tool(
                    name=f"create_{stem}",
                    description=create_fn.__doc__,
                    annotations=_WRITE_ANNOTATIONS,
                )(create_fn)
                mcp.tool(
                    name=f"update_{stem}",
                    description=update_fn.__doc__,
                    annotations=_WRITE_ANNOTATIONS,
                )(update_fn)
            if w.scope in policy.delete_scopes:
                delete_fn = _make_delete_tool(w.name)
                mcp.tool(
                    name=f"delete_{stem}",
                    description=delete_fn.__doc__,
                    annotations=_DELETE_ANNOTATIONS,
                )(delete_fn)
    _write_tools_registered = True


def main() -> None:
    register_write_tools()
    mcp.run()


if __name__ == "__main__":
    main()
