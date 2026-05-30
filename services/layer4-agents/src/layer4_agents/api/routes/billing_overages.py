from __future__ import annotations

"""Usage limit and overage billing routes."""

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
    response_model=billing.LimitsCheckResponse,
)
router.add_api_route(
    "/plans/{plan_id}/limits",
    billing.get_plan_limits,
    methods=["GET"],
    response_model=billing.get_plan_limitsResult,
)
