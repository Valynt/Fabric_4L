"""Layer-6 compat-surface contract tests (brooks R3).

Route collectors and middleware helpers are centralized in the shared harness
``tests/contract/compat_surface/harness.py``; this file keeps only the
layer-specific assertions that are not already covered by the shared helpers.
"""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient
from tests.contract.compat_surface.harness import collect_routes, get_middleware_names

from layer6_benchmarks.api.main import app


def test_l6_middleware_registration_and_effective_wrapping_order():
    middleware_names = get_middleware_names(app)
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:3] == [
        "GovernanceMiddleware",
        "SecurityMiddleware",
        "BaseHTTPMiddleware",
    ]


def test_l6_skip_validation_paths_contract():
    security_middleware = next(
        mw for mw in app.user_middleware if mw.cls.__name__ == "SecurityMiddleware"
    )
    skip_paths = security_middleware.kwargs["config"].skip_validation_paths
    assert skip_paths == frozenset({"/health", "/ready", "/metrics"})


def test_l6_health_ready_metrics_route_contract_presence_and_shape():
    routes = collect_routes(app.routes)
    health_endpoint = next(route.endpoint for route in routes if route.path == "/health")
    ready_endpoint = next(route.endpoint for route in routes if route.path == "/ready")
    metrics_endpoint = next(route.endpoint for route in routes if route.path == "/metrics")

    assert callable(health_endpoint)
    assert callable(ready_endpoint)
    assert callable(metrics_endpoint)


def test_l6_exception_handler_registrations_contract():
    handlers = app.exception_handlers
    assert HTTPException in handlers
    assert Exception in handlers


def test_l6_health_ready_metrics_response_contract():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code in {200, 503}
        health_payload = health.json()
        assert health_payload["service"] == "layer6-benchmarks"
        assert health_payload["status"] in {"healthy", "unhealthy", "degraded"}
        assert "timestamp" in health_payload

        ready = client.get("/ready")
        assert ready.status_code in {200, 503}
        ready_payload = ready.json()
        assert ready_payload["service"] == "layer6-benchmarks"
        assert ready_payload["status"] in {"ready", "not_ready", "degraded"}
        assert "checks" in ready_payload

        metrics = client.get("/metrics")
        assert metrics.status_code in {200, 403, 503}
        # Metrics endpoint returns JSON, not text/plain
        assert metrics.headers["content-type"].startswith("application/json")
