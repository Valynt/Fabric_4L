"""Phase 1 forwarding stub — canonical implementation now in layer7-billing.

Layer 4 retains this shim for backward compatibility. All calls are
forwarded to the Layer 7 Billing Service via HTTP client stubs.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import billing

router = APIRouter()

router.add_api_route(
    "/limits/{customer_id}",
    billing.get_usage_limits,
    methods=["GET"],
    response_model=billing.get_usage_limitsResult,
)
router.add_api_route(
    "/limits/{customer_id}/check",
    billing.check_request_allowed,
    methods=["POST"],
)
router.add_api_route(
    "/plans/{plan_id}/limits",
    billing.get_plan_limits,
    methods=["GET"],
    response_model=billing.get_plan_limitsResult,
)
