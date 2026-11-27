"""Probe Manager API2/API4 for custom button list, form, and invoke paths."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _load_dotenv() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in (".env",):
        path = root / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _api4_base(api2_url: str) -> str:
    explicit = os.environ.get("MANAGER_API4_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    parsed = urlparse(api2_url)
    path = parsed.path.rstrip("/")
    if path.casefold().endswith("/api2"):
        path = path[: -len("/api2")] + "/api4"
    else:
        path = path + "/api4"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _find_paths_in_openapi(spec: Any, needle: str) -> list[str]:
    paths: list[str] = []
    if not isinstance(spec, dict):
        return paths
    raw_paths = spec.get("paths") or {}
    if not isinstance(raw_paths, dict):
        return paths
    for path in raw_paths:
        if needle in path.casefold():
            paths.append(path)
    return sorted(paths)


async def main() -> None:
    _load_dotenv()
    api2 = os.environ.get("TEST_MANAGER_API_URL") or os.environ.get("MANAGER_API_URL", "")
    key = os.environ.get("TEST_MANAGER_API_KEY") or os.environ.get("MANAGER_API_KEY", "")
    if not api2 or not key:
        raise SystemExit("Set TEST_MANAGER_API_URL + TEST_MANAGER_API_KEY (or MANAGER_*) in .env")

    import httpx

    headers = {"X-API-KEY": key}
    api4 = _api4_base(api2)
    report: dict[str, Any] = {
        "api2_base": api2.rstrip("/"),
        "api4_base": api4,
        "api2_openapi_custom_button_paths": [],
        "api4_openapi_custom_button_paths": [],
        "api2_list_probe": {},
        "api2_form_probe": {},
        "api4_custom_button_probe": {},
        "invoke_candidates": [],
    }

    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        for label, base in (("api2", api2.rstrip("/")), ("api4", api4)):
            try:
                resp = await client.get(base)
                report[f"{label}_root_status"] = resp.status_code
                if resp.status_code == 200:
                    try:
                        spec = resp.json()
                        report[f"{label}_openapi_custom_button_paths"] = _find_paths_in_openapi(
                            spec, "custom-button"
                        )
                        report[f"{label}_openapi_custom_button_paths"].extend(
                            _find_paths_in_openapi(spec, "custombutton")
                        )
                        report[f"{label}_openapi_custom_button_paths"] = sorted(
                            set(report[f"{label}_openapi_custom_button_paths"])
                        )
                    except json.JSONDecodeError:
                        report[f"{label}_root_body_sample"] = resp.text[:500]
            except httpx.RequestError as exc:
                report[f"{label}_root_error"] = str(exc)

        list_paths = ["/custom-buttons", "/custom-button"]
        for list_path in list_paths:
            try:
                resp = await client.get(
                    f"{api2.rstrip('/')}{list_path}", params={"skip": 0, "pageSize": 5}
                )
                body = resp.json() if resp.status_code == 200 else resp.text[:300]
                report["api2_list_probe"][list_path] = {
                    "status": resp.status_code,
                    "envelope_keys": list(body.keys()) if isinstance(body, dict) else None,
                }
                if isinstance(body, dict):
                    for k, v in body.items():
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            report["api2_list_probe"][list_path]["items_key"] = k
                            report["api2_list_probe"][list_path]["item_keys"] = sorted(v[0].keys())
                            item_key = v[0].get("Key") or v[0].get("key")
                            if item_key:
                                form_path = f"/custom-button-form/{item_key}"
                                form_resp = await client.get(f"{api2.rstrip('/')}{form_path}")
                                form_body = (
                                    form_resp.json()
                                    if form_resp.status_code == 200
                                    else {"error": form_resp.text[:200]}
                                )
                                report["api2_form_probe"][form_path] = {
                                    "status": form_resp.status_code,
                                    "header_keys": sorted(form_body.keys())
                                    if isinstance(form_body, dict)
                                    else None,
                                }
                            break
            except httpx.RequestError as exc:
                report["api2_list_probe"][list_path] = {"error": str(exc)}

        try:
            resp = await client.get(f"{api4}/custom-button")
            report["api4_custom_button_probe"]["GET_/custom-button"] = {
                "status": resp.status_code,
                "body_keys": sorted(resp.json().keys())
                if resp.status_code == 200
                else resp.text[:200],
            }
        except httpx.RequestError as exc:
            report["api4_custom_button_probe"]["GET_error"] = str(exc)

        try:
            resp = await client.post(
                f"{api4}/custom-button",
                json={
                    "value": {
                        "name": "MCP probe button",
                        "text": "MCP probe",
                        "placement": "form",
                        "inactive": True,
                    }
                },
            )
            report["api4_custom_button_probe"]["POST_/custom-button"] = {
                "status": resp.status_code,
                "body": resp.json() if resp.content else None,
            }
            if resp.status_code in (200, 201) and resp.content:
                created = resp.json()
                btn_key = None
                if isinstance(created, dict):
                    val = created.get("value") or created
                    btn_key = val.get("key") or val.get("Key") or created.get("key")
                if btn_key:
                    del_resp = await client.delete(f"{api4}/custom-button/{btn_key}")
                    report["api4_custom_button_probe"]["DELETE_cleanup"] = del_resp.status_code
        except httpx.RequestError as exc:
            report["api4_custom_button_probe"]["POST_error"] = str(exc)

        all_paths = report.get("api2_openapi_custom_button_paths", []) + report.get(
            "api4_openapi_custom_button_paths", []
        )
        for path in all_paths:
            if re.search(r"invoke|run|execute|click", path, re.I):
                report["invoke_candidates"].append(path)

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
