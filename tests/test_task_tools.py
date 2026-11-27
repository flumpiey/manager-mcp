"""Task tool happy paths and scope gates (respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from manager_mcp.client import ManagerClient
from manager_mcp.scopes import WritePolicy, WritesDeniedError
from manager_mcp.server import mcp, register_task_tools, reset_client
from manager_mcp.task_tools import record_customer_payment

BASE = "http://example.test/api2"

VALID_RECEIPT = {
    "ReceivedIn": "bank-guid",
    "Customer": "cust-guid",
    "Date": "2026-07-13",
    "PaidBy": 1,
    "Lines": [
        {
            "Amount": 100.0,
            "AccountsReceivableCustomer": "cust-guid",
            "AccountsReceivableSalesInvoice": "inv-guid",
        }
    ],
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_API_URL", BASE)
    monkeypatch.setenv("MANAGER_API_KEY", "k")
    monkeypatch.setenv("MANAGER_MCP_WRITE_SCOPES", "banking,sales")
    for name in ("MANAGER_MCP_ALLOW_WRITES", "ALLOW_WRITES", "MANAGER_MCP_WRITES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("MANAGER_MCP_DELETE_SCOPES", raising=False)
    reset_client()
    yield
    reset_client()


@pytest.mark.asyncio
@respx.mock
async def test_record_customer_payment_happy_path() -> None:
    key = "11111111-1111-1111-1111-111111111111"
    respx.post(f"{BASE}/receipt-form").mock(
        return_value=httpx.Response(201, json={"Key": key, **VALID_RECEIPT})
    )
    respx.get(f"{BASE}/receipt-form/{key}").mock(
        return_value=httpx.Response(200, json={"Key": key, **VALID_RECEIPT})
    )
    client = ManagerClient(BASE, "k", policy=WritePolicy(frozenset({"banking"}), frozenset()))
    out = await record_customer_payment(
        client,
        client.policy,
        customer="cust-guid",
        bank_account="bank-guid",
        date="2026-07-13",
        amount=100.0,
        invoice_key="inv-guid",
    )
    await client.aclose()
    assert out["status"] == "ok"
    assert out["keys"]["receipt"] == key
    assert out["keys"]["invoice"] == "inv-guid"


@pytest.mark.asyncio
async def test_record_customer_payment_requires_banking_scope() -> None:
    client = ManagerClient(BASE, "k", policy=WritePolicy(frozenset({"sales"}), frozenset()))
    with pytest.raises(WritesDeniedError, match="banking"):
        await record_customer_payment(
            client,
            client.policy,
            customer="c",
            bank_account="b",
            date="2026-07-13",
            amount=1.0,
            invoice_key="i",
        )
    await client.aclose()


def test_task_tools_register_with_banking_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_MCP_WRITE_SCOPES", "banking")
    reset_client()
    captured: list[str] = []

    def fake_tool(*_args: object, **kwargs: object):
        def deco(fn: object) -> object:
            captured.append(str(kwargs.get("name") or getattr(fn, "__name__", "")))
            return fn

        return deco

    monkeypatch.setattr(mcp, "tool", fake_tool)
    register_task_tools()
    assert "record_customer_payment" in captured
    assert "record_customer_deposit" in captured
    assert "issue_sales_invoice" not in captured


def test_crud_deprecated_prefix_without_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    from manager_mcp.scopes import WritePolicy
    from manager_mcp.server import _deprecation_prefix

    policy = WritePolicy(frozenset({"banking"}), frozenset())
    assert "[DEPRECATED" in _deprecation_prefix(policy, "receipt")
    assert _deprecation_prefix(policy, "customer") == ""


def test_crud_no_deprecation_with_raw() -> None:
    from manager_mcp.scopes import WritePolicy
    from manager_mcp.server import _deprecation_prefix

    policy = WritePolicy(frozenset({"raw"}), frozenset())
    assert _deprecation_prefix(policy, "receipt") == ""


def _capture_task_tools(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_tool(*_args: object, **kwargs: object):
        def deco(fn: object) -> object:
            captured[str(kwargs.get("name"))] = fn
            return fn

        return deco

    monkeypatch.setattr(mcp, "tool", fake_tool)
    register_task_tools()
    return captured


@pytest.mark.asyncio
@respx.mock
async def test_supplier_payment_wrapper_uses_supplier_payee_and_ap_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "22222222-2222-2222-2222-222222222222"
    respx.get(f"{BASE}/chart-of-accounts").mock(
        return_value=httpx.Response(
            200,
            json={
                "chartOfAccounts": [
                    {"Key": "fees-acct", "Name": "Bank charges"},
                    {"Key": "ap-acct", "Name": "Accounts payable"},
                ]
            },
        )
    )
    post = respx.post(f"{BASE}/payment-form").mock(
        return_value=httpx.Response(201, json={"Key": key})
    )
    respx.get(f"{BASE}/payment-form/{key}").mock(
        return_value=httpx.Response(500, text="boom")
    )
    tools = _capture_task_tools(monkeypatch)
    out = await tools["record_supplier_payment"](
        supplier="sup-guid",
        bank_account="bank-guid",
        date="2026-07-13",
        amount=50.0,
        invoice_key="pinv-guid",
    )
    sent = __import__("json").loads(post.calls.last.request.content)
    assert sent["Payee"] == 2
    assert sent["Lines"][0]["Account"] == "ap-acct"
    # Read-back failed after a save: keep the key, warn, do not ask for a retry.
    assert out["keys"]["payment"] == key
    assert any("do not retry" in w for w in out["warnings"])


@pytest.mark.asyncio
async def test_record_expense_refuses_missing_requested_route() -> None:
    from manager_mcp.task_tools import record_expense

    policy = WritePolicy(frozenset({"purchases"}), frozenset())
    with pytest.raises(WritesDeniedError, match="payroll"):
        await record_expense(None, policy, {"Date": "2026-07-13"}, via="expense_claim")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="via must be"):
        await record_expense(None, policy, {}, via="bogus")  # type: ignore[arg-type]
