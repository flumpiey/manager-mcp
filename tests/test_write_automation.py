"""Custom button write validation (respx; no live Manager)."""

from __future__ import annotations

import httpx
import pytest
import respx

from manager_mcp.client import ManagerClient
from manager_mcp.scopes import WritePolicy
from manager_mcp.server import _make_create_tool, reset_client
from manager_mcp.writable import WRITABLE
from manager_mcp.write_validate import normalize_write_body, validate_write_body

BASE = "http://example.test/api2"

VALID_BUTTON = {
    "Name": "Agent button",
    "Text": "Run",
    "Placement": "form",
    "inactive": True,
    "endpoint": "https://example.com/hook",
    "html": "<button>Run</button>",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_API_URL", BASE)
    monkeypatch.setenv("MANAGER_API_KEY", "k")
    monkeypatch.setenv("MANAGER_MCP_WRITE_SCOPES", "automation")
    monkeypatch.setenv("MANAGER_MCP_DELETE_SCOPES", "automation")
    for name in ("MANAGER_MCP_ALLOW_WRITES", "ALLOW_WRITES", "MANAGER_MCP_WRITES"):
        monkeypatch.delenv(name, raising=False)
    reset_client()
    yield
    reset_client()


def test_normalize_custom_button_aliases() -> None:
    out = normalize_write_body(WRITABLE["custom_buttons"], dict(VALID_BUTTON))
    assert out["Endpoint"] == "https://example.com/hook"
    assert out["Html"] == "<button>Run</button>"
    assert out["Inactive"] is True
    assert "endpoint" not in out


def test_unknown_custom_button_field_rejected() -> None:
    body = {**VALID_BUTTON, "NotAField": 1}
    with pytest.raises(ValueError, match="unknown field"):
        validate_write_body(WRITABLE["custom_buttons"], body, creating=True)


@pytest.mark.asyncio
@respx.mock
async def test_create_custom_button_happy_path() -> None:
    key = "11111111-1111-1111-1111-111111111111"
    persisted = {
        "Key": key,
        "Name": "Agent button",
        "Endpoint": "https://example.com/hook",
        "Html": "<button>Run</button>",
        "Inactive": True,
        "Placement": "form",
        "text": "Agent button",
    }
    respx.post(f"{BASE}/custom-button-form").mock(
        return_value=httpx.Response(201, json={"Key": key, **persisted})
    )
    respx.get(f"{BASE}/custom-button-form/{key}").mock(
        return_value=httpx.Response(200, json=persisted)
    )
    create = _make_create_tool("custom_buttons")
    out = await create(dict(VALID_BUTTON))
    assert out["body"]["Key"] == key
    assert out["warnings"] == []


def test_client_api4_base_derived() -> None:
    client = ManagerClient(
        "http://127.0.0.1:55339/api2",
        "k",
        policy=WritePolicy(frozenset({"automation"}), frozenset()),
    )
    assert client.api4_base_url == "http://127.0.0.1:55339/api4"
