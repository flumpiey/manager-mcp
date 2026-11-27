"""Live create, update and delete through the MCP tools for resources with no task tool."""

from __future__ import annotations

import uuid

import pytest

from manager_mcp.writable import WRITABLE

pytestmark = pytest.mark.integration

# Field that Manager 26.8 keeps on each form (probed live; wrong names are dropped silently).
_FIELD = {
    "sales_orders": "Description",
    "purchase_orders": "Description",
    "inventory_items": "ItemName",
    "non_inventory_items": "Name",
    "credit_notes": "Description",
    "delivery_notes": "Description",
    "debit_notes": "Description",
    "goods_receipts": "Description",
    "employees": "Name",
    "depreciation_entries": "Description",
    "amortization_entries": "Description",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", sorted(_FIELD))
async def test_crud_round_trip(resource: str, call_tool, live_client) -> None:
    stem = WRITABLE[resource].tool_stem
    field = _FIELD[resource]
    first, second = f"mcp {uuid.uuid4().hex[:8]}", f"mcp {uuid.uuid4().hex[:8]}"
    created = await call_tool(f"create_{stem}", {"fields": {field: first}})
    key = created["body"]["Key"]
    try:
        assert created["warnings"] == []
        updated = await call_tool(f"update_{stem}", {"key": key, "fields": {field: second}})
        assert updated["warnings"] == []
        form = await live_client.get(f"{WRITABLE[resource].form_path}/{key}")
        assert form[field] == second
    finally:
        await call_tool(f"delete_{stem}", {"key": key})


@pytest.mark.asyncio
async def test_payslip_round_trip(call_tool, live_client) -> None:
    created = await call_tool("create_payslip", {"fields": {"Date": "2026-11-27"}})
    key = created["body"]["Key"]
    try:
        await call_tool("update_payslip", {"key": key, "fields": {"Date": "2026-11-28"}})
        form = await live_client.get(f"/payslip-form/{key}")
        assert form["Date"].startswith("2026-11-28")
    finally:
        await call_tool("delete_payslip", {"key": key})


@pytest.mark.asyncio
async def test_wrong_field_name_warns(call_tool) -> None:
    created = await call_tool("create_inventory_item", {"fields": {"Name": "mcp wrong field"}})
    try:
        assert any(w.startswith("Name missing after save") for w in created["warnings"])
    finally:
        await call_tool("delete_inventory_item", {"key": created["body"]["Key"]})
