from __future__ import annotations

from fastapi import HTTPException

from layer5_ground_truth.api.main import (
    Layer3ClientError,
    Layer3PolicyDeniedError,
    Layer3TenantMismatchError,
    create_app,
)


def test_l5_middleware_registration_and_effective_wrapping_order():
    app = create_app()

    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:4] == [
        "CORSMiddleware",
        "MetricsMiddleware",
        "SecurityMiddleware",
        "GovernanceMiddleware",
    ]


def test_l5_exception_handler_registrations_and_custom_shape_contracts():
    app = create_app()

    handlers = app.exception_handlers
    assert Layer3PolicyDeniedError in handlers
    assert Layer3TenantMismatchError in handlers
    assert Layer3ClientError in handlers
    assert HTTPException in handlers
    assert Exception in handlers

    assert handlers[Layer3PolicyDeniedError].__name__ == "layer3_security_exception_handler"
    assert handlers[Layer3TenantMismatchError].__name__ == "layer3_security_exception_handler"
    assert handlers[Layer3ClientError].__name__ == "layer3_operational_exception_handler"


def test_l5_health_ready_metrics_route_contract_presence_and_signatures():
    app = create_app()

    route_map = {route.path: route for route in app.routes}
    assert "/health" in route_map
    assert "/ready" in route_map
    assert "/metrics" in route_map

    assert route_map["/health"].methods == {"GET"}
    assert route_map["/ready"].methods == {"GET"}
    assert route_map["/metrics"].methods == {"GET"}
