"""Characterization tests for Layer 3 FastAPI application composition and startup."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from src.api.main import (
    app,
    _init_cache,
    _init_metrics,
    _init_versioning,
    _verify_production_vault,
    value_fabric_exception_handler,
    global_exception_handler,
)
from src.api.exceptions import ValidationError, ServiceUnavailableError


def _collect_paths(routes, prefix: str = ""):
    paths = set()
    for route in routes:
        if isinstance(route, APIRoute):
            paths.add(prefix + route.path)
        elif hasattr(route, "original_router"):
            paths.update(
                _collect_paths(route.original_router.routes, prefix + (getattr(getattr(route, "include_context", None), "prefix", "") or getattr(route, "path", "") or ""))
            )
        elif hasattr(route, "routes"):
            paths.update(_collect_paths(route.routes, prefix + (getattr(getattr(route, "include_context", None), "prefix", "") or getattr(route, "path", "") or "")))
    return paths


def test_app_exposes_expected_domain_routes():
    """Verify all critical Layer 3 domain routes are mounted."""
    route_paths = _collect_paths(app.routes)
    
    # Check operational routes
    assert "/health" in route_paths
    assert "/ready" in route_paths

    # Check key domain routes
    assert any("/models" in p for p in route_paths)
    assert any("/entities" in p for p in route_paths)
    assert any("/formulas" in p for p in route_paths)
    assert any("/signals" in p for p in route_paths)
    assert any("/variables" in p for p in route_paths)
    assert any("/provenance" in p for p in route_paths)


def test_init_cache_disabled():
    settings = MagicMock(cache_enabled=False)
    assert _init_cache(settings) is None


def test_init_metrics_disabled():
    mock_app = MagicMock()
    settings = MagicMock(metrics_enabled=False)
    assert _init_metrics(mock_app, settings) is None


def test_init_versioning():
    vc = _init_versioning()
    assert vc is not None


@pytest.mark.asyncio
async def test_verify_production_vault_healthy():
    with patch.dict("os.environ", {"ENVIRONMENT": "production", "VAULT_ADDR": "http://vault:8200"}), \
         patch("src.api.main.is_vault_healthy", return_value=True):
        await _verify_production_vault()


@pytest.mark.asyncio
async def test_verify_production_vault_unhealthy_raises():
    with patch.dict("os.environ", {"ENVIRONMENT": "production", "VAULT_ADDR": "http://vault:8200"}), \
         patch("src.api.main.is_vault_healthy", return_value=False):
        with pytest.raises(RuntimeError, match="Vault unreachable"):
            await _verify_production_vault()


@pytest.mark.asyncio
async def test_value_fabric_exception_handler_formatting():
    req = MagicMock()
    req.method = "GET"
    req.url.path = "/test"
    req.state.trace_id = "trace-1"
    req.app.state.metrics = None

    exc = ValidationError(message="Invalid query parameter")
    resp = await value_fabric_exception_handler(req, exc)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_global_exception_handler_formatting():
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/test"
    req.state.request_id = "req-123"
    req.app.state.metrics = None

    exc = RuntimeError("Unexpected failure")
    resp = await global_exception_handler(req, exc)
    assert resp.status_code == 500
