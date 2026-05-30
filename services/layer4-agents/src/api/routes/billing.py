from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Billing API routes for Stripe integration.

Provides endpoints for subscription management, customer portal,
entitlement checks, and usage-based billing. Includes high-throughput
usage event ingestion with idempotency and tenant isolation.
"""


import logging
import os
import re
from datetime import datetime
from typing import Any, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling import sanitize_log_error

# Customer ID validation pattern (alphanumeric, underscore, hyphen; 1-64 chars after prefix)
CUSTOMER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

from ...services.billing_security import (
    STRIPE_WEBHOOK_SKIP_IP_CHECK,
    get_client_ip as _get_client_ip,
    is_stripe_webhook_ip as _is_stripe_webhook_ip,
    validate_webhook_request_security,
)


def validate_customer_id(customer_id: str) -> str:
    """Validate customer_id format to prevent injection attacks.

    Args:
        customer_id: The customer ID to validate

    Returns:
        The validated customer ID

    Raises:
        HTTPException: If customer_id contains invalid characters
    """
    if not customer_id:
        raise ValidationError(message="customer_id is required")
    if not CUSTOMER_ID_PATTERN.match(customer_id):
        raise ValidationError(message="customer_id contains invalid characters")
    return customer_id


from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...database import get_session_factory
from ...services.billing_service import BillingService
from ...services.overage_service import OverageService
from ...services.stripe_client import StripeError
from ...services.usage_service import UsageService, UsageValidationError
from ..common.db import get_route_db


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


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


# ============================================================================
# Request/Response Models
# ============================================================================


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


class UsageEventRequest(BaseModel):
    """Request body for ingesting a single usage event."""

    event_id: str = Field(
        ..., min_length=1, max_length=128, description="Idempotency key"
    )
    customer_id: str = Field(
        ..., min_length=1, max_length=64, description="Customer identifier"
    )
    event_name: str = Field(
        ..., min_length=1, max_length=128, description="Logical event name"
    )
    metric_name: str = Field(
        ..., min_length=1, max_length=64, description="Metered metric name"
    )
    quantity: float = Field(..., ge=0, description="Quantity to record")
    unit: str | None = Field(default=None, max_length=32, description="Unit of measure")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )


class UsageBatchRequest(BaseModel):
    """Request body for batch ingestion of usage events."""

    events: list[UsageEventRequest] = Field(
        ..., min_length=1, max_length=1000, description="Events to ingest"
    )


# ============================================================================
# Subscription Endpoints
# ============================================================================


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get current subscription status for a customer.

    Args:
        customer_id: Internal customer/user ID

    Returns:
        Subscription details including plan and status
    """
    service = BillingService(db)
    subscription = await service.get_subscription(customer_id)

    if not subscription:
        # Return free tier default
        return get_subscriptionResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": None,
                "plan_id": "free",
                "status": "active",
                "current_period_start": None,
                "current_period_end": None,
                "cancel_at_period_end": False,
            }
        )

    return get_subscriptionResult.model_validate(
        {  # type: ignore[no-any-return]
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "current_period_start": (
                subscription.current_period_start.isoformat()
                if subscription.current_period_start
                else None
            ),
            "current_period_end": (
                subscription.current_period_end.isoformat()
                if subscription.current_period_end
                else None
            ),
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
    )


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class CancelSubscriptionResponse(BaseModel):
    canceled: bool
    cancel_at_period_end: bool
    current_period_end: str | None
    subscription_id: str


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


class UsageSummaryResponse(BaseModel):
    customer_id: str
    metric_name: str
    total_quantity: float
    event_count: int
    period_start: str | None
    period_end: str | None


class UsageEventResponse(BaseModel):
    id: str
    event_id: str
    event_name: str
    metric_name: str
    quantity: float
    unit: str
    timestamp: str
    status: str
    metadata: dict[str, Any] | None


class UsageSyncResponse(BaseModel):
    synced: int
    failed: int
    error: str | None


class LimitsCheckResponse(BaseModel):
    allowed: bool
    customer_id: str
    metric_name: str
    quantity: float
    limit: float | None
    current_usage: float | None
    remaining: float | None


class RevenueSummaryResponse(BaseModel):
    total_revenue_cents: int
    total_revenue_dollars: str
    invoice_count: int
    charge_count: int
    period_start: str
    period_end: str


class CustomerBalanceResponse(BaseModel):
    customer_id: str
    open_invoices_cents: int
    open_invoices_dollars: str
    lifetime_paid_cents: int
    lifetime_paid_dollars: str
    balance_cents: int
    balance_dollars: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe checkout session for subscription.

    Args:
        customer_id: Internal customer/user ID
        request: Checkout session parameters

    Returns:
        Session ID and checkout URL
    """
    service = BillingService(db)

    try:
        result = await service.create_checkout_session(
            customer_id=customer_id,
            plan_id=request.plan_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return result
    except ValueError as e:
        logger.warning(f"Checkout creation failed: {e}")
        raise ValidationError(message="Checkout creation failed") from e


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    """Create a Stripe customer portal session.

    Args:
        customer_id: Internal customer/user ID
        request: Portal session parameters

    Returns:
        Portal URL for customer to manage billing
    """
    service = BillingService(db)

    try:
        result = await service.create_portal_session(
            customer_id=customer_id,
            return_url=request.return_url,
        )
        return result
    except ValueError as e:
        logger.warning(f"Portal creation failed: {e}")
        raise ValidationError(message="Portal creation failed") from e


@router.get(
    "/invoices/{invoice_id}/reconciliation", response_model=reconcile_invoiceResult
)
async def reconcile_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Reconcile usage ledger against invoice line items."""
    service = BillingService(db)
    try:
        return await service.reconcile_invoice_usage(context.tenant_id, invoice_id)
    except ValueError as e:
        logger.warning("Invoice reconciliation failed: %s", e)
        raise NotFoundError(message="Invoice not found or cannot be reconciled") from e


# ============================================================================
# Subscription Lifecycle Endpoints
# ============================================================================


class CancelSubscriptionRequest(BaseModel):
    cancel_immediately: bool = Field(
        False, description="Cancel immediately vs at period end"
    )


class UpdatePlanRequest(BaseModel):
    plan_id: str = Field(..., description="Target plan (pro, enterprise)")


@router.post("/subscription/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Cancel a customer's subscription.

    Args:
        customer_id: Internal customer/user ID
        request: Cancellation options

    Returns:
        Cancellation result with period end date
    """
    service = BillingService(db)
    tenant_id = context.tenant_id

    try:
        result = await service.cancel_subscription(
            customer_id=customer_id,
            tenant_id=tenant_id,
            cancel_immediately=request.cancel_immediately,
        )
        return {
            "canceled": result["canceled"],
            "cancel_at_period_end": result["cancel_at_period_end"],
            "current_period_end": (
                result["current_period_end"].isoformat()
                if result["current_period_end"]
                else None
            ),
            "subscription_id": result["subscription_id"],
        }
    except ValueError as e:
        error_text = repr(e).lower()
        logger.warning(
            "Subscription cancellation failed",
            extra={
                "error_type": type(e).__name__,
                "not_found": "subscription" in error_text and "found" in error_text,
            },
        )
        if "subscription" in error_text and "found" in error_text:
            raise NotFoundError(message="Subscription not found") from e
        raise ValidationError(message="Subscription cancellation failed") from e


@router.post("/subscription/update-plan", response_model=UpdatePlanResponse)
async def update_subscription_plan(
    request: UpdatePlanRequest,
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Update a customer's subscription plan.

    Args:
        customer_id: Internal customer/user ID
        request: Target plan details

    Returns:
        Update result with previous and current plan
    """
    service = BillingService(db)
    tenant_id = context.tenant_id

    try:
        result = await service.update_subscription_plan(
            customer_id=customer_id,
            new_plan_id=request.plan_id,
            tenant_id=tenant_id,
        )
        return {
            "previous_plan_id": result["previous_plan_id"],
            "subscription_id": result["subscription_id"],
            "updated": result["updated"],
        }
    except ValueError as e:
        logger.warning(f"Plan update failed: {e}")
        raise ValidationError(message="Plan update failed") from e


@router.post("/subscription/reactivate", response_model=ReactivateSubscriptionResponse)
async def reactivate_subscription(
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Reactivate a subscription scheduled to cancel at period end.

    Args:
        customer_id: Internal customer/user ID

    Returns:
        Reactivation result
    """
    service = BillingService(db)
    tenant_id = context.tenant_id

    try:
        result = await service.reactivate_subscription(
            customer_id=customer_id,
            tenant_id=tenant_id,
        )
        return {
            "reactivated": result["reactivated"],
            "subscription_id": result["subscription_id"],
        }
    except ValueError as e:
        logger.warning(f"Subscription reactivation failed: {e}")
        raise ValidationError(message="Subscription reactivation failed") from e


# ============================================================================
# Entitlement Endpoints
# ============================================================================


@router.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get all feature entitlements for a customer.

    Args:
        customer_id: Internal customer/user ID

    Returns:
        Plan details and feature availability map
    """
    service = BillingService(db)
    return await service.get_entitlements(customer_id)


@router.get("/check-feature", response_model=check_featureResult)
async def check_feature(
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    feature_id: str = Query(..., min_length=1, max_length=64),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Check if a customer has access to a specific feature.

    Args:
        customer_id: Internal customer/user ID
        feature_id: Feature identifier to check

    Returns:
        Feature access status
    """
    service = BillingService(db)
    has_access = await service.check_entitlement(customer_id, feature_id)

    return check_featureResult.model_validate(
        {  # type: ignore[no-any-return]
            "feature_id": feature_id,
            "has_access": has_access,
        }
    )


# ============================================================================
# Customer Management
# ============================================================================


@router.post("/sync-customer", response_model=sync_customerResult)
async def sync_customer(
    request: CustomerSyncRequest,
    customer_id: str = Query(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    ),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Sync customer with Stripe (create or update).

    Args:
        customer_id: Internal customer/user ID
        request: Customer details

    Returns:
        Customer record with Stripe ID if available
    """
    service = BillingService(db)

    # Extract tenant_id from context if available
    tenant_id = context.tenant_id

    customer = await service.get_or_create_customer(
        customer_id=customer_id,
        email=request.email,
        name=request.name,
        tenant_id=tenant_id,
    )

    return sync_customerResult.model_validate(
        {  # type: ignore[no-any-return]
            "id": customer.id,
            "stripe_customer_id": customer.stripe_customer_id,
            "email": customer.email,
            "name": customer.name,
            "tenant_id": customer.tenant_id,
        }
    )


# ============================================================================
# Webhook Endpoint
# ============================================================================


async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    # SECURITY: Webhook uses get_db (no tenant context) intentionally.
    # Stripe server-to-server calls don't carry tenant JWTs.
    # Authentication is via Stripe-Signature HMAC verification + IP allowlist.
    db: AsyncSession = Depends(get_route_db),
) -> dict[str, Any]:
    """Handle Stripe webhook events.

    Processes subscription lifecycle events from Stripe with idempotency.
    Must configure webhook secret in STRIPE_WEBHOOK_SECRET env var.

    SECURITY: Validates request originates from Stripe IP ranges AND
    has valid Stripe-Signature header. Dual verification for defense-in-depth.

    Headers:
        Stripe-Signature: Webhook signature for verification

    Returns:
        Processing status
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise ServiceUnavailableError(message="Webhook processing not configured")

    # SECURITY: Canonical ingress checks for source IP + signature/timestamp shape.
    try:
        validate_webhook_request_security(
            request,
            stripe_signature,
            enforce_ip_check=not STRIPE_WEBHOOK_SKIP_IP_CHECK,
        )
    except HTTPException:
        client_ip = _get_client_ip(request)
        logger.warning(f"Webhook request from non-Stripe IP rejected: {client_ip}")
        raise
    except ValueError as e:
        logger.warning(f"Webhook security validation failed: {e}")
        raise ValidationError(message="Invalid webhook payload") from e

    # Read raw body for signature verification
    body = await request.body()

    service = BillingService(db)

    try:
        inbox = await service.handle_webhook(
            body, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
        if inbox.status != "processed":

            async def _process() -> None:
                session_factory = get_session_factory()
                async with session_factory() as worker_db:
                    worker = BillingService(worker_db)
                    try:
                        await worker.process_webhook_event(
                            inbox.id, body, stripe_signature, STRIPE_WEBHOOK_SECRET
                        )
                        await worker_db.commit()
                    except Exception:
                        await worker_db.rollback()
                        logger.exception("Webhook processing failed")

            background_tasks.add_task(_process)
        return stripe_webhookResult.model_validate({"received": True})  # type: ignore[no-any-return]
    except ValueError as e:
        logger.warning(f"Webhook validation failed: {e}")
        raise ValidationError(message="Invalid webhook payload") from e
    except StripeError as e:
        logger.error(f"Stripe API error during webhook: {e}")
        raise ServiceUnavailableError(message="Stripe processing failed") from e
    except Exception as e:
        logger.exception(f"Unexpected webhook error: {e}")
        raise ServiceUnavailableError(message="Webhook processing failed") from e


# ============================================================================
# Usage Metering Endpoints
# ============================================================================


async def ingest_usage_event(
    request: UsageEventRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Ingest a single usage event for billing.

    Args:
        request: Usage event details

    Returns:
        Ingested event with ID and status

    Raises:
        400: Validation error
        409: Duplicate event (idempotency conflict)
    """
    tenant_id = context.tenant_id

    service = UsageService(db, tenant_id=tenant_id)
    overage_service = OverageService(db, tenant_id=tenant_id)

    try:
        quota_result = await overage_service.validate_request(
            customer_id=request.customer_id,
            metric_name=request.metric_name,
            requested_quantity=request.quantity,
        )
        if not quota_result["allowed"]:
            _raise_quota_exceeded(request.metric_name, quota_result)

        event = await service.ingest_event(
            event_id=request.event_id,
            customer_id=request.customer_id,
            event_name=request.event_name,
            metric_name=request.metric_name,
            quantity=request.quantity,
            unit=request.unit,
            timestamp=request.timestamp,
            metadata=request.metadata,
        )

        return ingest_usage_eventResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": event.id,
                "event_id": event.event_id,
                "status": event.status,
                "tenant_id": event.tenant_id,
                "customer_id": event.customer_id,
                "metric_name": event.metric_name,
                "quantity": event.quantity,
                "timestamp": event.timestamp.isoformat(),
                "created_at": event.created_at.isoformat(),
            }
        )

    except UsageValidationError as e:
        raise ValidationError(
            message="Request failed", details={"error": e.message, "field": e.field}
        )
    except Exception as e:
        logger.exception(f"Usage event ingestion failed: {e}")
        raise ServiceUnavailableError(message="Failed to ingest usage event")


async def ingest_usage_batch(
    request: UsageBatchRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Ingest multiple usage events in a batch.

    Args:
        request: Batch of usage events (max 1000)

    Returns:
        Summary with counts of created, duplicate, and error events

    Raises:
        400: Batch validation error
    """
    tenant_id = context.tenant_id

    service = UsageService(db, tenant_id=tenant_id)
    overage_service = OverageService(db, tenant_id=tenant_id)

    try:
        projected_usage: dict[tuple[str, str], float] = {}
        for event in request.events:
            key = (event.customer_id, event.metric_name)
            projected_usage[key] = projected_usage.get(key, 0.0) + event.quantity

        for (customer_id, metric_name), total_requested in projected_usage.items():
            quota_result = await overage_service.validate_request(
                customer_id=customer_id,
                metric_name=metric_name,
                requested_quantity=total_requested,
            )
            if not quota_result["allowed"]:
                _raise_quota_exceeded(metric_name, quota_result)

        # Convert Pydantic models to dicts for the service
        events_data = [event.model_dump() for event in request.events]
        result = await service.ingest_batch(events_data)

        return ingest_usage_batchResult.model_validate(
            {  # type: ignore[no-any-return]
                "created": result["created"],
                "duplicates": result["duplicates"],
                "errors": result["errors"],
                "error_details": result.get("error_details"),
            }
        )

    except UsageValidationError as e:
        raise ValidationError(
            message="Request failed", details={"error": e.message, "field": e.field}
        )
    except Exception as e:
        logger.exception(f"Batch ingestion failed: {e}")
        raise ServiceUnavailableError(message="Failed to process batch")


async def get_usage_summary(
    customer_id: str,
    metric_name: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get aggregated usage summary for a customer and metric.

    Args:
        customer_id: Customer to query
        metric_name: Metric to aggregate
        start_date: Start of period (ISO format)
        end_date: End of period (ISO format)

    Returns:
        Usage summary with total quantity and event count
    """
    tenant_id = context.tenant_id

    service = UsageService(db, tenant_id=tenant_id)

    try:
        summary = await service.get_usage_summary(
            customer_id=customer_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
        )
        return summary

    except UsageValidationError as e:
        raise ValidationError(message="Request failed", details={"error": e.message})
    except Exception as e:
        logger.exception(f"Usage summary failed: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve usage summary")


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
    """List individual usage events for a customer.

    Args:
        customer_id: Customer to query
        metric_name: Optional metric filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum results (1-1000)
        offset: Pagination offset

    Returns:
        List of usage events
    """
    tenant_id = context.tenant_id

    service = UsageService(db, tenant_id=tenant_id)

    try:
        events = await service.list_customer_usage(
            customer_id=customer_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return [
            {
                "id": e.id,
                "event_id": e.event_id,
                "event_name": e.event_name,
                "metric_name": e.metric_name,
                "quantity": e.quantity,
                "unit": e.unit,
                "timestamp": e.timestamp.isoformat(),
                "status": e.status,
                "metadata": e.metadata,
            }
            for e in events
        ]

    except UsageValidationError as e:
        raise ValidationError(message="Request failed", details={"error": e.message})
    except Exception as e:
        logger.exception(f"Usage events listing failed: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve usage events")


async def sync_usage_to_stripe(
    customer_id: str,
    metric_name: str | None = None,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Sync pending usage events to Stripe MeterEvents.

    Aggregates pending usage and reports to Stripe for metered billing.
    Requires Stripe customer to be linked and STRIPE_METER_EVENTS_ENABLED=true.

    Args:
        customer_id: Customer to sync usage for
        metric_name: Optional metric filter (syncs all if omitted)

    Returns:
        Sync summary with counts and Stripe responses

    Raises:
        400: Validation error or no Stripe customer linked
        402: Stripe not configured
    """
    tenant_id = context.tenant_id

    service = UsageService(db, tenant_id=tenant_id)

    try:
        result = await service.sync_to_stripe(
            customer_id=customer_id,
            metric_name=metric_name,
        )

        # Check for errors in result
        if "error" in result and result["synced"] == 0:
            if "No Stripe customer ID" in result["error"]:
                raise ValidationError(
                    message="Request failed",
                    details={
                        "error": result["error"],
                        "action": "Sync customer with Stripe first via /billing/sync-customer",
                    },
                )
            if "Stripe not configured" in result["error"]:
                raise ServiceUnavailableError(
                    message="Stripe MeterEvents not configured",
                )

        return result

    except UsageValidationError as e:
        raise ValidationError(message="Request failed", details={"error": e.message})
    except Exception as e:
        logger.exception(f"Stripe sync failed: {e}")
        raise ServiceUnavailableError(message="Failed to sync usage to Stripe")


# ============================================================================
# Overage Detection & Limits
# ============================================================================


async def get_usage_limits(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get current usage and limits for a customer.

    Returns all configured limits and current usage percentages.
    Use this to show progress bars or warnings in the UI.

    Args:
        customer_id: Customer to check

    Returns:
        Usage limits and current consumption for all metrics
    """
    tenant_id = context.tenant_id

    service = OverageService(db, tenant_id=tenant_id)

    try:
        quota_check = await service.check_all_limits(customer_id)

        return get_usage_limitsResult.model_validate(
            {  # type: ignore[no-any-return]
                "customer_id": quota_check.customer_id,
                "plan_id": quota_check.plan_id,
                "all_limits_ok": quota_check.all_limits_ok,
                "warnings": quota_check.warnings,
                "total_overage_cost": quota_check.total_overage_cost,
                "metrics": [
                    {
                        "metric_name": check.metric_name,
                        "current_usage": check.current_usage,
                        "limit": check.limit if check.limit != float("inf") else None,
                        "percentage_used": check.percentage_used,
                        "remaining": check.remaining,
                        "overage": check.overage,
                        "overage_cost": check.overage_cost,
                        "warning_triggered": check.warning_triggered,
                        "limit_exceeded": check.limit_exceeded,
                        "period": {
                            "start": check.period_start.isoformat(),
                            "end": check.period_end.isoformat(),
                        },
                    }
                    for check in quota_check.checks
                ],
            }
        )

    except Exception as e:
        logger.exception(f"Usage limits check failed: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve usage limits")


async def check_request_allowed(
    customer_id: str,
    metric_name: str,
    quantity: float = Query(1.0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Check if a request should be allowed based on usage limits.

    Use this endpoint before processing expensive operations to validate
    that the customer has quota remaining. Returns 402 Payment Required
    if the hard limit is exceeded.

    Args:
        customer_id: Customer making the request
        metric_name: Metric being consumed
        quantity: Amount to be consumed

    Returns:
        Validation result with allow/deny decision

    Raises:
        402: Hard limit exceeded (upgrade required)
        400: Invalid request
    """
    tenant_id = context.tenant_id

    service = OverageService(db, tenant_id=tenant_id)

    try:
        result = await service.validate_request(customer_id, metric_name, quantity)

        if not result["allowed"]:
            _raise_quota_exceeded(metric_name, result)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Request validation failed: {e}")
        raise ServiceUnavailableError(message="Failed to validate request")


async def get_plan_limits(
    plan_id: str,
) -> dict[str, Any]:
    """Get the configured usage limits for a plan.

    Returns the limits configuration without customer-specific usage data.
    Useful for displaying plan details in pricing pages.

    Args:
        plan_id: Plan identifier (free, pro, enterprise)

    Returns:
        Plan limits configuration
    """
    from ...config.plans import get_plan

    plan = get_plan(plan_id)
    if not plan:
        raise NotFoundError(message=str(f"Plan not found: {plan_id}"))

    service = OverageService(cast(AsyncSession, None), tenant_id=None)  # No DB needed
    limits = service.get_plan_limits(plan_id)

    return get_plan_limitsResult.model_validate(
        {  # type: ignore[no-any-return]
            "plan_id": plan_id,
            "plan_name": plan.name,
            "limits": limits,
        }
    )


# ============================================================================
# Invoice Management
# ============================================================================


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
    type: str = Field(
        default="one_time",
        description="Item type: subscription, metered, one_time, proration",
    )
    usage_quantity: float | None = Field(
        None, description="Usage quantity for metered items"
    )
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


@router.get("/invoices", response_model=list_invoicesResult)
async def list_invoices(
    customer_id: str | None = Query(None),
    invoice_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """List invoices with optional filters.

    Returns paginated list of invoices for the tenant, optionally filtered
    by customer and status.
    """
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        invoices = await service.list_invoices(
            customer_id=customer_id,
            status=invoice_status,
            limit=limit,
            offset=offset,
        )

        return list_invoicesResult.model_validate(
            {  # type: ignore[no-any-return]
                "invoices": [
                    {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "customer_id": inv.customer_id,
                        "status": inv.status,
                        "currency": inv.currency,
                        "total_cents": inv.total,
                        "total_dollars": inv.total_dollars,
                        "amount_due_cents": inv.amount_due,
                        "amount_due_dollars": inv.amount_due_dollars,
                        "period_start": inv.period_start.isoformat(),
                        "period_end": inv.period_end.isoformat(),
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                        "created_at": inv.created_at.isoformat(),
                        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                        "item_count": len(inv.items),
                    }
                    for inv in invoices
                ],
                "pagination": {"limit": limit, "offset": offset},
            }
        )

    except Exception as e:
        logger.exception(f"Failed to list invoices: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve invoices")


@router.post("/invoices", response_model=create_invoiceResult)
async def create_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Create a new invoice.

    Creates a draft invoice for the specified customer and billing period.
    Add line items via POST /invoices/{id}/items, then finalize via POST /invoices/{id}/finalize.
    """
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        invoice = await service.create_invoice(
            customer_id=request.customer_id,
            period_start=request.period_start,
            period_end=request.period_end,
            invoice_number=request.invoice_number,
            subscription_id=request.subscription_id,
            currency=request.currency,
            description=request.description,
        )

        return create_invoiceResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_id": invoice.customer_id,
                "status": invoice.status,
                "total_cents": invoice.total,
                "total_dollars": invoice.total_dollars,
                "created_at": invoice.created_at.isoformat(),
            }
        )

    except ValueError as e:
        logger.warning(
            "invoice_value_error",
            extra={"error_code": "INVOICE_VALUE_ERROR", "error": sanitize_log_error(e)},
        )
        raise ValidationError(message="Invalid invoice request")
    except Exception as e:
        logger.exception(f"Failed to create invoice: {e}")
        raise ServiceUnavailableError(message="Failed to create invoice")


@router.get("/invoices/{invoice_id}", response_model=get_invoiceResult)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get invoice details including line items and charges."""
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        invoice = await service.get_invoice(
            invoice_id, include_items=True, include_charges=True
        )

        if not invoice:
            raise NotFoundError(message="Invoice not found")

        return get_invoiceResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_id": invoice.customer_id,
                "status": invoice.status,
                "currency": invoice.currency,
                "subtotal_cents": invoice.subtotal,
                "tax_cents": invoice.tax,
                "total_cents": invoice.total,
                "total_dollars": invoice.total_dollars,
                "amount_paid_cents": invoice.amount_paid,
                "amount_due_cents": invoice.amount_due,
                "amount_due_dollars": invoice.amount_due_dollars,
                "balance_cents": invoice.balance,
                "period_start": invoice.period_start.isoformat(),
                "period_end": invoice.period_end.isoformat(),
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "created_at": invoice.created_at.isoformat(),
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "description": invoice.description,
                "hosted_invoice_url": invoice.hosted_invoice_url,
                "invoice_pdf_url": invoice.invoice_pdf_url,
                "items": [
                    {
                        "id": item.id,
                        "type": item.type,
                        "description": item.description,
                        "quantity": float(item.quantity),
                        "unit_amount_cents": item.unit_amount,
                        "amount_cents": item.amount,
                        "amount_dollars": item.amount_dollars,
                        "usage_quantity": (
                            float(item.usage_quantity) if item.usage_quantity else None
                        ),
                        "usage_metric": item.usage_metric,
                        "tax_cents": item.tax_amount,
                        "discount_cents": item.discount_amount,
                    }
                    for item in invoice.items
                ],
                "charges": [
                    {
                        "id": charge.id,
                        "status": charge.status,
                        "amount_cents": charge.amount,
                        "amount_dollars": charge.amount_dollars,
                        "stripe_charge_id": charge.stripe_charge_id,
                        "payment_method_type": charge.payment_method_type,
                        "created_at": charge.created_at.isoformat(),
                    }
                    for charge in invoice.charges
                ],
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get invoice: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve invoice")


@router.post("/invoices/{invoice_id}/items", response_model=add_invoice_itemResult)
async def add_invoice_item(
    invoice_id: str,
    request: AddInvoiceItemRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Add a line item to an invoice."""
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        item = await service.add_invoice_item(
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

        return add_invoice_itemResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": item.id,
                "invoice_id": item.invoice_id,
                "type": item.type,
                "description": item.description,
                "amount_cents": item.amount,
                "amount_dollars": item.amount_dollars,
            }
        )

    except ValueError as e:
        logger.warning(
            "invoice_item_value_error",
            extra={
                "error_code": "INVOICE_ITEM_VALUE_ERROR",
                "error": sanitize_log_error(e),
            },
        )
        raise ValidationError(message="Invalid invoice item request")
    except Exception as e:
        logger.exception(f"Failed to add invoice item: {e}")
        raise ServiceUnavailableError(message="Failed to add invoice item")


@router.post("/invoices/{invoice_id}/finalize", response_model=finalize_invoiceResult)
async def finalize_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Finalize a draft invoice (make it open/payable).

    Recalculates totals from line items and changes status to 'open'.
    """
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        invoice = await service.finalize_invoice(invoice_id)

        return finalize_invoiceResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": invoice.id,
                "status": invoice.status,
                "total_cents": invoice.total,
                "total_dollars": invoice.total_dollars,
                "amount_due_cents": invoice.amount_due,
                "amount_due_dollars": invoice.amount_due_dollars,
            }
        )

    except ValueError as e:
        logger.warning(
            "invoice_finalize_value_error",
            extra={
                "error_code": "INVOICE_FINALIZE_VALUE_ERROR",
                "error": sanitize_log_error(e),
            },
        )
        raise ValidationError(message="Invalid invoice finalize request")
    except Exception as e:
        logger.exception(f"Failed to finalize invoice: {e}")
        raise ServiceUnavailableError(message="Failed to finalize invoice")


@router.post("/invoices/{invoice_id}/void", response_model=void_invoiceResult)
async def void_invoice(
    invoice_id: str,
    reason: str | None = Query(None, description="Void reason"),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Void an invoice."""
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        invoice = await service.void_invoice(invoice_id, reason=reason)

        return void_invoiceResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": invoice.id,
                "status": invoice.status,
                "voided_at": (
                    invoice.voided_at.isoformat() if invoice.voided_at else None
                ),
            }
        )

    except ValueError as e:
        logger.warning(
            "invoice_void_value_error",
            extra={
                "error_code": "INVOICE_VOID_VALUE_ERROR",
                "error": sanitize_log_error(e),
            },
        )
        raise ValidationError(message="Invalid invoice void request")
    except Exception as e:
        logger.exception(f"Failed to void invoice: {e}")
        raise ServiceUnavailableError(message="Failed to void invoice")


# ============================================================================
# Charge Management
# ============================================================================


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
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        charges = await service.list_charges(
            customer_id=customer_id,
            invoice_id=invoice_id,
            status=charge_status,
            limit=limit,
            offset=offset,
        )

        return list_chargesResult.model_validate(
            {  # type: ignore[no-any-return]
                "charges": [
                    {
                        "id": chg.id,
                        "customer_id": chg.customer_id,
                        "invoice_id": chg.invoice_id,
                        "status": chg.status,
                        "amount_cents": chg.amount,
                        "amount_dollars": chg.amount_dollars,
                        "amount_refunded_cents": chg.amount_refunded,
                        "net_amount_cents": chg.net_amount,
                        "stripe_charge_id": chg.stripe_charge_id,
                        "payment_method_type": chg.payment_method_type,
                        "failure_code": chg.failure_code,
                        "failure_message": chg.failure_message,
                        "receipt_url": chg.receipt_url,
                        "created_at": chg.created_at.isoformat(),
                    }
                    for chg in charges
                ],
                "pagination": {"limit": limit, "offset": offset},
            }
        )

    except Exception as e:
        logger.exception(f"Failed to list charges: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve charges")


@router.post("/charges", response_model=record_chargeResult)
async def record_charge(
    request: RecordChargeRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Record a charge attempt."""
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        charge = await service.record_charge(
            customer_id=request.customer_id,
            amount=request.amount_cents,
            status=request.status,
            invoice_id=request.invoice_id,
            stripe_charge_id=request.stripe_charge_id,
            payment_method_id=request.payment_method_id,
            payment_method_type=request.payment_method_type,
            description=request.description,
        )

        return record_chargeResult.model_validate(
            {  # type: ignore[no-any-return]
                "id": charge.id,
                "status": charge.status,
                "amount_cents": charge.amount,
                "amount_dollars": charge.amount_dollars,
                "stripe_charge_id": charge.stripe_charge_id,
                "created_at": charge.created_at.isoformat(),
            }
        )

    except ValueError as e:
        logger.warning(
            "charge_value_error",
            extra={"error_code": "CHARGE_VALUE_ERROR", "error": sanitize_log_error(e)},
        )
        raise ValidationError(message="Invalid charge request")
    except Exception as e:
        logger.exception(f"Failed to record charge: {e}")
        raise ServiceUnavailableError(message="Failed to record charge")


# ============================================================================
# Reporting
# ============================================================================


@router.get("/reports/revenue", response_model=RevenueSummaryResponse)
async def get_revenue_summary(
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get revenue summary for a period.

    Returns aggregated invoice and charge totals for the specified period.
    """
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        summary = await service.get_revenue_summary(period_start, period_end)
        return summary
    except Exception as e:
        logger.exception(f"Failed to get revenue summary: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve revenue summary")


@router.get("/customers/{customer_id}/balance", response_model=CustomerBalanceResponse)
async def get_customer_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get customer balance summary.

    Returns open invoice amounts and lifetime payment totals.
    """
    from ...services.invoice_service import InvoiceService

    tenant_id = context.tenant_id
    service = InvoiceService(db, tenant_id=tenant_id)

    try:
        balance = await service.get_customer_balance(customer_id)
        return balance
    except Exception as e:
        logger.exception(f"Failed to get customer balance: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve customer balance")


def _raise_quota_exceeded(metric_name: str, result: dict[str, Any]) -> None:
    """Raise a standardized hard-limit response for quota failures."""
    raise ServiceUnavailableError(
        message=result.get("error", f"Usage limit exceeded for {metric_name}"),
        details={
            "metric": metric_name,
            "limit": result.get("limit"),
            "current_usage": result.get("current_usage"),
            "requested": result.get("requested"),
            "overage": result.get("overage"),
            "upgrade_required": True,
        },
    )


# Local route modules register cohesive billing route groups without changing public paths.
from .billing_overages import router as overage_router
from .billing_usage import router as usage_router
from .billing_webhooks import router as webhook_router

router.include_router(webhook_router)
router.include_router(usage_router)
router.include_router(overage_router)
