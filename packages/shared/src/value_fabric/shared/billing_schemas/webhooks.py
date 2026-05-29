"""Webhook event Pydantic schemas for the billing service HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WebhookEvent(BaseModel):
    """Stripe webhook event envelope passed to the billing service."""

    id: str = Field(..., description="Stripe event ID (idempotency key)")
    type: str = Field(..., description="Stripe event type, e.g. 'customer.subscription.updated'")
    livemode: bool = Field(..., description="True for live-mode events; False for test-mode")
    data: dict[str, Any] = Field(..., description="Raw event data object from Stripe")
    created: int = Field(..., description="Unix timestamp when Stripe created the event")
