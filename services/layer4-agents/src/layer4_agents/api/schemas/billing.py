from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., description="Plan to subscribe to (pro, enterprise)")
    success_url: str = Field(..., description="Redirect URL after successful checkout")
    cancel_url: str = Field(..., description="Redirect URL if checkout canceled")


class PortalRequest(BaseModel):
    return_url: str = Field(..., description="URL to return to after portal session")


class CustomerSyncRequest(BaseModel):
    email: str = Field(..., description="Customer email address")
    name: str | None = Field(None, description="Customer name")


class SubscriptionResponse(BaseModel):
    id: str | None
    plan_id: str
    status: str
    current_period_start: str | None
    current_period_end: str | None
    cancel_at_period_end: bool


class UsageEventRequest(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128)
    customer_id: str = Field(..., min_length=1, max_length=64)
    event_name: str = Field(..., min_length=1, max_length=128)
    metric_name: str = Field(..., min_length=1, max_length=64)
    quantity: float = Field(..., ge=0)
    unit: str | None = Field(default=None, max_length=32)
    timestamp: datetime = Field(...)
    metadata: dict[str, Any] | None = Field(default=None)


class UsageBatchRequest(BaseModel):
    events: list[UsageEventRequest] = Field(..., min_length=1, max_length=1000)


class CreateInvoiceRequest(BaseModel):
    customer_id: str
    due_date: datetime | None = None
    description: str | None = None


class AddInvoiceItemRequest(BaseModel):
    description: str
    amount_cents: int
    quantity: int = 1


class RecordChargeRequest(BaseModel):
    customer_id: str
    amount_cents: int
    currency: str = "usd"
    description: str | None = None
