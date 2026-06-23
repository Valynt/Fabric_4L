"""Regression coverage for Layer 1 metrics endpoint access control."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
L1_API_DIR = REPO_ROOT / "services" / "layer1-ingestion" / "src" / "layer1_ingestion" / "api"
L1_MAIN = L1_API_DIR / "main.py"
L1_ADMIN_ROUTES = L1_API_DIR / "main_admin_routes.py"


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
@pytest.mark.parametrize("path", [L1_MAIN])
def test_l1_metrics_handler_verifies_metrics_access_before_reading_metrics(
    path: Path,
) -> None:
    source = _source(path)
    body = _function_body_source(source, "metrics_endpoint")

    assert "verify_metrics_access(request)" in body
    assert "get_metrics()" in body
    assert body.index("verify_metrics_access(request)") < body.index("get_metrics()")
    assert "Metrics endpoint requires internal access" in body


@pytest.mark.security
def test_l1_metrics_route_rejects_unauthenticated_request() -> None:
    from layer1_ingestion.api.main import app

    response = TestClient(app).get("/api/v1/ingestion/metrics")

    assert response.status_code in {401, 403}


class _MetricsStub:
    def get_metrics(self) -> str:
        return "# l1 metrics\n"


def _external_metrics_request(headers: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host="8.8.8.8"),
    )


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-token"},
        {"X-Prometheus-Scrape-Token": "wrong-token"},
    ],
)
async def test_l1_metrics_handler_denies_external_requests_without_valid_token(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    from layer1_ingestion.api import main

    monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "expected-token")
    monkeypatch.setattr(main, "get_metrics", lambda: _MetricsStub())

    with pytest.raises(main.AuthorizationError):
        await main.metrics_endpoint(_external_metrics_request(headers))


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer expected-token"},
        {"X-Prometheus-Scrape-Token": "expected-token"},
    ],
)
async def test_l1_metrics_handler_allows_external_requests_with_valid_token(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    from layer1_ingestion.api import main

    monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "expected-token")
    monkeypatch.setattr(main, "get_metrics", lambda: _MetricsStub())

    response = await main.metrics_endpoint(_external_metrics_request(headers))

    assert response.status_code == 200
    assert b"# l1 metrics" in response.body
