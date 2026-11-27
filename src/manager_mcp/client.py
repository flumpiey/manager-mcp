"""Async httpx client for Manager.io API2 (GET always; writes scope-gated)."""

from __future__ import annotations

import mimetypes
import os
from typing import Any
from uuid import UUID

import httpx

from manager_mcp.attachments import action_url
from manager_mcp.scopes import WRITE_METHODS, WritePolicy

BASE_QUERY_KEYS = frozenset({"term", "sortBy", "sortByDesc", "skip", "pageSize", "fields"})


class ConfigError(ValueError):
    """Missing or invalid Manager connection configuration."""


class ManagerUnavailableError(RuntimeError):
    """Manager API unreachable (process down, wrong URL, network)."""


class ManagerApiError(RuntimeError):
    """Manager returned an HTTP error (especially 5xx from bad field types)."""


class ManagerClient:
    """httpx wrapper. GET always; mutations require WritePolicy authorization."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        policy: WritePolicy | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ConfigError("MANAGER_API_URL is required")
        if not api_key or not api_key.strip():
            raise ConfigError("MANAGER_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key.strip()
        self.policy = policy or WritePolicy(frozenset(), frozenset())
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-KEY": self._api_key},
            timeout=60.0,
        )

    @classmethod
    def from_env(
        cls,
        *,
        policy: WritePolicy | None = None,
    ) -> ManagerClient:
        return cls(
            os.environ.get("MANAGER_API_URL", ""),
            os.environ.get("MANAGER_API_KEY", ""),
            policy=policy if policy is not None else WritePolicy.from_env(),
        )

    @staticmethod
    def clean_params(
        params: dict[str, Any] | None, extra_keys: frozenset[str] = frozenset()
    ) -> dict[str, Any]:
        if not params:
            return {}
        allowed = BASE_QUERY_KEYS | extra_keys
        return {k: v for k, v in params.items() if k in allowed and v is not None}

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        extra_keys: frozenset[str] = frozenset(),
    ) -> Any:
        return await self._send("GET", path, params=self.clean_params(params, extra_keys))

    async def post(self, path: str, *, json: Any = None) -> Any:
        return await self._send("POST", path, json=json)

    async def put(self, path: str, *, json: Any = None) -> Any:
        return await self._send("PUT", path, json=json)

    async def patch(self, path: str, *, json: Any = None) -> Any:
        return await self._send("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self._send("DELETE", path)

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        method = method.upper()
        url_path = path if path.startswith("/") else f"/{path}"
        # Keys from the model land in the path; block traversal to unlisted endpoints.
        if any(seg in {".", ".."} or "%" in seg or "\\" in seg for seg in url_path.split("/")):
            raise ValueError(f"Invalid path or key: {url_path!r}")
        if method in WRITE_METHODS:
            self.policy.authorize(method, url_path)
        try:
            response = await self._client.request(
                method,
                url_path,
                params=params or None,
                json=json,
            )
        except httpx.RequestError as exc:
            # Keep MCP alive when Manager desktop/API is closed.
            hint = (
                " The write may have saved: check with list_records before any retry."
                if method in WRITE_METHODS
                else ""
            )
            raise ManagerUnavailableError(
                f"Manager.io is not reachable at {self.base_url}. "
                f"Ask the user to open Manager (with API enabled) and retry.{hint} "
                f"Detail: {exc}"
            ) from exc
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            snippet = (exc.response.text or "")[:200]
            if status >= 500:
                raise ManagerApiError(
                    f"Manager HTTP {status} for {method} {url_path}. "
                    "Usually a bad field name or type (e.g. PaidBy must be int; "
                    "use ReceivedIn/PaidFrom not BankAccount). "
                    "get_record a template, fix the body, retry once. "
                    f"Body: {snippet}"
                ) from exc
            raise
        if not response.content:
            return None
        return response.json()

    async def upload_attachment(self, invoice_key: str, file_name: str, data: bytes) -> None:
        """Attach a file to a purchase invoice through Manager's internal upload route.

        Scope-checked like any purchase invoice write. Needs a Manager user login,
        because the route ignores X-API-KEY. Manager returns nothing to read back.
        """
        key = str(UUID(invoice_key))
        self.policy.authorize("POST", f"/purchase-invoice-form/{key}")
        username = os.environ.get("MANAGER_UI_USERNAME", "").strip()
        password = os.environ.get("MANAGER_UI_PASSWORD", "").strip()
        if not username or not password:
            raise ConfigError(
                "MANAGER_UI_USERNAME and MANAGER_UI_PASSWORD are required to upload attachments."
            )
        envelope = await self.get("/purchase-invoices", params={"pageSize": 1})
        business = (envelope or {}).get("business") if isinstance(envelope, dict) else None
        business_name = business.get("name") if isinstance(business, dict) else None
        if not business_name:
            raise ManagerApiError("Could not read the business name from /purchase-invoices.")
        root = self.base_url.rsplit("/api2", 1)[0]
        url = action_url(root, "NewAttachment", business_name, key)
        mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        try:
            response = await self._client.post(
                url,
                files={file_name: (file_name, data, mime)},
                auth=(username, password),
                follow_redirects=False,
            )
        except httpx.RequestError as exc:
            raise ManagerUnavailableError(
                f"Manager.io is not reachable at {root}. "
                f"The upload may have saved: check the invoice's Attachments tab. Detail: {exc}"
            ) from exc
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 300 or "text/html" in content_type:
            location = response.headers.get("location")
            raise ManagerApiError(
                f"Attachment upload got HTTP {response.status_code}"
                + (f", redirect to {location}" if location else "")
                + f", content-type {content_type!r}. No attachment was confirmed. "
                "A redirect usually means the Manager user login was refused."
            )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


__all__ = [
    "BASE_QUERY_KEYS",
    "ConfigError",
    "ManagerApiError",
    "ManagerClient",
    "ManagerUnavailableError",
]
