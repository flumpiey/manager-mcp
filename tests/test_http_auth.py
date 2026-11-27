"""Transport selection and the email allowlist on top of GoogleProvider."""

from __future__ import annotations

import pytest

from manager_mcp.http_auth import TransportConfigError, build_run_kwargs


def test_default_is_stdio() -> None:
    assert build_run_kwargs({}) == {}
    assert build_run_kwargs({"MANAGER_MCP_TRANSPORT": "stdio"}) == {}


def test_unknown_transport_rejected() -> None:
    with pytest.raises(TransportConfigError, match="stdio.*http"):
        build_run_kwargs({"MANAGER_MCP_TRANSPORT": "sse"})


def test_http_requires_oauth_config() -> None:
    with pytest.raises(TransportConfigError, match="MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID"):
        build_run_kwargs({"MANAGER_MCP_TRANSPORT": "http"})


def test_http_requires_allowed_emails() -> None:
    with pytest.raises(TransportConfigError, match="MANAGER_MCP_ALLOWED_EMAILS"):
        build_run_kwargs(
            {
                "MANAGER_MCP_TRANSPORT": "http",
                "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
                "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
            }
        )


def test_http_builds_kwargs_with_defaults() -> None:
    kwargs = build_run_kwargs(
        {
            "MANAGER_MCP_TRANSPORT": "http",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET": "secret",
            "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
            "MANAGER_MCP_ALLOWED_EMAILS": "Me@Example.com, other@example.com",
        }
    )
    assert kwargs["transport"] == "http"
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8080
    auth = kwargs["auth"]
    assert auth._allowed_emails == frozenset({"me@example.com", "other@example.com"})


def test_http_respects_host_and_port_overrides() -> None:
    kwargs = build_run_kwargs(
        {
            "MANAGER_MCP_TRANSPORT": "http",
            "MANAGER_MCP_HTTP_HOST": "0.0.0.0",
            "MANAGER_MCP_HTTP_PORT": "9090",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET": "secret",
            "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
            "MANAGER_MCP_ALLOWED_EMAILS": "me@example.com",
        }
    )
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 9090


def test_http_auth_session_timeout_is_one_day() -> None:
    kwargs = build_run_kwargs(
        {
            "MANAGER_MCP_TRANSPORT": "http",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET": "secret",
            "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
            "MANAGER_MCP_ALLOWED_EMAILS": "me@example.com",
        }
    )
    assert kwargs["auth"]._fastmcp_access_token_expiry_seconds == 24 * 60 * 60


def test_http_requires_client_secret() -> None:
    with pytest.raises(TransportConfigError, match="MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET"):
        build_run_kwargs(
            {
                "MANAGER_MCP_TRANSPORT": "http",
                "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
                "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
                "MANAGER_MCP_ALLOWED_EMAILS": "me@example.com",
            }
        )


def test_http_mode_silences_url_logging() -> None:
    import logging

    logging.getLogger("httpx").setLevel(logging.INFO)
    build_run_kwargs(
        {
            "MANAGER_MCP_TRANSPORT": "http",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID": "client-id",
            "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET": "secret",
            "MANAGER_MCP_OAUTH_BASE_URL": "https://manager-mcp.example.com",
            "MANAGER_MCP_ALLOWED_EMAILS": "me@example.com",
        }
    )
    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)


@pytest.mark.asyncio
async def test_verify_token_rejects_email_outside_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mcp.server.auth.provider import AccessToken

    from manager_mcp.http_auth import AllowlistedGoogleProvider

    provider = AllowlistedGoogleProvider(
        allowed_emails=frozenset({"allowed@example.com"}),
        client_id="client-id",
        client_secret="secret",
        base_url="https://manager-mcp.example.com",
    )

    def fake_verify(token: str, *, email: str, verified: bool = True) -> AccessToken:
        return AccessToken(
            token=token,
            client_id="client-id",
            scopes=["openid", "email"],
            claims={"email": email, "email_verified": verified},
        )

    async def verify_allowed(self: object, token: str) -> AccessToken | None:
        return fake_verify(token, email="allowed@example.com")

    async def verify_denied(self: object, token: str) -> AccessToken | None:
        return fake_verify(token, email="stranger@example.com")

    from fastmcp.server.auth.providers.google import GoogleProvider

    monkeypatch.setattr(GoogleProvider, "verify_token", verify_allowed)
    assert (await provider.verify_token("tok")) is not None

    monkeypatch.setattr(GoogleProvider, "verify_token", verify_denied)
    assert (await provider.verify_token("tok")) is None

    async def verify_unverified(self: object, token: str) -> AccessToken | None:
        return fake_verify(token, email="allowed@example.com", verified=False)

    monkeypatch.setattr(GoogleProvider, "verify_token", verify_unverified)
    assert (await provider.verify_token("tok")) is None

    # Real tokeninfo responses carry the string "true", not a bool.
    async def verify_string_true(self: object, token: str) -> AccessToken | None:
        return fake_verify(token, email="allowed@example.com", verified="true")  # type: ignore[arg-type]

    monkeypatch.setattr(GoogleProvider, "verify_token", verify_string_true)
    assert (await provider.verify_token("tok")) is not None
