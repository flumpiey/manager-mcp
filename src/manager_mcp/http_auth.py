"""Streamable HTTP transport + Google OAuth for remote MCP access.

Stdio (the default) has no transport-level auth of its own — the host process
controls who can launch it. Streamable HTTP is reachable over the network, so
it must authenticate every request. GoogleProvider (fastmcp>=2.0) implements
the MCP OAuth spec by delegating login to Google, but it authenticates *any*
Google account that completes login — it has no built-in allowlist. Manager
MCP is single-tenant, so AllowlistedGoogleProvider adds that check itself.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp.server.auth.providers.google import GoogleProvider
from mcp.server.auth.provider import AccessToken

TRANSPORT_ENV = "MANAGER_MCP_TRANSPORT"
HOST_ENV = "MANAGER_MCP_HTTP_HOST"
PORT_ENV = "MANAGER_MCP_HTTP_PORT"
CLIENT_ID_ENV = "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_ID"
CLIENT_SECRET_ENV = "MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET"
BASE_URL_ENV = "MANAGER_MCP_OAUTH_BASE_URL"
ALLOWED_EMAILS_ENV = "MANAGER_MCP_ALLOWED_EMAILS"
AUTH_SESSION_TIMEOUT_SECONDS = 365 * 24 * 60 * 60


class TransportConfigError(ValueError):
    """Invalid MANAGER_MCP_TRANSPORT / OAuth environment configuration."""


class AllowlistedGoogleProvider(GoogleProvider):
    """GoogleProvider that also rejects tokens whose email isn't allowlisted."""

    def __init__(self, *, allowed_emails: frozenset[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._allowed_emails = allowed_emails

    async def verify_token(self, token: str) -> AccessToken | None:
        access_token = await super().verify_token(token)
        if access_token is None:
            return None
        email = (access_token.claims or {}).get("email", "")
        if email.lower() not in self._allowed_emails:
            return None
        return access_token


def _split_csv(value: str) -> frozenset[str]:
    return frozenset(item.strip().lower() for item in value.split(",") if item.strip())


def build_run_kwargs(environ: dict[str, str] | None = None) -> dict[str, Any]:
    """kwargs for `mcp.run()`.

    Empty dict (stdio, fastmcp's default) unless MANAGER_MCP_TRANSPORT=http.
    """
    env = environ if environ is not None else os.environ
    transport = env.get(TRANSPORT_ENV, "stdio").strip().lower()
    if transport in ("", "stdio"):
        return {}
    if transport != "http":
        raise TransportConfigError(f"{TRANSPORT_ENV} must be 'stdio' or 'http', got {transport!r}")

    client_id = env.get(CLIENT_ID_ENV, "").strip()
    base_url = env.get(BASE_URL_ENV, "").strip()
    allowed_emails_raw = env.get(ALLOWED_EMAILS_ENV, "").strip()
    missing = [
        name
        for name, value in (
            (CLIENT_ID_ENV, client_id),
            (BASE_URL_ENV, base_url),
            (ALLOWED_EMAILS_ENV, allowed_emails_raw),
        )
        if not value
    ]
    if missing:
        raise TransportConfigError(
            f"{TRANSPORT_ENV}=http requires {', '.join(missing)} to be set."
        )

    auth = AllowlistedGoogleProvider(
        allowed_emails=_split_csv(allowed_emails_raw),
        client_id=client_id,
        client_secret=env.get(CLIENT_SECRET_ENV) or None,
        base_url=base_url,
        required_scopes=["openid", "email"],
        fastmcp_access_token_expiry_seconds=AUTH_SESSION_TIMEOUT_SECONDS,
    )
    return {
        "transport": "http",
        "host": env.get(HOST_ENV, "0.0.0.0").strip(),
        "port": int(env.get(PORT_ENV, "8080")),
        "auth": auth,
    }
