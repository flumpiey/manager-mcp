"""Banking field normalisation and line-level persistence diff."""

from __future__ import annotations

import pytest

from manager_mcp.writable import WRITABLE
from manager_mcp.write_validate import diff_persisted, normalize_write_body, validate_write_body

VALID_RECEIPT = {
    "ReceivedIn": "bank-guid",
    "Customer": "cust-guid",
    "Date": "2026-07-13",
    "Payer": 1,
    "Lines": [
        {
            "Amount": 100.0,
            "AccountsReceivableCustomer": "cust-guid",
            "SalesInvoice": "inv-guid",
        }
    ],
}


def test_normalize_receipt_legacy_names() -> None:
    legacy = {
        "ReceivedIn": "bank-guid",
        "Customer": "cust-guid",
        "Date": "2026-07-13",
        "PaidBy": 1,
        "Lines": [
            {
                "Amount": 100.0,
                "AccountsReceivableCustomer": "cust-guid",
                "SalesInvoice": "inv-guid",
            }
        ],
    }
    out = normalize_write_body(WRITABLE["receipts"], legacy)
    assert out["PaidBy"] == 1
    assert out["Lines"][0]["AccountsReceivableSalesInvoice"] == "inv-guid"
    assert "SalesInvoice" not in out["Lines"][0]


def test_normalize_payment_legacy_names() -> None:
    body = {
        "PaidFrom": "bank-guid",
        "Supplier": "sup-guid",
        "Date": "2026-07-13",
        "PaidBy": 2,
        "Lines": [
            {
                "Account": "ap-guid",
                "Amount": 50.0,
                "AccountsPayableSupplier": "sup-guid",
                "AccountsPayablePurchaseInvoice": "inv-guid",
            }
        ],
    }
    out = normalize_write_body(WRITABLE["payments"], body)
    assert out["Payee"] == 2
    assert "PaidBy" not in out
    assert out["Lines"][0]["PurchaseInvoice"] == "inv-guid"


def test_diff_persisted_flags_dropped_line_field() -> None:
    warnings = diff_persisted(
        WRITABLE["payments"],
        {
            "PaidFrom": "bank-guid",
            "Date": "2026-07-13",
            "Payee": 2,
            "Lines": [
                {
                    "Account": "ap-guid",
                    "Amount": 50.0,
                    "AccountsPayableSupplier": "sup-guid",
                    "PurchaseInvoice": "inv-guid",
                }
            ],
        },
        {
            "Key": "k",
            "PaidFrom": "bank-guid",
            "Date": "2026-07-13",
            "Payee": 2,
            "Lines": [
                {
                    "Account": "ap-guid",
                    "Amount": 50.0,
                    "AccountsPayableSupplier": "sup-guid",
                }
            ],
        },
    )
    assert any("PurchaseInvoice" in w and "missing after save" in w for w in warnings)


def test_journal_unknown_field_rejected() -> None:
    with pytest.raises(ValueError, match="unknown field"):
        validate_write_body(
            WRITABLE["journal_entries"],
            {"Date": "2026-07-13", "NotAField": 1, "Lines": [{"Account": "a", "Debit": 1}]},
            creating=True,
        )
