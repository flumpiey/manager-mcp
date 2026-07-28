"""MCP tool tests with respx (no live Manager)."""

from __future__ import annotations

import httpx
import pytest
import respx

from manager_mcp.resources import resolve
from manager_mcp.server import mcp, reset_client

BASE = "http://example.test/api2"
REPORTS = [
    "aged_receivables",
    "aged_payables",
    "bank_balances",
    "trial_balance",
    "profit_and_loss",
    "balance_sheet",
    "tax_summary",
]


@pytest.fixture(autouse=True)
def _env_and_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_API_URL", BASE)
    monkeypatch.setenv("MANAGER_API_KEY", "test-key")
    reset_client()
    yield
    reset_client()


async def _call(name: str, arguments: dict | None = None) -> dict:
    result = await mcp.call_tool(name, arguments or {})
    assert not result.is_error, result
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.asyncio
@respx.mock
async def test_aged_receivables_success() -> None:
    body = {"customers": [{"name": "Acme", "accountsReceivable": {"value": 12.5}}]}
    path = resolve("aged_receivables").path  # type: ignore[union-attr]
    respx.get(f"{BASE}{path}").mock(return_value=httpx.Response(200, json=body))
    out = await _call("aged_receivables")
    assert out["body"] == body
    assert out["period_applied"] is False
    assert "period_unsupported_notice" not in out


@pytest.mark.asyncio
@respx.mock
async def test_aged_receivables_auth_error() -> None:
    path = resolve("aged_receivables").path  # type: ignore[union-attr]
    respx.get(f"{BASE}{path}").mock(return_value=httpx.Response(401, json={"e": 1}))
    with pytest.raises(Exception, match="401"):
        await _call("aged_receivables")


@pytest.mark.asyncio
@respx.mock
async def test_aged_receivables_period_unsupported_notice() -> None:
    path = resolve("aged_receivables").path  # type: ignore[union-attr]
    respx.get(f"{BASE}{path}").mock(return_value=httpx.Response(200, json={"customers": []}))
    out = await _call("aged_receivables", {"from_date": "2024-01-01", "to_date": "2024-12-31"})
    assert out["period_applied"] is False
    assert "period_unsupported_notice" in out


@pytest.mark.asyncio
@respx.mock
async def test_trial_balance_period_applied() -> None:
    path = resolve("trial_balance").path  # type: ignore[union-attr]
    route = respx.get(f"{BASE}{path}").mock(
        return_value=httpx.Response(200, json={"trialBalanceTransactions": []})
    )
    out = await _call("trial_balance", {"from_date": "2024-01-01", "to_date": "2024-12-31"})
    assert out["period_applied"] is True
    assert route.calls.last.request.url.params.get("fromDate") == "2024-01-01"
    assert route.calls.last.request.url.params.get("toDate") == "2024-12-31"


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("name", REPORTS)
async def test_report_shortcuts(name: str) -> None:
    path = resolve(name).path  # type: ignore[union-attr]
    respx.get(f"{BASE}{path}").mock(return_value=httpx.Response(200, json={"ok": name}))
    out = await _call(name)
    assert out["report"] == name
    assert out["body"] == {"ok": name}


@pytest.mark.asyncio
async def test_list_resources_boundary() -> None:
    out = await _call("list_resources")
    assert out["read_only"] is True
    assert "create" in out["boundary"].casefold() or "delete" in out["boundary"].casefold()
    names = {r["name"] for r in out["resources"]}
    assert "customers" in names
    assert "aged_receivables" in names
    assert "bank_balances" in names
    assert "bank_accounts" in names


@pytest.mark.asyncio
@respx.mock
async def test_list_records_truncation_and_term() -> None:
    respx.get(f"{BASE}/customers").mock(
        return_value=httpx.Response(
            200,
            json={
                "totalRecords": 120,
                "customers": [{"key": str(i)} for i in range(50)],
            },
        )
    )
    out = await _call(
        "list_records",
        {"resource": "customers", "term": "acme", "skip": 0, "page_size": 50},
    )
    assert len(out["items"]) == 50
    assert out["truncated"] is True
    assert out["has_more"] is True
    assert out["term"] == "acme"
    assert respx.calls.last.request.url.params.get("term") == "acme"


@pytest.mark.asyncio
async def test_list_records_unknown_resource() -> None:
    with pytest.raises(Exception, match="Unknown collection"):
        await _call("list_records", {"resource": "nope"})


@pytest.mark.asyncio
@respx.mock
async def test_get_record_form_path() -> None:
    respx.get(f"{BASE}/customer-form/guid-1").mock(
        return_value=httpx.Response(200, json={"Name": "Acme"})
    )
    out = await _call("get_record", {"resource": "customers", "key": "guid-1"})
    assert out["body"] == {"Name": "Acme"}
    assert out["key"] == "guid-1"


@pytest.mark.asyncio
@respx.mock
async def test_get_record_404() -> None:
    respx.get(f"{BASE}/customer-form/missing").mock(
        return_value=httpx.Response(404, json={})
    )
    with pytest.raises(Exception, match="not found"):
        await _call("get_record", {"resource": "customers", "key": "missing"})


@pytest.mark.asyncio
async def test_bank_dual_tool_descriptions() -> None:
    tools = {t.name: t for t in await mcp.list_tools()}
    assert "bank_accounts" in (tools["bank_balances"].description or "")
    assert "bank_balances" in (tools["list_records"].description or "")
