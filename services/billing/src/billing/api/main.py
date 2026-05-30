"""FastAPI application for the billing service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Any

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import close_db, get_session, init_db
from ..schemas import (
    CustomerCreateRequest,
    CustomerRead,
    ErrorResponse,
    SubscriptionCreateRequest,
    SubscriptionRead,
    WebhookPayload,
)
from ..service import BillingService

logger = structlog.get_logger(__name__)

# OpenTelemetry bootstrap — aligns with shared framework contract (P0-007)
try:
    from value_fabric.shared.fastapi_framework.app import init_telemetry, instrument_fastapi_app
except ImportError:
    init_telemetry = None  # type: ignore[assignment]
    instrument_fastapi_app = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    """Start-up and shut-down lifecycle hooks."""
    logger.info("billing_service_starting", version="0.1.0")
    await init_db()
    logger.info("billing_database_ready")
    yield
    logger.info("billing_service_stopping")
    await close_db()


app = FastAPI(
    title="Billing Service",
    description="Stripe-integrated subscription billing for Value Fabric",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

if init_telemetry is not None:
    app.state.telemetry_provider = init_telemetry("billing")
    if instrument_fastapi_app is not None:
        instrument_fastapi_app(app, enabled=app.state.telemetry_provider is not None)
        logger.info("billing_telemetry_initialized", service="billing")


# ---------------------------------------------------------------------------
# Shared dependency helpers
# ---------------------------------------------------------------------------


def _get_billing_service() -> BillingService:
    """Instantiate BillingService without a live Stripe client.

    In production, inject a configured ``stripe`` client via the app state
    or dependency override.
    """
    return BillingService(stripe_client=None)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ServiceDep = Annotated[BillingService, Depends(_get_billing_service)]


def _require_tenant(x_tenant_id: str = Header(..., alias="X-Tenant-Id")) -> str:
    """Extract tenant ID from the ``X-Tenant-Id`` header.

    In a full deployment this is provided by ``GovernanceMiddleware`` after
    validating the JWT.  For service-to-service calls the caller sets this
    header explicitly.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Tenant-Id header")
    return x_tenant_id


TenantDep = Annotated[str, Depends(_require_tenant)]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["ops"], include_in_schema=False)
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


@app.post(
    "/v1/customers",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    tags=["customers"],
    summary="Create or sync a billing customer",
)
async def create_customer(
    body: CustomerCreateRequest,
    tenant_id: TenantDep,
    session: SessionDep,
    service: ServiceDep,
) -> Any:
    """Create a billing customer record and optionally sync it to Stripe."""
    customer = await service.get_or_create_customer(
        session,
        user_id=body.user_id,
        tenant_id=tenant_id,
        email=body.email,
        name=body.name,
    )
    return CustomerRead(
        user_id=customer.id,
        tenant_id=customer.tenant_id,
        stripe_customer_id=customer.stripe_customer_id,
        stripe_sync_status=customer.stripe_sync_status,
        created_at=customer.created_at,
    )


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@app.post(
    "/v1/subscriptions",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["subscriptions"],
    summary="Create a subscription",
)
async def create_subscription(
    body: SubscriptionCreateRequest,
    tenant_id: TenantDep,
    session: SessionDep,
    service: ServiceDep,
) -> Any:
    """Create a new subscription record."""
    sub = await service.create_subscription(
        session,
        user_id=body.user_id,
        tenant_id=tenant_id,
        plan_id=body.plan_id.value,
        stripe_price_id=body.stripe_price_id,
    )
    return SubscriptionRead(
        id=sub.id,
        user_id=sub.user_id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


@app.get(
    "/v1/subscriptions/active",
    response_model=SubscriptionRead | None,
    tags=["subscriptions"],
    summary="Get active subscription for a user",
)
async def get_active_subscription(
    user_id: str,
    tenant_id: TenantDep,
    session: SessionDep,
    service: ServiceDep,
) -> Any:
    """Return the current active or trialing subscription, or null."""
    sub = await service.get_active_subscription(session, user_id=user_id, tenant_id=tenant_id)
    if sub is None:
        return None
    return SubscriptionRead(
        id=sub.id,
        user_id=sub.user_id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


@app.delete(
    "/v1/subscriptions/{subscription_id}",
    response_model=SubscriptionRead,
    tags=["subscriptions"],
    summary="Cancel a subscription",
)
async def cancel_subscription(
    subscription_id: str,
    tenant_id: TenantDep,
    session: SessionDep,
    service: ServiceDep,
    at_period_end: bool = True,
) -> Any:
    """Cancel a subscription immediately or at the end of the billing period."""
    try:
        sub = await service.cancel_subscription(
            session,
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            at_period_end=at_period_end,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found") from None
    return SubscriptionRead(
        id=sub.id,
        user_id=sub.user_id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@app.post(
    "/v1/webhooks/stripe",
    tags=["webhooks"],
    summary="Receive Stripe webhook events",
    status_code=status.HTTP_200_OK,
)
async def stripe_webhook(
    payload: WebhookPayload,
    tenant_id: TenantDep,
    session: SessionDep,
    service: ServiceDep,
) -> dict[str, str]:
    """Idempotently process an inbound Stripe webhook event."""
    processed = await service.process_webhook(
        session,
        event_id=payload.id,
        tenant_id=tenant_id,
        event_type=payload.type,
        livemode=payload.livemode,
        raw_payload=payload.data,
    )
    return {"status": "processed" if processed else "duplicate"}


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a sanitised 500 – no stack traces in production responses."""
    logger.exception("unhandled_error", path=request.url.path, exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error="internal_server_error").model_dump(),
    )
