"""Write opt-in gate and default read-only tool-set tests."""

from __future__ import annotations

import pytest

from manager_mcp.client import writes_enabled
from manager_mcp.server import mcp, register_write_tools

MUTATING_TOKENS = ("create", "update", "delete", "post", "put", "patch")


@pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
def test_writes_enabled_truthy(value: str) -> None:
    assert writes_enabled({"MANAGER_MCP_ALLOW_WRITES": value}) is True


@pytest.mark.parametrize("value", ["", "   ", "0", "maybe", "false"])
def test_writes_enabled_falsey(value: str) -> None:
    assert writes_enabled({"MANAGER_MCP_ALLOW_WRITES": value}) is False


def test_writes_enabled_unset() -> None:
    assert writes_enabled({}) is False


@pytest.mark.asyncio
async def test_default_tools_have_no_mutating_verbs() -> None:
    tools = await mcp.list_tools()
    names = [t.name.casefold() for t in tools]
    assert names, "expected curated tools to be registered"
    assert "api_write" not in names
    for name in names:
        for token in MUTATING_TOKENS:
            assert token not in name, f"mutating token {token!r} in tool {name!r}"


@pytest.mark.asyncio
async def test_register_write_tools_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGER_MCP_ALLOW_WRITES", "1")
    # Force re-register path: module may already have registered in another test.
    import manager_mcp.server as server

    server._write_tools_registered = False
    register_write_tools()
    names = {t.name for t in await mcp.list_tools()}
    assert "api_write" in names
