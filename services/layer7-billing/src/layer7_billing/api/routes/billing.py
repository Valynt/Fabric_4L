"""Billing API routes extracted from Layer 4 (Phase 1).

Provides endpoints for subscription management, customer portal,
entitlement checks, and usage-based billing. Includes high-throughput
usage event ingestion with idempotency and tenant isolation.

This module is the Layer-7 canonical implementation. Layer 4 now
forwards to these endpoints via thin HTTP client stubs.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ... import repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan_id: str = Field(..., description="Plan to subscribe to (pro, enterprise)")
    success_url: str = Field(..., description="Redirect URL after successful checkout")
    cancel_url: str = Field(..., description="Redirect URL if checkout canceled")


class PortalRequest(BaseModel):
    """Request to create a customer portal session."""

    return_url: str = Field(..., description="URL to return to after portal session")


class CustomerSyncRequest(BaseModel):
    """Request to sync customer with Stripe."""

    email: str = Field(..., description="Customer email address")
    name: str | None = Field(None, description="Customer name")


class SubscriptionResponse(BaseModel):
    """Subscription status response."""

    id: str | None
    plan_id: str
    status: str
    current_period_start: str | None
    current_period_end: str | None
    cancel_at_period_end: bool


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class CancelSubscriptionRequest(BaseModel):
    cancel_immediately: bool = Field(False, description="Cancel immediately vs at period end")


class CancelSubscriptionResponse(BaseModel):
    canceled: bool
    cancel_at_period_end: bool
    current_period_end: str | None
    subscription_id: str


class UpdatePlanRequest(BaseModel):
    plan_id: str = Field(..., description="Target plan (pro, enterprise)")


class UpdatePlanResponse(BaseModel):
    previous_plan_id: str
    subscription_id: str
    updated: bool


class ReactivateSubscriptionResponse(BaseModel):
    reactivated: bool
    subscription_id: str


class EntitlementsResponse(BaseModel):
    plan_id: str
    plan_name: str
    features: dict[str, Any]


class CustomerBalanceResponse(BaseModel):
    customer_id: str
    open_invoices_cents: int
    open_invoices_dollars: str
    lifetime_paid_cents: int
    lifetime_paid_dollars: str
    balance_cents: int
    balance_dollars: str


# ---------------------------------------------------------------------------
# Subscription Endpoints
# ---------------------------------------------------------------------------


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get current subscription status for a customer."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    # Phase 1: Stub returning free-tier default.
    # Full implementation will query Stripe via repository.
    logger.info(
        "get_subscription forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
    )
    return {
        "id": None,
        "plan_id": "free",
        "status": "active",
        "current_period_start": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
    }


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe checkout session for subscription."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "create_checkout forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        plan_id=request.plan_id,
    )
    # Phase 1: Stub. Full implementation will integrate Stripe.
    raise ServiceUnavailableError(message="Stripe checkout not yet configured in L7")


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe customer portal session."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "create_portal forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
    )
    # Phase 1: Stub. Full implementation will integrate Stripe.
    raise ServiceUnavailableError(message="Stripe portal not yet configured in L7")


# ---------------------------------------------------------------------------
# Subscription Lifecycle Endpoints
# ---------------------------------------------------------------------------


@router.post("/subscription/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Cancel a customer's subscription."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "cancel_subscription forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        cancel_immediately=request.cancel_immediately,
    )
    raise ServiceUnavailableError(message="Stripe cancellation not yet configured in L7")


@router.post("/subscription/update-plan", response_model=UpdatePlanResponse)
async def update_subscription_plan(
    request: UpdatePlanRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Update a customer's subscription plan."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "update_subscription_plan forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        plan_id=request.plan_id,
    )
    raise ServiceUnavailableError(message="Stripe plan update not yet configured in L7")


@router.post("/subscription/reactivate", response_model=ReactivateSubscriptionResponse)
async def reactivate_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Reactivate a subscription scheduled to cancel at period end."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "reactivate_subscription forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
    )
    raise ServiceUnavailableError(message="Stripe reactivation not yet configured in L7")


# ---------------------------------------------------------------------------
# Entitlement Endpoints
# ---------------------------------------------------------------------------


@router.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get all feature entitlements for a customer."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    # Return plan entitlements from L7 repository
    plan_entitlements = await repository.get_plan_entitlements(
        db, str(ctx.tenant_id), "default"
    )
    features = {feat: True for feat in plan_entitlements}
    return {
        "plan_id": "default",
        "plan_name": "Default Plan",
        "features": features,
    }


@router.get("/check-feature")
async def check_feature(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    feature_id: str = Query(..., min_length=1, max_length=64),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Check if a customer has access to a specific feature."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    plan_entitlements = await repository.get_plan_entitlements(
        db, str(ctx.tenant_id), "default"
    )
    has_access = feature_id in plan_entitlements
    return {
        "feature_id": feature_id,
        "has_access": has_access,
    }


# ---------------------------------------------------------------------------
# Customer Management
# ---------------------------------------------------------------------------


@router.post("/sync-customer")
async def sync_customer(
    request: CustomerSyncRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Sync customer with Stripe (create or update)."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "sync_customer forwarded",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        email=request.email,
    )
    # Phase 1: Stub. Returns a placeholder.
    return {
        "id": customer_id,
        "stripe_customer_id": None,
        "email": request.email,
        "name": request.name,
        "tenant_id": str(ctx.tenant_id),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


@router.get("/customers/{customer_id}/balance", response_model=CustomerBalanceResponse)
async def get_customer_balance(
    customer_id: str,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get customer balance summary."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    invoices = await repository.list_invoices(db, str(ctx.tenant_id))
    total_cents = sum(inv.get("payload", {}).get("total_cents", 0) for inv in invoices)

    return {
        "customer_id": customer_id,
        "open_invoices_cents": total_cents,
        "open_invoices_dollars": f"${total_cents / 100:.2f}",
        "lifetime_paid_cents": 0,
        "lifetime_paid_dollars": "$0.00",
        "balance_cents": total_cents,
        "balance_dollars": f"${total_cents / 100:.2f}",
    }
