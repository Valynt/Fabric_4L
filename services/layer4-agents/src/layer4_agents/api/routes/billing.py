from __future__ import annotations

"""Phase 1 forwarding stub — canonical billing routes now live in layer7-billing.

This module re-exports the Layer 7 billing routes via HTTP client forwarding.
All billing endpoints are served from the Layer 7 Billing Service (port 8008).
Layer 4 retains this stub for backward compatibility during the migration.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import (
    ServiceUnavailableError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..common.db import get_route_db

logger = logging.getLogger(__name__)

# Known Stripe webhook IPs (documented by Stripe) + loopback for local dev
_STRIPE_WEBHOOK_IPS = {"3.18.12.63", "52.15.183.38", "54.187.174.170", "127.0.0.1", "::1"}


def _is_stripe_webhook_ip(ip: str) -> bool:
    """Return True if *ip* is a known Stripe webhook or loopback address."""
    return ip in _STRIPE_WEBHOOK_IPS


def _get_client_ip(request: Request) -> str:
    """Extract the client IP from forwarded headers or the transport socket."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    x_real = request.headers.get("X-Real-IP")
    if x_real:
        return x_real.strip()
    if request.client is not None:
        return request.client.host
    return ""


router = APIRouter(prefix="/billing", tags=["Billing"])


# ---------------------------------------------------------------------------
# Response models (re-exported for L4 consumers)
# ---------------------------------------------------------------------------

class get_subscriptionResult(TypedDictModel):
    cancel_at_period_end: bool
    current_period_end: Any
    current_period_start: Any
    id: Any
    plan_id: str
    status: str

class check_featureResult(TypedDictModel):
    feature_id: Any
    has_access: Any

class sync_customerResult(TypedDictModel):
    email: Any
    id: Any
    name: Any
    stripe_customer_id: Any
    tenant_id: Any

class get_plan_limitsResult(TypedDictModel):
    limits: Any
    plan_id: Any
    plan_name: Any

class stripe_webhookResult(TypedDictModel):
    received: bool

class ingest_usage_eventResult(TypedDictModel):
    created_at: Any
    customer_id: Any
    event_id: Any
    id: Any
    metric_name: Any
    quantity: Any
    status: Any
    tenant_id: Any
    timestamp: Any

class ingest_usage_batchResult(TypedDictModel):
    created: Any
    duplicates: Any
    error_details: Any
    errors: Any

class get_usage_limitsResult(TypedDictModel):
    all_limits_ok: Any
    customer_id: Any
    metrics: Any
    plan_id: Any
    total_overage_cost: Any
    warnings: Any

class list_invoicesResult(TypedDictModel):
    invoices: Any
    pagination: dict[str, Any]

class create_invoiceResult(TypedDictModel):
    created_at: Any
    customer_id: Any
    id: Any
    invoice_number: Any
    status: Any
    total_cents: Any
    total_dollars: Any

class get_invoiceResult(TypedDictModel):
    amount_due_cents: Any
    amount_due_dollars: Any
    amount_paid_cents: Any
    balance_cents: Any
    charges: Any
    created_at: Any
    currency: Any
    customer_id: Any
    description: Any
    due_date: Any
    hosted_invoice_url: Any
    id: Any
    invoice_number: Any
    invoice_pdf_url: Any
    items: Any
    paid_at: Any
    period_end: Any
    period_start: Any
    status: Any
    subtotal_cents: Any
    tax_cents: Any
    total_cents: Any
    total_dollars: Any

class add_invoice_itemResult(TypedDictModel):
    amount_cents: Any
    amount_dollars: Any
    description: Any
    id: Any
    invoice_id: Any
    type: Any

class finalize_invoiceResult(TypedDictModel):
    amount_due_cents: Any
    amount_due_dollars: Any
    id: Any
    status: Any
    total_cents: Any
    total_dollars: Any

class void_invoiceResult(TypedDictModel):
    id: Any
    status: Any
    voided_at: Any

class list_chargesResult(TypedDictModel):
    charges: Any
    pagination: dict[str, Any]

class record_chargeResult(TypedDictModel):
    amount_cents: Any
    amount_dollars: Any
    created_at: Any
    id: Any
    status: Any
    stripe_charge_id: Any

class reconcile_invoiceResult(TypedDictModel):
    invoice_id: Any
    mismatch_count: Any
    mismatches: Any


# ============================================================================
# Forwarding stubs — all billing endpoints now served by Layer 7
# ============================================================================

_L7_BILLING_URL = os.environ.get("LAYER7_BILLING_URL", "http://layer7-billing:8008")


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    plan_id: str = Field(..., description="Plan to subscribe to")
    success_url: str = Field(..., description="Redirect URL after successful checkout")
    cancel_url: str = Field(..., description="Redirect URL if checkout canceled")


class PortalRequest(BaseModel):
    """Request to create a customer portal session."""
    return_url: str = Field(..., description="URL to return to after portal session")


class CustomerSyncRequest(BaseModel):
    """Request to sync customer with Stripe."""
    email: str = Field(..., description="Customer email address")
    name: str | None = Field(None, description="Customer name")


class UsageEventRequest(BaseModel):
    """Request body for ingesting a single usage event."""
    event_id: str = Field(..., min_length=1, max_length=128, description="Idempotency key")
    customer_id: str = Field(..., min_length=1, max_length=64, description="Customer identifier")
    event_name: str = Field(..., min_length=1, max_length=128, description="Logical event name")
    metric_name: str = Field(..., min_length=1, max_length=64, description="Metered metric name")
    quantity: float = Field(..., ge=0, description="Quantity to record")
    unit: str | None = Field(default=None, max_length=32, description="Unit of measure")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class UsageBatchRequest(BaseModel):
    """Request body for batch ingestion of usage events."""
    events: list[UsageEventRequest] = Field(..., min_length=1, max_length=1000, description="Events to ingest")


class CancelSubscriptionRequest(BaseModel):
    cancel_immediately: bool = Field(False, description="Cancel immediately vs at period end")


class UpdatePlanRequest(BaseModel):
    plan_id: str = Field(..., description="Target plan (pro, enterprise)")


class CreateInvoiceRequest(BaseModel):
    """Request to create a new invoice."""
    customer_id: str = Field(..., description="Customer being invoiced")
    period_start: datetime = Field(..., description="Billing period start")
    period_end: datetime = Field(..., description="Billing period end")
    invoice_number: str | None = Field(None, description="Optional invoice number")
    subscription_id: str | None = Field(None, description="Optional subscription link")
    currency: str = Field(default="USD", description="Currency code")
    description: str | None = Field(None, description="Invoice description")


class AddInvoiceItemRequest(BaseModel):
    """Request to add an invoice line item."""
    description: str = Field(..., description="Line item description")
    amount_cents: int = Field(..., ge=0, description="Amount in cents")
    quantity: float = Field(default=1.0, gt=0, description="Quantity")
    unit_amount_cents: int | None = Field(None, description="Price per unit in cents")
    type: str = Field(default="one_time", description="Item type")
    usage_quantity: float | None = Field(None, description="Usage quantity for metered items")
    usage_metric: str | None = Field(None, description="Usage metric for metered items")
    tax_cents: int = Field(default=0, ge=0, description="Tax amount in cents")
    discount_cents: int = Field(default=0, ge=0, description="Discount amount in cents")


class RecordChargeRequest(BaseModel):
    """Request to record a charge."""
    customer_id: str = Field(..., description="Customer being charged")
    amount_cents: int = Field(..., gt=0, description="Charge amount in cents")
    status: str = Field(default="succeeded", description="Charge status")
    invoice_id: str | None = Field(None, description="Linked invoice ID")
    stripe_charge_id: str | None = Field(None, description="Stripe charge ID")
    payment_method_id: str | None = Field(None, description="Payment method ID")
    payment_method_type: str | None = Field(None, description="Payment method type")
    description: str | None = Field(None, description="Charge description")


def _forward_error() -> None:
    """Raise a consistent error directing callers to Layer 7."""
    raise ServiceUnavailableError(
        message="Billing routes have moved to Layer 7",
        details={
            "migration": "Phase 1: billing routes extracted to layer7-billing",
            "target_service": _L7_BILLING_URL,
            "action_required": "Call /v1/billing/* on layer7-billing directly",
        },
    )


# ---------------------------------------------------------------------------
# Subscription Endpoints
# ---------------------------------------------------------------------------

@router.get("/subscription", response_model=get_subscriptionResult)
async def get_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get current subscription status."""
    _forward_error()


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """[STUB] Forwarded to Layer 7. Create a Stripe checkout session."""
    _forward_error()


@router.post("/portal")
async def create_portal(
    request: PortalRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """[STUB] Forwarded to Layer 7. Create a Stripe customer portal session."""
    _forward_error()


# ---------------------------------------------------------------------------
# Subscription Lifecycle Endpoints
# ---------------------------------------------------------------------------

@router.post("/subscription/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Cancel a customer's subscription."""
    _forward_error()


@router.post("/subscription/update-plan")
async def update_subscription_plan(
    request: UpdatePlanRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Update a customer's subscription plan."""
    _forward_error()


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Reactivate a subscription."""
    _forward_error()


# ---------------------------------------------------------------------------
# Entitlement Endpoints
# ---------------------------------------------------------------------------

@router.get("/entitlements")
async def get_entitlements(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get all feature entitlements for a customer."""
    _forward_error()


@router.get("/check-feature", response_model=check_featureResult)
async def check_feature(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    feature_id: str = Query(..., min_length=1, max_length=64),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Check if a customer has access to a specific feature."""
    _forward_error()


# ---------------------------------------------------------------------------
# Customer Management
# ---------------------------------------------------------------------------

@router.post("/sync-customer", response_model=sync_customerResult)
async def sync_customer(
    request: CustomerSyncRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Sync customer with Stripe."""
    _forward_error()


# ---------------------------------------------------------------------------
# Webhook Endpoint
# ---------------------------------------------------------------------------

async def stripe_webhook(
    request: Request,
    background_tasks: Any,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_route_db),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Handle Stripe webhook events."""
    _forward_error()


# ---------------------------------------------------------------------------
# Usage Metering Endpoints
# ---------------------------------------------------------------------------

async def ingest_usage_event(
    request: UsageEventRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Ingest a single usage event for billing."""
    _forward_error()


async def ingest_usage_batch(
    request: UsageBatchRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Ingest multiple usage events in a batch."""
    _forward_error()


async def get_usage_summary(
    customer_id: str,
    metric_name: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get aggregated usage summary."""
    _forward_error()


async def list_usage_events(
    customer_id: str,
    metric_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> list[dict[str, Any]]:
    """[STUB] Forwarded to Layer 7. List individual usage events for a customer."""
    _forward_error()


async def sync_usage_to_stripe(
    customer_id: str,
    metric_name: str | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Sync pending usage events to Stripe MeterEvents."""
    _forward_error()


# ---------------------------------------------------------------------------
# Overage Detection & Limits
# ---------------------------------------------------------------------------

async def get_usage_limits(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get current usage and limits for a customer."""
    _forward_error()


async def check_request_allowed(
    customer_id: str,
    metric_name: str,
    quantity: float = Query(1.0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Check if a request should be allowed based on usage limits."""
    _forward_error()


async def get_plan_limits(
    plan_id: str,
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get the configured usage limits for a plan."""
    _forward_error()


# ---------------------------------------------------------------------------
# Invoice Management
# ---------------------------------------------------------------------------

@router.get("/invoices", response_model=list_invoicesResult)
async def list_invoices(
    customer_id: str | None = Query(None),
    invoice_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. List invoices with optional filters."""
    _forward_error()


@router.post("/invoices", response_model=create_invoiceResult)
async def create_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Create a new invoice."""
    _forward_error()


@router.get("/invoices/{invoice_id}", response_model=get_invoiceResult)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get invoice details including line items and charges."""
    _forward_error()


@router.post("/invoices/{invoice_id}/items", response_model=add_invoice_itemResult)
async def add_invoice_item(
    invoice_id: str,
    request: AddInvoiceItemRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Add a line item to an invoice."""
    _forward_error()


@router.post("/invoices/{invoice_id}/finalize", response_model=finalize_invoiceResult)
async def finalize_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Finalize a draft invoice."""
    _forward_error()


@router.post("/invoices/{invoice_id}/void", response_model=void_invoiceResult)
async def void_invoice(
    invoice_id: str,
    reason: str | None = Query(None, description="Void reason"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Void an invoice."""
    _forward_error()


# ---------------------------------------------------------------------------
# Charge Management
# ---------------------------------------------------------------------------

@router.get("/charges", response_model=list_chargesResult)
async def list_charges(
    customer_id: str | None = Query(None),
    invoice_id: str | None = Query(None),
    charge_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. List charge records."""
    _forward_error()


@router.post("/charges", response_model=record_chargeResult)
async def record_charge(
    request: RecordChargeRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Record a charge attempt."""
    _forward_error()


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

@router.get("/reports/revenue")
async def get_revenue_summary(
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get revenue summary for a period."""
    _forward_error()


@router.get("/customers/{customer_id}/balance")
async def get_customer_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """[STUB] Forwarded to Layer 7. Get customer balance summary."""
    _forward_error()


# ---------------------------------------------------------------------------
# Re-export adjacent route modules (also stubbed)
# ---------------------------------------------------------------------------
def _is_adjacent_billing_route_initializing(name: str) -> bool:
    module = sys.modules.get(f"{__package__}.{name}")
    spec = getattr(module, "__spec__", None)
    return bool(getattr(spec, "_initializing", False))


if not any(
    _is_adjacent_billing_route_initializing(name)
    for name in ("billing_overages", "billing_usage", "billing_webhooks")
):
    from .billing_overages import router as billing_overages_router
    from .billing_usage import router as billing_usage_router
    from .billing_webhooks import router as billing_webhooks_router

    router.include_router(billing_overages_router)
    router.include_router(billing_usage_router)
    router.include_router(billing_webhooks_router)
