"""Live payment task tools."""

from __future__ import annotations

import pytest

from manager_mcp.task_tools import (
    issue_purchase_invoice,
    issue_sales_invoice,
    record_customer_payment,
    record_supplier_payment,
    void_document,
)

pytestmark = pytest.mark.integration

_TODAY = "2026-07-29"


def _list_row_key(row: dict[str, object]) -> str:
    key = row.get("Key") or row.get("key")
    return str(key) if key else ""


def _money_value(raw: object) -> float | None:
    if isinstance(raw, dict) and "value" in raw:
        try:
            return float(raw["value"])
        except (TypeError, ValueError):
            return None
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


@pytest.mark.asyncio
async def test_record_customer_payment_happy_path(
    live_client,
    temp_customer,
    bank_account_key,
    income_account_key,
) -> None:
    invoice_out = await issue_sales_invoice(
        live_client,
        live_client.policy,
        {
            "Customer": temp_customer,
            "IssueDate": _TODAY,
            "Lines": [
                {
                    "Account": income_account_key,
                    "LineDescription": "Payment test",
                    "Qty": 1,
                    "SalesUnitPrice": 100.0,
                }
            ],
        },
    )
    invoice_key = invoice_out["keys"]["sales_invoice"]
    receipt_key = ""
    try:
        out = await record_customer_payment(
            live_client,
            live_client.policy,
            customer=temp_customer,
            bank_account=bank_account_key,
            date=_TODAY,
            amount=100.0,
            invoice_key=invoice_key,
        )
        assert out["status"] == "ok"
        receipt_key = out["keys"]["receipt"]
        assert receipt_key
        assert out["keys"]["invoice"] == invoice_key
        assert not any("unallocated" in w.casefold() for w in out["warnings"])
    finally:
        if receipt_key:
            await void_document(live_client, live_client.policy, "receipts", receipt_key)
        await void_document(live_client, live_client.policy, "sales_invoices", invoice_key)


@pytest.mark.asyncio
async def test_record_supplier_payment_happy_path(
    live_client,
    temp_supplier,
    bank_account_key,
    expense_account_key,
) -> None:
    invoice_out = await issue_purchase_invoice(
        live_client,
        live_client.policy,
        {
            "Supplier": temp_supplier,
            "IssueDate": _TODAY,
            "Lines": [
                {
                    "Account": expense_account_key,
                    "LineDescription": "Supplier payment test",
                    "Qty": 1,
                    "PurchaseUnitPrice": 25.0,
                }
            ],
        },
    )
    invoice_key = invoice_out["keys"]["purchase_invoice"]
    payment_key = ""
    pay_amount = 25.0
    listed = await live_client.get("/purchase-invoices", params={"skip": 0, "pageSize": 50})
    if isinstance(listed, dict):
        for row in listed.get("purchaseInvoices") or []:
            if isinstance(row, dict) and _list_row_key(row) == invoice_key:
                amount = _money_value(row.get("invoiceAmount"))
                if amount is not None and amount > 0:
                    pay_amount = amount
                break
    try:
        out = await record_supplier_payment(
            live_client,
            live_client.policy,
            supplier=temp_supplier,
            bank_account=bank_account_key,
            date=_TODAY,
            amount=pay_amount,
            invoice_key=invoice_key,
        )
        assert out["status"] == "ok"
        payment_key = out["keys"]["payment"]
        assert payment_key
        assert out["keys"]["invoice"] == invoice_key

        invoices = await live_client.get("/purchase-invoices", params={"skip": 0, "pageSize": 50})
        invoice_row = None
        if isinstance(invoices, dict):
            for row in invoices.get("purchaseInvoices") or []:
                if isinstance(row, dict) and _list_row_key(row) == invoice_key:
                    invoice_row = row
                    break
        assert invoice_row is not None, "purchase invoice not found in list"
        balance = _money_value(invoice_row.get("balanceDue") or invoice_row.get("BalanceDue"))
        assert balance == 0.0
        status = str(invoice_row.get("status") or invoice_row.get("Status") or "")
        assert status == "PaidInFull"

        payment = await live_client.get(f"/payment-form/{payment_key}")
        assert isinstance(payment, dict)
        lines = payment.get("Lines") or []
        assert lines and isinstance(lines[0], dict)
        assert str(lines[0].get("PurchaseInvoice")) == invoice_key
    finally:
        if payment_key:
            await void_document(live_client, live_client.policy, "payments", payment_key)
        await void_document(live_client, live_client.policy, "purchase_invoices", invoice_key)
