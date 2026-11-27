"""Intent-shaped accounting task tools (compose scoped CRUD operations)."""

from __future__ import annotations

import base64
import binascii
from typing import Any
from uuid import UUID

import httpx

from manager_mcp.client import ManagerApiError, ManagerClient, ManagerUnavailableError
from manager_mcp.scopes import WritePolicy, WritesDeniedError
from manager_mcp.writable import WRITABLE, WritableResource
from manager_mcp.write_validate import diff_persisted, normalize_write_body, validate_write_body


def _body_key(body: Any) -> str:
    return body.get("Key", "") if isinstance(body, dict) else ""


def _envelope(
    status: str,
    *,
    keys: dict[str, str],
    body: Any = None,
    warnings: list[str] | None = None,
    next_steps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "keys": keys,
        "body": body,
        "warnings": warnings or [],
        "next_steps": next_steps or [],
    }


def require_write_scopes(policy: WritePolicy, *scopes: str) -> None:
    effective = policy.effective_write_scopes
    missing = [s for s in scopes if s not in effective]
    if missing:
        raise WritesDeniedError(
            f"Task requires scope(s) {missing!r} in MANAGER_MCP_WRITE_SCOPES "
            f"(effective: {sorted(effective)})."
        )


def require_delete_scope(policy: WritePolicy, scope: str) -> None:
    if scope not in policy.effective_delete_scopes:
        raise WritesDeniedError(
            f"void_document requires scope {scope!r} in MANAGER_MCP_DELETE_SCOPES."
        )


async def _post(
    client: ManagerClient,
    resource: WritableResource,
    fields: dict[str, Any],
) -> dict[str, Any]:
    validate_write_body(resource, fields, creating=True)
    payload = normalize_write_body(resource, fields)
    body = await client.post(resource.form_path, json=payload)
    return {"body": body, "warnings": await _verify(client, resource, payload, body)}


async def _verify(
    client: ManagerClient, resource: WritableResource, payload: dict[str, Any], body: Any
) -> list[str]:
    """Read the saved form back and diff it. Never raises: the write already happened."""
    if not isinstance(body, dict):
        return []
    key = body.get("Key") or body.get("key")
    if not key:
        return ["create/update response had no Key; could not verify"]
    try:
        persisted = await client.get(f"{resource.form_path}/{key}")
    except (ManagerUnavailableError, ManagerApiError, httpx.HTTPStatusError) as exc:
        return [f"Saved as {key} but read-back failed; do not retry the write. Detail: {exc}"]
    form = persisted if isinstance(persisted, dict) else None
    if resource.known_keys:
        return diff_persisted(resource, payload, form)
    if form is None:
        return ["could not verify persistence (no form body returned)"]
    # Manager returns 201 but drops unknown field names; empty values are omitted on read.
    return [
        f"{k} missing after save (Manager drops unknown field names; clone get_record)"
        for k, v in payload.items()
        if v and k not in form
    ]


async def _accounts_payable_account_key(client: ManagerClient) -> str | None:
    """Resolve the Accounts payable control account from the COA, else a past AP line."""
    coa = await client.get("/chart-of-accounts", params={"skip": 0, "pageSize": 200})
    if isinstance(coa, dict):
        for item in coa.get("chartOfAccounts") or []:
            if not isinstance(item, dict):
                continue
            control = str(item.get("ControlAccount") or item.get("controlAccount") or "")
            name = str(item.get("Name") or item.get("name") or "")
            if control == "AccountsPayable" or name.casefold() == "accounts payable":
                key = item.get("Key") or item.get("key")
                if key:
                    return str(key)
    payments = await client.get("/payments", params={"skip": 0, "pageSize": 10})
    if isinstance(payments, dict):
        for row in payments.get("payments") or []:
            pay_key = (row.get("Key") or row.get("key")) if isinstance(row, dict) else None
            if not pay_key:
                continue
            form = await client.get(f"/payment-form/{pay_key}")
            for line in (form.get("Lines") or []) if isinstance(form, dict) else []:
                # Only supplier lines post to AP; other lines (bank fees) hit expense accounts.
                if (
                    isinstance(line, dict)
                    and line.get("Account")
                    and line.get("AccountsPayableSupplier")
                ):
                    return str(line["Account"])
    return None


def _allocation_link_warning(warnings: list[str], link_field: str) -> str | None:
    needle = f".{link_field} "
    for warning in warnings:
        if link_field in warning and (
            "missing after save" in warning or "differs after save" in warning
        ):
            return warning
        if needle in warning:
            return warning
    return None


_DEPOSIT_ACCOUNT_NAME = "customer deposits"
_DEPOSIT_ACCOUNT_GUIDE = (
    "In Manager: Settings → Bank and Cash Accounts → New Account. "
    "Name it exactly 'Customer deposits' (liability-style holding account), "
    "or pass bank_account explicitly. Alternatively, with banking scope enabled, "
    "call create_bank_account with {\"Name\": \"Customer deposits\"} in a separate step."
)


async def _find_deposit_bank_account(client: ManagerClient) -> dict[str, Any] | None:
    # Exact name only: a substring match picked real accounts such as "Fixed Deposit".
    body = await client.get(
        "/bank-and-cash-accounts",
        params={"term": _DEPOSIT_ACCOUNT_NAME, "skip": 0, "pageSize": 50},
    )
    if not isinstance(body, dict):
        return None
    for item in body.get("bankAndCashAccounts") or []:
        if not isinstance(item, dict):
            continue
        key = item.get("Key") or item.get("key")
        name = str(item.get("Name") or item.get("name") or item.get("text") or "")
        if key and name.strip().casefold() == _DEPOSIT_ACCOUNT_NAME:
            return {**item, "Key": key}
    return None


async def issue_sales_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    require_write_scopes(policy, "sales")
    out = await _post(client, WRITABLE["sales_invoices"], fields)
    return _envelope(
        "ok",
        keys={"sales_invoice": _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
    )


MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


async def attach_receipt_to_purchase_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    invoice_key: str,
    file_name: str,
    file_content_base64: str,
) -> dict[str, Any]:
    """Attach base64 file content to a purchase invoice (no server paths or URLs)."""
    require_write_scopes(policy, "purchases")
    try:
        key = str(UUID(invoice_key))
    except ValueError as exc:
        raise ValueError(f"invoice_key {invoice_key!r} is not a valid key.") from exc
    name = file_name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name:
        raise ValueError("file_name is empty.")
    # Refuse oversize input before decoding it (base64 is 4/3 of the bytes).
    if len(file_content_base64) > (MAX_ATTACHMENT_BYTES * 4) // 3 + 4:
        raise ValueError(f"The file is larger than the {MAX_ATTACHMENT_BYTES} byte limit.")
    try:
        data = base64.b64decode(file_content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"file_content_base64 is not valid base64: {exc}") from exc
    if not data:
        raise ValueError("The file is empty.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"The file is larger than the {MAX_ATTACHMENT_BYTES} byte limit.")
    try:
        await client.get(f"{WRITABLE['purchase_invoices'].form_path}/{key}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ValueError(f"Purchase invoice {key} not found.") from exc
        raise
    await client.upload_attachment(key, name, data)
    return _envelope(
        "unverified",
        keys={"purchase_invoice": key, "file_name": name},
        warnings=[
            "Manager accepted the upload, but its API cannot list attachments, "
            "so the attachment was not read back."
        ],
        next_steps=[f"Check the Attachments tab of purchase invoice {key} in Manager."],
    )


async def issue_purchase_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    require_write_scopes(policy, "purchases")
    out = await _post(client, WRITABLE["purchase_invoices"], fields)
    return _envelope(
        "ok",
        keys={"purchase_invoice": _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
    )


async def issue_quote(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
    *,
    purchase: bool = False,
) -> dict[str, Any]:
    require_write_scopes(policy, "quotes")
    resource = WRITABLE["purchase_quotes"] if purchase else WRITABLE["sales_quotes"]
    out = await _post(client, resource, fields)
    label = "purchase_quote" if purchase else "sales_quote"
    return _envelope(
        "ok", keys={label: _body_key(out["body"])}, body=out["body"], warnings=out["warnings"]
    )


async def convert_quote_to_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    quote_key: str,
    *,
    purchase: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_write_scopes(policy, "quotes", "sales" if not purchase else "purchases")
    quote_resource = WRITABLE["purchase_quotes"] if purchase else WRITABLE["sales_quotes"]
    invoice_resource = (
        WRITABLE["purchase_invoices"] if purchase else WRITABLE["sales_invoices"]
    )
    quote = await client.get(f"{quote_resource.form_path}/{quote_key}")
    if not isinstance(quote, dict):
        raise ValueError(f"Quote {quote_key} returned no form body.")
    fields = dict(quote)
    fields.pop("Key", None)
    if extra_fields:
        fields.update(extra_fields)
    out = await _post(client, invoice_resource, fields)
    label = "purchase_invoice" if purchase else "sales_invoice"
    return _envelope(
        "ok",
        keys={"quote": quote_key, label: _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
    )


def _receipt_with_allocation(
    *,
    customer: str,
    bank_account: str,
    date: str,
    amount: float,
    invoice_key: str | None,
    reference: str | None,
    paid_by: int,
    description: str | None,
) -> dict[str, Any]:
    line: dict[str, Any] = {
        "Amount": amount,
        "AccountsReceivableCustomer": customer,
    }
    if invoice_key:
        line["AccountsReceivableSalesInvoice"] = invoice_key
    fields: dict[str, Any] = {
        "ReceivedIn": bank_account,
        "Customer": customer,
        "Date": date,
        "PaidBy": paid_by,
        "Lines": [line],
    }
    if reference:
        fields["Reference"] = reference
    if description:
        fields["Description"] = description
    return fields


async def record_customer_payment(
    client: ManagerClient,
    policy: WritePolicy,
    *,
    customer: str,
    bank_account: str,
    date: str,
    amount: float,
    invoice_key: str,
    reference: str | None = None,
    paid_by: int = 1,
    description: str | None = None,
) -> dict[str, Any]:
    require_write_scopes(policy, "banking")
    fields = _receipt_with_allocation(
        customer=customer,
        bank_account=bank_account,
        date=date,
        amount=amount,
        invoice_key=invoice_key,
        reference=reference,
        paid_by=paid_by,
        description=description,
    )
    out = await _post(client, WRITABLE["receipts"], fields)
    key = _body_key(out["body"])
    if not invoice_key:
        return _envelope(
            "partial",
            keys={"receipt": key},
            warnings=["No invoice_key supplied; receipt is unallocated."],
            next_steps=[
                "Call record_customer_payment again with invoice_key, or allocate "
                "manually in Manager."
            ],
            body=out["body"],
        )
    link_warning = _allocation_link_warning(out["warnings"], "AccountsReceivableSalesInvoice")
    if link_warning:
        return _envelope(
            "partial",
            keys={"receipt": key, "invoice": invoice_key},
            warnings=out["warnings"],
            next_steps=[
                "Receipt saved but the sales invoice link did not persist. "
                "Check Lines[0].AccountsReceivableSalesInvoice and PaidBy, then "
                "update via update_receipt or void and retry."
            ],
            body=out["body"],
        )
    return _envelope(
        "ok",
        keys={"receipt": key, "invoice": invoice_key},
        body=out["body"],
        warnings=out["warnings"],
    )


async def record_supplier_payment(
    client: ManagerClient,
    policy: WritePolicy,
    *,
    supplier: str,
    bank_account: str,
    date: str,
    amount: float,
    invoice_key: str,
    reference: str | None = None,
    paid_by: int = 2,
    description: str | None = None,
) -> dict[str, Any]:
    require_write_scopes(policy, "banking")
    ap_account = await _accounts_payable_account_key(client)
    if not ap_account:
        return _envelope(
            "partial",
            keys={},
            warnings=["Could not resolve Accounts payable control account for payment line."],
            next_steps=[
                "Ensure the books have an Accounts payable account, or create a "
                "payment in Manager once and retry record_supplier_payment."
            ],
        )
    line: dict[str, Any] = {
        "Account": ap_account,
        "Amount": amount,
        "AccountsPayableSupplier": supplier,
        "PurchaseInvoice": invoice_key,
    }
    fields: dict[str, Any] = {
        "PaidFrom": bank_account,
        "Supplier": supplier,
        "Date": date,
        "Payee": paid_by,
        "Lines": [line],
    }
    if reference:
        fields["Reference"] = reference
    if description:
        fields["Description"] = description
    out = await _post(client, WRITABLE["payments"], fields)
    payment_key = _body_key(out["body"])
    link_warning = _allocation_link_warning(out["warnings"], "PurchaseInvoice")
    if link_warning:
        return _envelope(
            "partial",
            keys={"payment": payment_key, "invoice": invoice_key},
            warnings=out["warnings"],
            next_steps=[
                "Payment saved but the purchase invoice link did not persist. "
                "Check Lines[0].PurchaseInvoice, Account (AP), and Payee, then "
                "update via update_payment or void and retry."
            ],
            body=out["body"],
        )
    return _envelope(
        "ok",
        keys={"payment": payment_key, "invoice": invoice_key},
        body=out["body"],
        warnings=out["warnings"],
    )


async def record_expense(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
    *,
    via: str = "auto",
) -> dict[str, Any]:
    if via not in {"auto", "expense_claim", "purchase_invoice"}:
        raise ValueError(f"via must be auto, expense_claim or purchase_invoice, not {via!r}.")
    if via == "expense_claim" or (
        via == "auto" and "purchases" not in policy.effective_write_scopes
    ):
        require_write_scopes(policy, "payroll")
        resource, label = WRITABLE["expense_claims"], "expense_claim"
    else:
        require_write_scopes(policy, "purchases")
        resource, label = WRITABLE["purchase_invoices"], "purchase_invoice"
    out = await _post(client, resource, fields)
    return _envelope(
        "ok", keys={label: _body_key(out["body"])}, body=out["body"], warnings=out["warnings"]
    )


async def transfer_between_accounts(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    require_write_scopes(policy, "banking")
    out = await _post(client, WRITABLE["inter_account_transfers"], fields)
    return _envelope(
        "ok", keys={"transfer": _body_key(out["body"])}, body=out["body"], warnings=out["warnings"]
    )


async def post_journal_entry(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    require_write_scopes(policy, "ledger")
    out = await _post(client, WRITABLE["journal_entries"], fields)
    return _envelope(
        "ok",
        keys={"journal_entry": _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
    )


async def void_document(
    client: ManagerClient,
    policy: WritePolicy,
    resource: str,
    key: str,
) -> dict[str, Any]:
    w = WRITABLE.get(resource)
    if w is None or not w.implemented:
        raise ValueError(
            f"Unknown voidable resource {resource!r}. "
            f"Use a writable resource name (e.g. sales_invoices, receipts)."
        )
    require_delete_scope(policy, w.scope)
    path = f"{w.form_path}/{key}"
    body = await client.delete(path)
    return _envelope("ok", keys={resource: key}, body=body)


async def record_customer_deposit(
    client: ManagerClient,
    policy: WritePolicy,
    *,
    customer: str,
    amount: float,
    date: str,
    bank_account: str | None = None,
    reference: str | None = None,
    paid_by: int = 1,
    description: str | None = None,
) -> dict[str, Any]:
    require_write_scopes(policy, "banking")
    deposit_account = None
    if bank_account:
        deposit_account = bank_account
    else:
        found = await _find_deposit_bank_account(client)
        if found:
            deposit_account = str(found["Key"])
    if not deposit_account:
        return {
            "status": "precondition_failed",
            "preconditions": {
                "ok": False,
                "missing": [
                    {
                        "name": "deposit_bank_account",
                        "why": (
                            "Customer deposits must post to a dedicated bank/cash holding "
                            "account so they are not booked as revenue."
                        ),
                        "how_to_create": _DEPOSIT_ACCOUNT_GUIDE,
                    }
                ],
            },
            "keys": {},
            "warnings": [],
            "next_steps": [_DEPOSIT_ACCOUNT_GUIDE],
        }
    fields = _receipt_with_allocation(
        customer=customer,
        bank_account=deposit_account,
        date=date,
        amount=amount,
        invoice_key=None,
        reference=reference,
        paid_by=paid_by,
        description=description or "Customer deposit (not revenue)",
    )
    out = await _post(client, WRITABLE["receipts"], fields)
    return _envelope(
        "ok",
        keys={"receipt": _body_key(out["body"]), "deposit_account": deposit_account},
        body=out["body"],
        warnings=out["warnings"],
        next_steps=[
            "Deposit recorded. When the final invoice exists, call "
            "apply_deposit_to_invoice or allocate via journal entry."
        ],
    )


async def issue_deposit_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    require_write_scopes(policy, "quotes")
    body = dict(fields)
    desc = str(body.get("Description") or "")
    if "deposit" not in desc.casefold():
        body["Description"] = (desc + " - Deposit invoice (not revenue)").strip(" -")
    out = await _post(client, WRITABLE["sales_quotes"], body)
    return _envelope(
        "ok",
        keys={"sales_quote": _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
        next_steps=[
            "This is a quote styled as a deposit invoice, not a sales invoice. "
            "Call record_customer_deposit when cash is received."
        ],
    )


async def apply_deposit_to_invoice(
    client: ManagerClient,
    policy: WritePolicy,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Post a journal entry moving deposit balance to the sales invoice / AR."""
    require_write_scopes(policy, "ledger")
    out = await _post(client, WRITABLE["journal_entries"], fields)
    return _envelope(
        "ok",
        keys={"journal_entry": _body_key(out["body"])},
        body=out["body"],
        warnings=out["warnings"],
        next_steps=["Verify invoice balance and customer available credit with reads."],
    )
