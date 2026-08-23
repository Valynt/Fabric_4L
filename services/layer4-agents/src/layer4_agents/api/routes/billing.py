from __future__ import annotations

"""Production billing routes backed by Layer 4 services.

This module provides the production billing API surface for the frontend
and other consumers. All endpoints are served by the fully-implemented
Layer 4 billing services (BillingService, InvoiceService, UsageService,
OverageService) with Stripe SDK integration, tenant isolation, and
audit-grade record keeping.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Any, NoReturn

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.error_handling.exceptions import (
    BadRequestError,
    NotFoundError,
    ServiceUnavailableError,
    ValueFabricException,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...services.billing_security import validate_webhook_request_security
from ...services.billing_service import BillingService
from ...services.invoice_service import InvoiceService
from ...services.overage_service import OverageService
from ...services.usage_service import UsageService
from ..common.db import get_route_db, get_webhook_db
from .billing_helpers import (
    dt_iso as _dt_iso,
    get_client_ip as _get_client_ip,
    is_stripe_webhook_ip as _is_stripe_webhook_ip,
    serialize_charge as _serialize_charge,
    serialize_customer as _serialize_customer,
    serialize_invoice as _serialize_invoice,
    serialize_subscription as _serialize_subscription,
    serialize_usage_event as _serialize_usage_event,
)

__all__ = ["_is_stripe_webhook_ip"]

logger = logging.getLogger(__name__)

# Known Stripe webhook IPs (documented by Stripe) + loopback for local dev
_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_WEBHOOK_SECRET = _STRIPE_WEBHOOK_SECRET
STRIPE_WEBHOOK_SKIP_IP_CHECK = False


async def _defer_webhook_db() -> None:
    """Defer webhook DB acquisition until after Stripe security checks pass."""
    return None


async def _emit_billing_audit(
    action: AuditAction,
    context: RequestContext,
    resource_type: str,
    resource_id: str | None = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit a billing audit event (best-effort; never blocks request)."""
    try:
        await emit_audit_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=str(context.tenant_id) if context.tenant_id else None,
            user_id=context.user_id,
            api_key_id=context.api_key_id,
            request_id=context.request_id,
            outcome=outcome,
            details=details or {},
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Billing audit emission failed (non-critical): %s", exc)


def _raise_billing_bad_request(
    exc: ValueError, message: str = "Invalid billing request."
) -> NoReturn:
    """Translate a ValueError into a structured, client-safe BadRequestError.

    The original exception text is logged server-side for debugging but is
    never returned to the client (ban_str_e).

    Args:
        exc: The validation exception raised by a billing service.
        message: A safe, human-readable message to return to the client.

    Raises:
        BadRequestError: A sanitized error with a stable code and safe message.
    """
    logger.info("Billing validation failed: %s", exc)
    raise BadRequestError(
        message=message,
        details={"code": "BILLING_VALIDATION_ERROR"},
    ) from exc


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


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/billing", tags=["Billing"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


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

    events: list[UsageEventRequest] = Field(
        ..., min_length=1, max_length=1000, description="Events to ingest"
    )


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


# ---------------------------------------------------------------------------
# Subscription Endpoints
# ---------------------------------------------------------------------------


@router.get("/subscription", response_model=get_subscriptionResult)
async def get_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get current subscription status."""
    svc = BillingService(db)
    sub = await svc.get_subscription(customer_id, tenant_id=context.tenant_id)
    return _serialize_subscription(sub)


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe checkout session."""
    svc = BillingService(db)
    try:
        result = await svc.create_checkout_session(
            customer_id=customer_id,
            plan_id=request.plan_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_CHECKOUT_INITIATED,
            context=context,
            resource_type="billing_checkout",
            resource_id=result["session_id"],
            details={"plan_id": request.plan_id, "customer_id": customer_id},
        )
        return {"session_id": result["session_id"], "url": result["url"]}
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.post("/portal")
async def create_portal(
    request: PortalRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe customer portal session."""
    svc = BillingService(db)
    try:
        result = await svc.create_portal_session(
            customer_id=customer_id, return_url=request.return_url
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_PORTAL_OPENED,
            context=context,
            resource_type="billing_portal",
            details={"customer_id": customer_id},
        )
        return {"url": result["url"]}
    except ValueError as exc:
        _raise_billing_bad_request(exc)


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
    """Cancel a customer's subscription."""
    svc = BillingService(db)
    try:
        result = await svc.cancel_subscription(
            customer_id=customer_id,
            tenant_id=context.tenant_id,
            cancel_immediately=request.cancel_immediately,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_SUBSCRIPTION_CANCELED,
            context=context,
            resource_type="billing_subscription",
            resource_id=result.get("subscription_id"),
            details={
                "customer_id": customer_id,
                "cancel_at_period_end": result.get("cancel_at_period_end"),
            },
        )
        return {
            "canceled": result.get("canceled", True),
            "cancel_at_period_end": result.get("cancel_at_period_end", False),
            "current_period_end": _dt_iso(result.get("current_period_end")),
            "subscription_id": result.get("subscription_id"),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.post("/subscription/update-plan")
async def update_subscription_plan(
    request: UpdatePlanRequest,
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Update a customer's subscription plan."""
    svc = BillingService(db)
    try:
        result = await svc.update_subscription_plan(
            customer_id=customer_id,
            new_plan_id=request.plan_id,
            tenant_id=context.tenant_id,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_PLAN_CHANGED,
            context=context,
            resource_type="billing_subscription",
            resource_id=result.get("subscription_id"),
            details={
                "customer_id": customer_id,
                "previous_plan_id": result.get("previous_plan_id"),
                "new_plan_id": request.plan_id,
            },
        )
        return {
            "updated": result.get("updated", True),
            "previous_plan_id": result.get("previous_plan_id"),
            "subscription_id": result.get("subscription_id"),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Reactivate a subscription."""
    svc = BillingService(db)
    try:
        result = await svc.reactivate_subscription(
            customer_id=customer_id, tenant_id=context.tenant_id
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_SUBSCRIPTION_REACTIVATED,
            context=context,
            resource_type="billing_subscription",
            resource_id=result.get("subscription_id"),
            details={"customer_id": customer_id},
        )
        return {
            "reactivated": result.get("reactivated", True),
            "subscription_id": result.get("subscription_id"),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


# ---------------------------------------------------------------------------
# Entitlement Endpoints
# ---------------------------------------------------------------------------


@router.get("/entitlements")
async def get_entitlements(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get all feature entitlements for a customer."""
    svc = BillingService(db)
    result = await svc.get_entitlements(customer_id)
    # Enrich feature dicts with name/description to match frontend contract
    features = result.get("features", {})
    enriched: dict[str, Any] = {}
    for feat_key, feat_val in features.items():
        if isinstance(feat_val, dict):
            enriched[feat_key] = {
                "enabled": feat_val.get("enabled", True),
                "name": feat_val.get("name", feat_key.replace("_", " ").title()),
                "description": feat_val.get("description", ""),
            }
        else:
            enriched[feat_key] = {
                "enabled": bool(feat_val),
                "name": feat_key.replace("_", " ").title(),
                "description": "",
            }
    result["features"] = enriched
    return result


@router.get("/check-feature", response_model=check_featureResult)
async def check_feature(
    customer_id: str = Query(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    feature_id: str = Query(..., min_length=1, max_length=64),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Check if a customer has access to a specific feature."""
    svc = BillingService(db)
    has_access = await svc.check_entitlement(customer_id, feature_id)
    return {"feature_id": feature_id, "has_access": has_access}


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
    """Sync customer with Stripe."""
    svc = BillingService(db)
    try:
        customer = await svc.get_or_create_customer(
            customer_id=customer_id,
            email=request.email,
            name=request.name,
            tenant_id=context.tenant_id,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_CUSTOMER_SYNCED,
            context=context,
            resource_type="billing_customer",
            resource_id=customer.id,
            details={"customer_id": customer_id, "email": request.email},
        )
        return _serialize_customer(customer)
    except ValueError as exc:
        _raise_billing_bad_request(exc)


# ---------------------------------------------------------------------------
# Webhook Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/webhook",
    responses={
        400: {
            "description": "Invalid webhook payload — verify the payload body and Stripe-Signature timestamp"
        },
    },
)
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession | None = Depends(_defer_webhook_db),
) -> dict[str, Any]:
    """Handle Stripe webhook events."""
    client_ip = _get_client_ip(request)
    webhook_secret = STRIPE_WEBHOOK_SECRET or _STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        raise ServiceUnavailableError(
            message="Stripe webhook secret not configured",
            details={"env_var": "STRIPE_WEBHOOK_SECRET"},
        )

    payload = await request.body()
    try:
        validate_webhook_request_security(
            request,
            stripe_signature,
            enforce_ip_check=not STRIPE_WEBHOOK_SKIP_IP_CHECK,
        )
        if db is None:
            async for session in get_webhook_db():
                db = session
                break
        if db is None:
            raise ServiceUnavailableError(message="Billing database unavailable")
        svc = BillingService(db)
        webhook_event = await svc.handle_webhook(
            payload=payload,
            signature=stripe_signature,
            webhook_secret=webhook_secret,
        )
        # Process the event inline (durable inbox pattern)
        await svc.process_webhook_event(
            event_id=webhook_event.id,
            payload=payload,
            signature=stripe_signature,
            webhook_secret=webhook_secret,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_WEBHOOK_RECEIVED,
            context=RequestContext(),
            resource_type="billing_webhook",
            details={"client_ip": client_ip},
        )
        return {"received": True}
    except ValueError as exc:
        _raise_billing_bad_request(exc, message="Invalid webhook payload")
    except ValueFabricException:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error(
            "Webhook processing failed",
            extra={
                "error_code": "BILLING_WEBHOOK_PROCESSING_ERROR",
                "exception_type": type(exc).__name__,
            },
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_WEBHOOK_RECEIVED,
            context=RequestContext(),
            resource_type="billing_webhook",
            outcome=AuditOutcome.FAILURE,
            details={"client_ip": client_ip, "error_code": "BILLING_WEBHOOK_PROCESSING_ERROR"},
        )
        # Return 200 to Stripe so it doesn't retry indefinitely for unrecoverable errors
        return {"received": True}


# ---------------------------------------------------------------------------
# Usage Metering Endpoints
# ---------------------------------------------------------------------------


async def ingest_usage_event(
    request: UsageEventRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Ingest a single usage event for billing."""
    # Pre-check usage limits before consuming quota
    overage_svc = OverageService(db, tenant_id=context.tenant_id)
    check = await overage_svc.validate_request(
        customer_id=request.customer_id,
        metric_name=request.metric_name,
        requested_quantity=request.quantity,
    )
    if not check.get("allowed", True):
        from value_fabric.shared.error_handling.exceptions import RateLimitError

        raise RateLimitError(
            message=check.get("error", "Usage limit exceeded"),
            details={
                "limit": check.get("limit"),
                "current_usage": check.get("current_usage"),
                "overage": check.get("overage"),
                "metric": request.metric_name,
            },
        )

    usage_svc = UsageService(db, tenant_id=context.tenant_id)
    try:
        event = await usage_svc.ingest_event(
            event_id=request.event_id,
            customer_id=request.customer_id,
            event_name=request.event_name,
            metric_name=request.metric_name,
            quantity=request.quantity,
            unit=request.unit,
            timestamp=request.timestamp,
            metadata=request.metadata,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_USAGE_INGESTED,
            context=context,
            resource_type="billing_usage_event",
            resource_id=event.id,
            details={
                "customer_id": request.customer_id,
                "metric_name": request.metric_name,
                "quantity": request.quantity,
            },
        )
        return _serialize_usage_event(event)
    except ValueError as exc:
        _raise_billing_bad_request(exc)


async def ingest_usage_batch(
    request: UsageBatchRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Ingest multiple usage events in a batch."""
    if not request.events:
        return {"events": []}

    # Pre-check overages for the batch
    overage_svc = OverageService(db, tenant_id=context.tenant_id)
    total_by_customer_metric: dict[tuple[str, str], float] = {}
    for ev in request.events:
        key = (ev.customer_id, ev.metric_name)
        total_by_customer_metric[key] = total_by_customer_metric.get(key, 0) + ev.quantity

    for (customer_id, metric_name), total_qty in total_by_customer_metric.items():
        check = await overage_svc.validate_request(
            customer_id=customer_id,
            metric_name=metric_name,
            requested_quantity=total_qty,
        )
        if not check.get("allowed", True):
            from value_fabric.shared.error_handling.exceptions import RateLimitError

            raise RateLimitError(
                message=check.get("error", "Usage limit exceeded"),
                details={
                    "limit": check.get("limit"),
                    "current_usage": check.get("current_usage"),
                    "overage": check.get("overage"),
                    "metric": metric_name,
                },
            )

    usage_svc = UsageService(db, tenant_id=context.tenant_id)
    raw_events = []
    for ev in request.events:
        raw_events.append(
            {
                "event_id": ev.event_id,
                "customer_id": ev.customer_id,
                "event_name": ev.event_name,
                "metric_name": ev.metric_name,
                "quantity": ev.quantity,
                "unit": ev.unit,
                "timestamp": ev.timestamp,
                "metadata": ev.metadata,
            }
        )
    try:
        result = await usage_svc.ingest_batch(raw_events)
        batch_customer_id = (
            request.events[0].customer_id
            if request.events
            else str(context.tenant_id) if context.tenant_id else None
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_USAGE_INGESTED,
            context=context,
            resource_type="billing_usage_batch",
            details={"customer_id": batch_customer_id, "event_count": len(request.events)},
        )
        return {
            "created": result.get("created", []),
            "duplicates": result.get("duplicates", []),
            "errors": result.get("errors", 0),
            "error_details": result.get("error_details", []),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


async def get_usage_summary(
    customer_id: str,
    metric_name: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get aggregated usage summary."""
    usage_svc = UsageService(db, tenant_id=context.tenant_id)
    result = await usage_svc.get_usage_summary(
        customer_id=customer_id,
        metric_name=metric_name,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "customer_id": customer_id,
        "metric_name": metric_name,
        "total_quantity": result.get("total_quantity", 0),
        "unit": result.get("unit"),
        "period_start": _dt_iso(result.get("period_start")),
        "period_end": _dt_iso(result.get("period_end")),
    }


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
    """List individual usage events for a customer."""
    usage_svc = UsageService(db, tenant_id=context.tenant_id)
    events = await usage_svc.list_customer_usage(
        customer_id=customer_id,
        metric_name=metric_name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return [_serialize_usage_event(ev) for ev in events]


async def sync_usage_to_stripe(
    customer_id: str,
    metric_name: str | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Sync pending usage events to Stripe MeterEvents."""
    usage_svc = UsageService(db, tenant_id=context.tenant_id)
    try:
        result = await usage_svc.sync_to_stripe(customer_id=customer_id, metric_name=metric_name)
        return {
            "synced": result.get("synced", 0),
            "failed": result.get("failed", 0),
            "customer_id": customer_id,
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


# ---------------------------------------------------------------------------
# Overage Detection & Limits
# ---------------------------------------------------------------------------


async def get_usage_limits(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get current usage and limits for a customer."""
    overage_svc = OverageService(db, tenant_id=context.tenant_id)
    result = await overage_svc.check_all_limits(customer_id)
    return {
        "customer_id": result.customer_id,
        "plan_id": result.plan_id,
        "all_limits_ok": result.all_limits_ok,
        "warnings": result.warnings,
        "total_overage_cost": result.total_overage_cost,
        "metrics": [
            {
                "metric_name": check.metric_name,
                "current_usage": check.current_usage,
                "limit": check.limit,
                "percentage_used": check.percentage_used,
                "remaining": check.remaining,
                "overage": check.overage,
                "warning_triggered": check.warning_triggered,
                "limit_exceeded": check.limit_exceeded,
                "overage_cost": check.overage_cost,
                "period_start": _dt_iso(check.period_start),
                "period_end": _dt_iso(check.period_end),
            }
            for check in result.checks
        ],
    }


async def check_request_allowed(
    customer_id: str,
    metric_name: str,
    quantity: float = Query(1.0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Check if a request should be allowed based on usage limits."""
    overage_svc = OverageService(db, tenant_id=context.tenant_id)
    result = await overage_svc.validate_request(
        customer_id=customer_id,
        metric_name=metric_name,
        requested_quantity=quantity,
    )
    return result


async def get_plan_limits(
    plan_id: str,
) -> dict[str, Any]:
    """Get the configured usage limits for a plan."""
    from ...config.plans import get_plan as get_plan_config

    # OverageService does not need DB for plan limits (reads from config)
    overage_svc = OverageService(db=None, tenant_id=None)  # type: ignore[arg-type]
    plan_config = get_plan_config(plan_id)
    return {
        "plan_id": plan_id,
        "plan_name": getattr(plan_config, "name", plan_id) if plan_config else plan_id,
        "limits": overage_svc.get_plan_limits(plan_id),
    }


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
    """List invoices with optional filters."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    invoices = await svc.list_invoices(
        customer_id=customer_id,
        status=invoice_status,
        limit=limit,
        offset=offset,
    )
    return {
        "invoices": [_serialize_invoice(inv) for inv in invoices],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": len(invoices),  # Approximate; full count would require extra query
        },
    }


@router.post("/invoices", response_model=create_invoiceResult)
async def create_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Create a new invoice."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    try:
        inv = await svc.create_invoice(
            customer_id=request.customer_id,
            period_start=request.period_start,
            period_end=request.period_end,
            invoice_number=request.invoice_number,
            subscription_id=request.subscription_id,
            currency=request.currency,
            description=request.description,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_INVOICE_CREATED,
            context=context,
            resource_type="billing_invoice",
            resource_id=inv.id,
            details={"customer_id": request.customer_id, "total_cents": inv.total},
        )
        return {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "status": inv.status,
            "total_cents": inv.total,
            "total_dollars": inv.total_dollars,
            "created_at": _dt_iso(inv.created_at),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.get("/invoices/{invoice_id}", response_model=get_invoiceResult)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get invoice details including line items and charges."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    inv = await svc.get_invoice(invoice_id, include_items=True, include_charges=True)
    if inv is None:
        raise NotFoundError(resource_type="invoice", resource_id=invoice_id)
    return _serialize_invoice(inv, include_items=True, include_charges=True)


@router.post("/invoices/{invoice_id}/items", response_model=add_invoice_itemResult)
async def add_invoice_item(
    invoice_id: str,
    request: AddInvoiceItemRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Add a line item to an invoice."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    try:
        item = await svc.add_invoice_item(
            invoice_id=invoice_id,
            description=request.description,
            amount=request.amount_cents,
            quantity=request.quantity,
            unit_amount=request.unit_amount_cents,
            item_type=request.type,
            usage_quantity=request.usage_quantity,
            usage_metric=request.usage_metric,
            tax_amount=request.tax_cents,
            discount_amount=request.discount_cents,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_INVOICE_UPDATED,
            context=context,
            resource_type="billing_invoice",
            resource_id=invoice_id,
            details={"item_id": item.id, "amount_cents": item.amount},
        )
        return {
            "id": item.id,
            "invoice_id": item.invoice_id,
            "type": item.type,
            "description": item.description,
            "amount_cents": item.amount,
            "amount_dollars": item.amount_dollars,
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.post("/invoices/{invoice_id}/finalize", response_model=finalize_invoiceResult)
async def finalize_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Finalize a draft invoice."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    try:
        inv = await svc.finalize_invoice(invoice_id)
        await _emit_billing_audit(
            action=AuditAction.BILLING_INVOICE_FINALIZED,
            context=context,
            resource_type="billing_invoice",
            resource_id=invoice_id,
            details={"status": inv.status},
        )
        return {
            "id": inv.id,
            "status": inv.status,
            "total_cents": inv.total,
            "total_dollars": inv.total_dollars,
            "amount_due_cents": inv.amount_due,
            "amount_due_dollars": inv.amount_due_dollars,
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


@router.post("/invoices/{invoice_id}/void", response_model=void_invoiceResult)
async def void_invoice(
    invoice_id: str,
    reason: str | None = Query(None, description="Void reason"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Void an invoice."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    try:
        inv = await svc.void_invoice(invoice_id, reason=reason)
        await _emit_billing_audit(
            action=AuditAction.BILLING_INVOICE_VOIDED,
            context=context,
            resource_type="billing_invoice",
            resource_id=invoice_id,
            details={"reason": reason},
        )
        return {
            "id": inv.id,
            "status": inv.status,
            "voided_at": _dt_iso(inv.voided_at),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


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
    """List charge records."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    charges = await svc.list_charges(
        customer_id=customer_id,
        invoice_id=invoice_id,
        status=charge_status,
        limit=limit,
        offset=offset,
    )
    return {
        "charges": [_serialize_charge(charge) for charge in charges],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": len(charges),
        },
    }


@router.post("/charges", response_model=record_chargeResult)
async def record_charge(
    request: RecordChargeRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Record a charge attempt."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    try:
        charge = await svc.record_charge(
            customer_id=request.customer_id,
            amount=request.amount_cents,
            status=request.status,
            invoice_id=request.invoice_id,
            stripe_charge_id=request.stripe_charge_id,
            payment_method_id=request.payment_method_id,
            payment_method_type=request.payment_method_type,
            description=request.description,
        )
        await _emit_billing_audit(
            action=AuditAction.BILLING_CHARGE_RECORDED,
            context=context,
            resource_type="billing_charge",
            resource_id=charge.id,
            details={
                "customer_id": request.customer_id,
                "amount_cents": charge.amount,
                "status": charge.status,
            },
        )
        return {
            "id": charge.id,
            "status": charge.status,
            "amount_cents": charge.amount,
            "amount_dollars": charge.amount_dollars,
            "stripe_charge_id": charge.stripe_charge_id,
            "created_at": _dt_iso(charge.created_at),
        }
    except ValueError as exc:
        _raise_billing_bad_request(exc)


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
    """Get revenue summary for a period."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    return await svc.get_revenue_summary(period_start, period_end)


@router.get("/customers/{customer_id}/balance")
async def get_customer_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get customer balance summary."""
    svc = InvoiceService(db, tenant_id=context.tenant_id)
    return await svc.get_customer_balance(customer_id)


# ---------------------------------------------------------------------------
# Re-export adjacent route modules
# ---------------------------------------------------------------------------


def _is_adjacent_billing_route_initializing(name: str) -> bool:
    import sys

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
