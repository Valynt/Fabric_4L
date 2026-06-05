"""Regression coverage for Layer 1 metrics endpoint access control."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
L1_API_DIR = REPO_ROOT / "services" / "layer1-ingestion" / "src" / "layer1_ingestion" / "api"
L1_MAIN = L1_API_DIR / "main.py"
L1_ADMIN_ROUTES = L1_API_DIR / "main_admin_routes.py"
L1_MONOLITH = L1_API_DIR / "app_monolith.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    raise AssertionError(f"{function_name} not found")


@pytest.mark.security
def test_l1_registered_metrics_paths_are_inventoried() -> None:
    main_source = _source(L1_MAIN)
    admin_source = _source(L1_ADMIN_ROUTES)

    assert 'router = APIRouter(prefix="/api/v1/ingestion")' in main_source
    assert '"/metrics"' in admin_source
    assert "main.metrics_endpoint" in admin_source
    assert "Depends(require_authenticated)" in admin_source

    registered_paths = {"/api/v1/ingestion/metrics"}
    assert registered_paths == {"/api/v1/ingestion/metrics"}


@pytest.mark.security
@pytest.mark.parametrize("path", [L1_MAIN, L1_MONOLITH])
def test_l1_metrics_handler_verifies_metrics_access_before_reading_metrics(
    path: Path,
) -> None:
    source = _source(path)
    body = _function_body_source(source, "metrics_endpoint")

    assert "verify_metrics_access(request)" in body
    assert "get_metrics()" in body
    assert body.index("verify_metrics_access(request)") < body.index("get_metrics()")
    assert "Metrics endpoint requires internal access" in body
