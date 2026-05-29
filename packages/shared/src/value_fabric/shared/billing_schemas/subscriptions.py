"""Subscription Pydantic schemas for the billing service HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .plans import PlanId, SubscriptionStatus


class SubscriptionCreateRequest(BaseModel):
    """Request body to create a subscription for a customer."""

    user_id: str = Field(..., description="Application user identifier")
    tenant_id: str = Field(..., description="Tenant that owns this subscription")
    plan_id: PlanId = Field(..., description="Requested plan")
    stripe_price_id: str = Field(..., description="Stripe Price ID for the plan")


class SubscriptionRead(BaseModel):
    """Serialised subscription returned by the API."""

    id: str
    user_id: str
    tenant_id: str
    plan_id: PlanId
    status: SubscriptionStatus
    stripe_subscription_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
