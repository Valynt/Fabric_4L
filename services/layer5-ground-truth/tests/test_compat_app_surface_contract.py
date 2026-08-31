"""Layer-5 compat-surface contract tests (brooks R3).

Route collectors and middleware helpers are centralized in the shared harness
``tests/contract/compat_surface/harness.py``; this file keeps only the
layer-specific assertions that are not already covered by the shared helpers.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

from layer5_ground_truth.api.main import (
    Layer3ClientError,
    Layer3PolicyDeniedError,
    Layer3TenantMismatchError,
    create_app,
)

# The repo-root ``tests`` package is shadowed by this layer's own ``tests``
# package (it has an ``__init__.py``), so the shared harness is loaded from
# its absolute path instead of via ``from tests.contract...``.
_HARNESS_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "contract"
    / "compat_surface"
    / "harness.py"
)
_spec = importlib.util.spec_from_file_location("_compat_surface_harness", _HARNESS_PATH)
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)

collect_paths = _harness.collect_paths
get_middleware_names = _harness.get_middleware_names


def test_l5_middleware_registration_and_effective_wrapping_order():
    app = create_app()

    middleware_names = get_middleware_names(app)
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

    paths = collect_paths(app.routes)
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
