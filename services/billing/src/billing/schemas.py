"""Pydantic schemas for the billing service HTTP API.

These are service-local schemas that extend the shared ``billing_schemas``
package.  Cross-service callers import from ``value_fabric.shared.billing_schemas``
instead.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .models import PlanId, SubscriptionStatus


class CustomerCreateRequest(BaseModel):
    """Request body to create or sync a billing customer."""

    user_id: str = Field(..., description="Application user identifier")
    tenant_id: str = Field(..., description="Tenant that owns this customer")
    email: str = Field(..., description="Customer email address")
    name: str | None = Field(None, description="Optional display name")


class CustomerRead(BaseModel):
    """Serialised customer returned by the API."""

    user_id: str
    tenant_id: str
    stripe_customer_id: str | None
    stripe_sync_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCreateRequest(BaseModel):
    """Request body to create a subscription."""

    user_id: str
    tenant_id: str
    plan_id: PlanId
    stripe_price_id: str


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
    cancel_at_period_end: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookPayload(BaseModel):
    """Raw Stripe webhook payload validated before processing."""

    id: str = Field(..., description="Stripe event ID (used for idempotency)")
    type: str = Field(..., description="Stripe event type")
    livemode: bool
    data: dict
    created: int


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: str
    detail: str | None = None
