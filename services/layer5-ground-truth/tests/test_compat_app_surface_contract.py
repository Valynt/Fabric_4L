from __future__ import annotations

import asyncio

from fastapi import HTTPException
from starlette.requests import Request

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
    assert "CORSMiddleware" not in middleware_names
    assert middleware_names[:6] == [
        "GovernanceMiddleware",
        "BaseHTTPMiddleware",
        "SecurityMiddleware",
        "BaseHTTPMiddleware",
        "_TenantEnforcementMiddleware",
        "RequestIDMiddleware",
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


def test_l5_health_ready_metrics_route_contract_presence():
    app = create_app()

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/ready" in paths
    assert "/metrics" in paths


def test_l5_exception_handler_shape_semantics_for_custom_and_catchall():
    app = create_app()
    handlers = app.exception_handlers
    scope = {"type": "http", "headers": [], "method": "GET", "path": "/compat-check"}
    request = Request(scope)

    policy_exc = Layer3PolicyDeniedError("policy denied", tenant_id="tenant-a")
    policy_response = asyncio.run(handlers[Layer3PolicyDeniedError](request, policy_exc))
    policy_payload = policy_response.body.decode("utf-8")
    assert policy_response.status_code == policy_exc.status_code
    assert '"code":"L5_LAYER3_POLICY_DENIED"' in policy_payload
    assert '"trace_id"' in policy_payload

    catch_all_response = asyncio.run(handlers[Exception](request, Exception("boom")))
    catch_all_payload = catch_all_response.body.decode("utf-8")
    assert catch_all_response.status_code == 500
    assert '"error"' in catch_all_payload
    assert '"code":"INTERNAL_ERROR"' in catch_all_payload
