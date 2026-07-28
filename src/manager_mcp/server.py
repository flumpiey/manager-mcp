"""FastMCP Manager.io server (stdio via `manager-mcp`). Writes opt-in via env."""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP

from manager_mcp.client import WRITE_METHODS, ManagerClient, writes_enabled
from manager_mcp.resources import all_resources, extract_items, form_path, resolve

_PERIOD_ALIASES = {
    "from_date": "fromDate",
    "to_date": "toDate",
    "from": "fromDate",
    "to": "toDate",
}

mcp = FastMCP("manager-mcp")
_client: ManagerClient | None = None
_write_tools_registered = False


def get_client() -> ManagerClient:
    global _client
    if _client is None:
        _client = ManagerClient.from_env()
    return _client


def reset_client() -> None:
    """Test helper: drop cached client."""
    global _client
    _client = None


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
    resources = [
        {
            "name": r.name,
            "kind": r.kind,
            "description": r.description,
            "path": r.path,
        }
        for r in all_resources()
    ]
    return {
        "resources": resources,
        "read_only": True,
        "boundary": "Read-only: no create, edit, post, or delete operations are available.",
    }


@mcp.tool(
    description=(
        "Search/page a curated collection (customers, suppliers, sales_invoices, "
        "purchase_invoices, chart_of_accounts, bank_accounts). "
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


async def api_write(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST/PUT/PATCH/DELETE a Manager API2 path. Requires MANAGER_MCP_ALLOW_WRITES."""
    verb = method.upper()
    if verb not in WRITE_METHODS:
        raise ValueError(f"method must be one of {sorted(WRITE_METHODS)}")
    if not path.startswith("/") or ".." in path:
        raise ValueError("path must be an absolute API path starting with /")
    client = get_client()
    if verb == "DELETE":
        result = await client.delete(path)
    elif verb == "POST":
        result = await client.post(path, json=body)
    elif verb == "PUT":
        result = await client.put(path, json=body)
    else:
        result = await client.patch(path, json=body)
    return {"method": verb, "path": path, "body": result}


def register_write_tools() -> None:
    """Register api_write when MANAGER_MCP_ALLOW_WRITES is truthy."""
    global _write_tools_registered
    if _write_tools_registered or not writes_enabled():
        return
    mcp.tool(
        name="api_write",
        description=(
            "Mutating Manager.io API call (POST/PUT/PATCH/DELETE). "
            "Only available when MANAGER_MCP_ALLOW_WRITES is enabled."
        ),
    )(api_write)
    _write_tools_registered = True


def main() -> None:
    register_write_tools()
    mcp.run()


if __name__ == "__main__":
    main()
