from __future__ import annotations

from src.api.main import app


def test_l6_middleware_registration_and_effective_wrapping_order():
    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:3] == [
        "GovernanceMiddleware",
        "SecurityMiddleware",
        "BaseHTTPMiddleware",
    ]


def test_l6_skip_validation_paths_contract():
    security_middleware = next(mw for mw in app.user_middleware if mw.cls.__name__ == "SecurityMiddleware")
    skip_paths = security_middleware.kwargs["config"].skip_validation_paths
    assert skip_paths == frozenset({"/health", "/ready", "/metrics"})


def test_l6_health_ready_metrics_route_contract_presence_and_shape():
    health_endpoint = next(route.endpoint for route in app.routes if route.path == "/health")
    ready_endpoint = next(route.endpoint for route in app.routes if route.path == "/ready")
    metrics_endpoint = next(route.endpoint for route in app.routes if route.path == "/metrics")

    assert callable(health_endpoint)
    assert callable(ready_endpoint)
    assert callable(metrics_endpoint)
