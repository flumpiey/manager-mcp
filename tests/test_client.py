"""GET-only ManagerClient tests (respx; no live Manager)."""

from __future__ import annotations

import httpx
import pytest
import respx

from manager_mcp.client import ConfigError, ManagerClient


def test_from_env_missing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MANAGER_API_URL", raising=False)
    monkeypatch.setenv("MANAGER_API_KEY", "k")
    with pytest.raises(ConfigError, match="MANAGER_API_URL"):
        ManagerClient.from_env()


def test_from_env_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_API_URL", "http://example.test/api2")
    monkeypatch.delenv("MANAGER_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="MANAGER_API_KEY"):
        ManagerClient.from_env()


def test_clean_params_drops_unknown() -> None:
    client = ManagerClient("http://example.test/api2", "secret")
    cleaned = client.clean_params(
        {
            "term": "acme",
            "skip": 0,
            "pageSize": 50,
            "evil": "drop-me",
            "sortBy": "Name",
            "sortByDesc": True,
            "fields": "Key,Name",
        }
    )
    assert cleaned == {
        "term": "acme",
        "skip": 0,
        "pageSize": 50,
        "sortBy": "Name",
        "sortByDesc": True,
        "fields": "Key,Name",
    }
    assert "evil" not in cleaned


def test_clean_params_allows_configured_date_keys() -> None:
    client = ManagerClient(
        "http://example.test/api2",
        "secret",
        extra_query_keys=frozenset({"from", "to"}),
    )
    cleaned = client.clean_params({"from": "2024-01-01", "to": "2024-12-31", "nope": 1})
    assert cleaned == {"from": "2024-01-01", "to": "2024-12-31"}


@pytest.mark.asyncio
async def test_write_methods_blocked_by_default() -> None:
    from manager_mcp.client import WritesDisabledError

    client = ManagerClient("http://example.test/api2", "secret", allow_writes=False)
    with pytest.raises(WritesDisabledError):
        await client.post("/customer-form", json={"Name": "x"})


@pytest.mark.asyncio
@respx.mock
async def test_post_when_writes_allowed() -> None:
    route = respx.post("http://example.test/api2/customer-form").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = ManagerClient("http://example.test/api2", "secret", allow_writes=True)
    assert await client.post("/customer-form", json={"Name": "x"}) == {"ok": True}
    assert route.called
    await client.aclose()


def test_writes_enabled_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from manager_mcp.client import writes_enabled

    monkeypatch.setenv("MANAGER_MCP_ALLOW_WRITES", "true")
    assert writes_enabled() is True
    monkeypatch.delenv("MANAGER_MCP_ALLOW_WRITES", raising=False)
    assert writes_enabled() is False


@pytest.mark.asyncio
@respx.mock
async def test_get_sends_api_key_header() -> None:
    route = respx.get("http://example.test/api2/customers").mock(
        return_value=httpx.Response(200, json=[{"Key": "1"}])
    )
    client = ManagerClient("http://example.test/api2", "super-secret")
    data = await client.get("/customers")
    assert data == [{"Key": "1"}]
    assert route.called
    assert route.calls.last.request.headers["X-API-KEY"] == "super-secret"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_http_error_propagates() -> None:
    respx.get("http://example.test/api2/customers").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )
    client = ManagerClient("http://example.test/api2", "bad")
    with pytest.raises(httpx.HTTPStatusError):
        await client.get("/customers")
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_empty_body_returns_none() -> None:
    respx.get("http://example.test/api2/empty").mock(
        return_value=httpx.Response(200, content=b"")
    )
    client = ManagerClient("http://example.test/api2", "k")
    assert await client.get("/empty") is None
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_filters_query_params() -> None:
    route = respx.get("http://example.test/api2/customers").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = ManagerClient("http://example.test/api2", "k")
    await client.get("/customers", params={"term": "x", "inject": "no"})
    assert route.calls.last.request.url.params.get("term") == "x"
    assert "inject" not in route.calls.last.request.url.params
    await client.aclose()
