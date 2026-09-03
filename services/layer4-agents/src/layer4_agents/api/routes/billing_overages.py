"""Entitlement and usage-limit billing routes.

Layer 4 is the canonical billing runtime; there is no separate Layer 7
Billing Service. The handlers registered here are re-exported from the
local ``billing`` module (OverageService, UsageService). Patch this
service, not a Layer 7 package.
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
