"""Receipt attachment upload (respx; no live Manager)."""

from __future__ import annotations

import base64

import httpx
import pytest
import respx

from manager_mcp.attachments import action_url
from manager_mcp.client import ConfigError, ManagerApiError, ManagerClient
from manager_mcp.scopes import WritePolicy, WritesDeniedError
from manager_mcp.task_tools import attach_receipt_to_purchase_invoice

BASE = "http://m.test/api2"
KEY = "6d4af96a-0959-4bb2-9160-fa825ec67c43"
UPLOAD = "http://m.test/new-attachment?ogYHVGVzdCBDbwoSCWr5Sm1ZCbJLEZFg-oJexnxD"
CONTENT = base64.b64encode(b"receipt bytes").decode()


@pytest.fixture(autouse=True)
def _login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_UI_USERNAME", "mcp-user")
    monkeypatch.setenv("MANAGER_UI_PASSWORD", "s3cret-pass")


def _client(scopes: frozenset[str] = frozenset({"purchases"})) -> ManagerClient:
    return ManagerClient(BASE, "k", policy=WritePolicy(scopes, frozenset()))


def _mock_invoice_and_business() -> None:
    respx.get(f"{BASE}/purchase-invoice-form/{KEY}").mock(
        return_value=httpx.Response(200, json={"Key": KEY})
    )
    respx.get(f"{BASE}/purchase-invoices").mock(
        return_value=httpx.Response(200, json={"business": {"name": "Test Co"}})
    )


def test_action_url_matches_known_encoding() -> None:
    assert action_url("http://m.test", "NewAttachment", "Test Co", KEY) == UPLOAD
    with pytest.raises(ValueError, match="127"):
        action_url("http://m.test", "NewAttachment", "x" * 128, KEY)


@pytest.mark.asyncio
@respx.mock
async def test_upload_sends_file_with_login_and_reports_unverified() -> None:
    _mock_invoice_and_business()
    upload = respx.post(UPLOAD).mock(return_value=httpx.Response(200))
    client = _client()
    out = await attach_receipt_to_purchase_invoice(
        client, client.policy, KEY, "C:\\scans\\receipt.pdf", CONTENT
    )
    request = upload.calls.last.request
    assert request.headers["authorization"].startswith("Basic ")
    assert b'filename="receipt.pdf"' in request.content
    assert b"receipt bytes" in request.content
    assert out["status"] == "unverified"
    assert out["keys"] == {"purchase_invoice": KEY, "file_name": "receipt.pdf"}


@pytest.mark.asyncio
@respx.mock
async def test_redirect_fails_without_echoing_password() -> None:
    _mock_invoice_and_business()
    respx.post(UPLOAD).mock(return_value=httpx.Response(302, headers={"location": "/"}))
    client = _client()
    with pytest.raises(ManagerApiError, match="HTTP 302, redirect to /") as err:
        await attach_receipt_to_purchase_invoice(client, client.policy, KEY, "r.pdf", CONTENT)
    assert "s3cret-pass" not in str(err.value)


@pytest.mark.asyncio
@respx.mock
async def test_upload_refused_without_purchases_scope() -> None:
    client = _client(frozenset({"sales"}))
    with pytest.raises(WritesDeniedError, match="purchases"):
        await attach_receipt_to_purchase_invoice(client, client.policy, KEY, "r.pdf", CONTENT)
    with pytest.raises(WritesDeniedError):
        await client.upload_attachment(KEY, "r.pdf", b"x")
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_missing_login_names_both_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MANAGER_UI_PASSWORD")
    _mock_invoice_and_business()
    client = _client()
    with pytest.raises(ConfigError, match="MANAGER_UI_USERNAME and MANAGER_UI_PASSWORD"):
        await attach_receipt_to_purchase_invoice(client, client.policy, KEY, "r.pdf", CONTENT)


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("key", "name", "content", "message"),
    [
        ("not-a-key", "r.pdf", CONTENT, "not a valid key"),
        (KEY, "  ", CONTENT, "file_name is empty"),
        (KEY, "r.pdf", "not base64!!", "not valid base64"),
        (KEY, "r.pdf", "", "file is empty"),
        (KEY, "r.pdf", "A" * (14 * 1024 * 1024), "byte limit"),
    ],
    ids=["bad-key", "empty-name", "bad-base64", "empty-file", "oversize"],
)
async def test_bad_input_sends_nothing(key: str, name: str, content: str, message: str) -> None:
    client = _client()
    with pytest.raises(ValueError, match=message):
        await attach_receipt_to_purchase_invoice(client, client.policy, key, name, content)
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_unknown_invoice_stops_before_upload() -> None:
    respx.get(f"{BASE}/purchase-invoice-form/{KEY}").mock(return_value=httpx.Response(404))
    upload = respx.post(UPLOAD)
    client = _client()
    with pytest.raises(ValueError, match="not found"):
        await attach_receipt_to_purchase_invoice(client, client.policy, KEY, "r.pdf", CONTENT)
    assert not upload.called
