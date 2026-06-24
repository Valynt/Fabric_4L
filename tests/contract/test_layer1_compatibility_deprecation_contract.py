from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_layer1_compatibility_routes_emit_deprecation_telemetry_contract() -> None:
    module = _load_module(
        REPO_ROOT
        / "services"
        / "layer1-ingestion"
        / "src"
        / "layer1_ingestion"
        / "api"
        / "routes"
        / "compatibility.py"
    )
    source = ast.unparse(module)

    assert "legacy_route_deprecation_usage" in source
    assert "_DEPRECATION_REMOVAL_DATE = '2026-07-15'" in source
    assert "response.headers['Deprecation'] = 'true'" in source
    assert "response.headers['Sunset'] = _DEPRECATION_REMOVAL_DATE" in source


def test_frontend_uses_canonical_command_center_route_only() -> None:
    source = (REPO_ROOT / "apps" / "web" / "src" / "shell" / "router.tsx").read_text(encoding="utf-8")

    assert 'path: "/command-center"' in source
    assert 'path: "/context/command-center"' not in source
