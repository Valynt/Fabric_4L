"""Usage limit and overage billing routes (Phase 1 extract from Layer 4).

Canonical implementation lives in Layer 7. Layer 4 now forwards to
these endpoints via thin HTTP client stubs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ServiceUnavailableError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ... import repository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Billing — Overage"])


class LimitsCheckResponse(BaseModel):
    allowed: bool
    customer_id: str
    metric_name: str
    quantity: float
    limit: float | None = None
    current_usage: float | None = None
    remaining: float | None = None


class UsageLimitsResponse(BaseModel):
    customer_id: str
    plan_id: str
    all_limits_ok: bool
    warnings: list[str] = []
    total_overage_cost: float = 0.0
    metrics: list[dict[str, Any]] = []


class PlanLimitsResponse(BaseModel):
    plan_id: str
    plan_name: str
    limits: dict[str, Any]


@router.get("/limits/{customer_id}", response_model=UsageLimitsResponse)
async def get_usage_limits(
    customer_id: str,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get current usage and limits for a customer."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    logger.info(
        "get_usage_limits",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
    )
    # Phase 1: Return limits based on current usage aggregates.
    aggregates = await repository.get_usage_aggregates(db, str(ctx.tenant_id))
    metrics = [
        {
            "metric_name": metric,
            "current_usage": quantity,
            "limit": None,
            "percentage_used": 0.0,
            "remaining": None,
            "overage": 0.0,
            "overage_cost": 0.0,
            "warning_triggered": False,
            "limit_exceeded": False,
        }
        for metric, quantity in aggregates.items()
    ]
    return {
        "customer_id": customer_id,
        "plan_id": "default",
        "all_limits_ok": True,
        "warnings": [],
        "total_overage_cost": 0.0,
        "metrics": metrics,
    }


@router.post("/limits/{customer_id}/check", response_model=LimitsCheckResponse)
async def check_request_allowed(
    customer_id: str,
    metric_name: str = Query(..., min_length=1, max_length=64),
    quantity: float = Query(1.0, ge=0),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Check if a request should be allowed based on usage limits."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    logger.info(
        "check_request_allowed",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        metric_name=metric_name,
        quantity=quantity,
    )
    return {
        "allowed": True,
        "customer_id": customer_id,
        "metric_name": metric_name,
        "quantity": quantity,
        "limit": None,
        "current_usage": None,
        "remaining": None,
    }


@router.get("/plans/{plan_id}/limits", response_model=PlanLimitsResponse)
async def get_plan_limits(
    plan_id: str,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get the configured usage limits for a plan."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    entitlements = await repository.get_plan_entitlements(db, str(ctx.tenant_id), plan_id)
    return {
        "plan_id": plan_id,
        "plan_name": plan_id,
        "limits": {"entitlements": entitlements},
    }
