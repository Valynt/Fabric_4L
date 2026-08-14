from __future__ import annotations

import ast
import re
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
    assert "response.headers['Deprecation'] = 'true'" in source

    # D1: the sunset date is owned by docs/deprecation_register.json and read
    # through the shared loader. A hardcoded date here would let the runtime
    # advertise a removal date that the CI gate never sees.
    assert "response.headers['Sunset'] = _get_deprecation_removal_date()" in source
    assert "removal_date_for" in source
    assert "_DEPRECATION_REMOVAL_DATE" not in source
    assert not re.search(r"['\"]20\d\d-\d\d-\d\d['\"]", source), (
        "Layer 1 compatibility routes must not hardcode sunset dates; "
        "register them in docs/deprecation_register.json instead."
    )


def test_layer1_deprecation_register_is_read_through_canonical_loader() -> None:
    """Runtime startup warnings must consume the same register/schema as CI."""
    module = _load_module(
        REPO_ROOT
        / "services"
        / "layer1-ingestion"
        / "src"
        / "layer1_ingestion"
        / "api"
        / "main.py"
    )
    source = ast.unparse(module)

    assert "load_deprecation_items" in source
    # The register is keyed by ``items``; the historical ``deprecations`` key
    # produced a silently-empty register at runtime.
    assert "get('deprecations', [])" not in source
    assert "'deprecations': []" not in source


def test_frontend_uses_canonical_command_center_route_only() -> None:
    source = (REPO_ROOT / "apps" / "web" / "src" / "shell" / "router.tsx").read_text(encoding="utf-8")

    assert 'path: "/command-center"' in source
    assert 'path: "/context/command-center"' not in source
