"""Customer Pydantic schemas for the billing service HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CustomerCreateRequest(BaseModel):
    """Request body to create or sync a billing customer."""

    user_id: str = Field(..., description="Application user identifier")
    tenant_id: str = Field(..., description="Tenant that owns this customer")
    email: EmailStr = Field(..., description="Customer email address")
    name: str | None = Field(None, description="Optional display name")


class CustomerRead(BaseModel):
    """Serialised billing customer returned by the API."""

    user_id: str
    tenant_id: str
    stripe_customer_id: str | None
    stripe_sync_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
