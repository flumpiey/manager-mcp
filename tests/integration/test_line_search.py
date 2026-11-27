"""Live line-item search: a match only in a line description is found."""

from __future__ import annotations

import uuid

import pytest

from manager_mcp.task_tools import void_document

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_search_finds_line_only_text(
    live_client, call_tool, temp_supplier, expense_account_key
) -> None:
    word = f"lineonly{uuid.uuid4().hex[:8]}"
    body = await live_client.post(
        "/purchase-invoice-form",
        json={
            "Supplier": temp_supplier,
            "Lines": [
                {"Account": expense_account_key, "LineDescription": f"Bracket {word}", "Qty": 1,
                 "PurchaseUnitPrice": 1.0}
            ],
        },
    )
    key = body["Key"]
    try:
        header = await call_tool("list_records", {"resource": "purchase_invoices", "term": word})
        assert header["items"] == []
        found = await call_tool(
            "search_line_items", {"resource": "purchase_invoices", "term": word}
        )
        assert [m["Key"] for m in found["matches"]] == [key]
    finally:
        await void_document(live_client, live_client.policy, "purchase_invoices", key)
