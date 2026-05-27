from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app


def test_l6_middleware_registration_and_effective_wrapping_order():
    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:3] == [
        "GovernanceMiddleware",
        "MetricsMiddleware",
        "SecurityMiddleware",
    ]


def test_l6_skip_validation_paths_contract():
    security_middleware = next(mw for mw in app.user_middleware if mw.cls.__name__ == "SecurityMiddleware")
    skip_paths = security_middleware.kwargs["config"].skip_validation_paths
    assert skip_paths == frozenset({"/health", "/ready", "/metrics"})


def test_l6_health_ready_metrics_route_contract_presence_and_payload_shape():
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/ready" in paths
    assert "/metrics" in paths

    with TestClient(app) as client:
        health = client.get("/health")

    assert health.status_code in {200, 503}
    payload = health.json()
    assert payload["service"] == "layer6-benchmarks"
    assert payload["status"] in {"healthy", "degraded", "unhealthy"}
