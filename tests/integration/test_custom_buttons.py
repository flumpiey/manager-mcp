"""Live custom button CRUD (automation scope)."""

from __future__ import annotations

import uuid

import pytest

from manager_mcp.server import _make_create_tool, _make_delete_tool

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_custom_button_round_trip(live_client) -> None:
    name = f"Integration Button {uuid.uuid4().hex[:8]}"
    create = _make_create_tool("custom_buttons")
    delete = _make_delete_tool("custom_buttons")
    out = await create(
        {
            "Name": name,
            "Text": name,
            "Placement": "form",
            "inactive": True,
        }
    )
    key = out["body"]["Key"]
    try:
        assert out["warnings"] == []
        form = await live_client.get(f"/custom-button-form/{key}")
        assert isinstance(form, dict)
        assert form.get("Name") == name
        assert form.get("Inactive") is True
    finally:
        await delete(key)
