"""Release metadata must carry one version, or the MCP Registry publish fails."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _toml_version(path: Path) -> str:
    return re.search(r'^version = "([^"]+)"', path.read_text(encoding="utf-8"), re.M).group(1)


def test_versions_match() -> None:
    version = _toml_version(ROOT / "pyproject.toml")
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))
    assert server["version"] == version
    assert all(p["version"] == version for p in server["packages"])
    assert manifest["version"] == version
    assert _toml_version(ROOT / "mcpb" / "pyproject.toml") == version
