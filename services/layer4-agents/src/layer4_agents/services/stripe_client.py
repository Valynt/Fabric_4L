from __future__ import annotations

"""Stripe SDK client configuration and initialization.

Includes support for Stripe MeterEvents (usage-based billing).
"""
import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class report_meter_eventResult(TypedDictModel):
    event_name: Any
    id: Any
    reason: str | None = None
    skipped: bool | None = None
    status: Any
    stripe_customer_id: Any

class sync_usage_to_stripeResult(TypedDictModel):
    error: Any
    stripe_response: Any | None = None
    synced: int
    total_quantity: int

class get_billing_meterResult(TypedDictModel):
    display_name: Any
    event_name: Any
    id: Any
    status: Any

logger = logging.getLogger(__name__)

# Optional stripe import for environments where it's not installed
try:
    import stripe
    _stripe_available = True
except ImportError:
    stripe = None  # type: ignore
    _stripe_available = False
    logger.warning("stripe module not installed - billing features disabled")

# Initialize Stripe with API key from environment
_stripe_api_key = os.environ.get("STRIPE_SECRET_KEY", "")
if _stripe_available and _stripe_api_key:
    stripe.api_key = _stripe_api_key
    logger.info("Stripe SDK initialized")
else:
    logger.warning("Stripe not configured - billing features disabled")

# Price IDs from environment (set in Stripe Dashboard)
STRIPE_PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_ENTERPRISE = os.environ.get("STRIPE_PRICE_ENTERPRISE", "")

# Valid plan IDs
VALID_PLANS = {"pro", "enterprise"}


class StripeNotConfiguredError(Exception):
    """Raised when Stripe is not properly configured."""
    pass


class StripeError(Exception):
    """Raised when a Stripe API call fails."""
    pass


def get_stripe() -> Any:
    """Get configured Stripe module.

    Raises:
        StripeNotConfiguredError: If stripe module is not installed or not configured.
    """
    if stripe is None:
        raise StripeNotConfiguredError(
            "Stripe module not installed. Install with: pip install stripe"
        )
    if not getattr(stripe, 'api_key', None):
        raise StripeNotConfiguredError(
            "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable."
        )
    return stripe


def get_price_id(plan_id: str) -> str | None:
    """Get Stripe price ID for a plan.

    Args:
        plan_id: Plan identifier ('pro' or 'enterprise')

    Returns:
        Stripe price ID or None if plan not found or not configured
    """
    if plan_id not in VALID_PLANS:
        logger.warning(f"Invalid plan_id: {plan_id}. Valid plans: {VALID_PLANS}")
        return None

    price_map = {
        "pro": STRIPE_PRICE_PRO,
        "enterprise": STRIPE_PRICE_ENTERPRISE,
    }
    price_id = price_map.get(plan_id)

    if not price_id:
        logger.warning(f"Price ID not configured for plan: {plan_id}")

    return price_id


# MeterEvents configuration for usage-based billing
STRIPE_METER_API_KEY = os.environ.get("STRIPE_METER_API_KEY", "")  # Can be separate from main key
STRIPE_METER_EVENTS_ENABLED = os.environ.get("STRIPE_METER_EVENTS_ENABLED", "false").lower() == "true"

# Map internal metric names to Stripe event names
STRIPE_METER_EVENT_MAP = {
    "api_calls": "api_requests",
    "tokens": "llm_tokens",
    "bytes": "data_processed",
    "compute_hours": "compute_time",
    "storage_gb": "storage_usage",
}


class StripeMeterEventError(Exception):
    """Raised when a Stripe MeterEvent call fails."""
    pass


def report_meter_event(
    stripe_customer_id: str,
    metric_name: str,
    quantity: float,
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Report a usage event to Stripe for metered billing.

    Uses Stripe's MeterEvents API for usage-based billing.
    https://stripe.com/docs/api/billing/meter-event

    Args:
        stripe_customer_id: Stripe customer ID (cus_*)
        metric_name: Internal metric name (e.g., 'api_calls', 'tokens')
        quantity: Numeric quantity consumed
        timestamp: Optional event timestamp (defaults to now)
        event_id: Optional unique identifier for idempotency

    Returns:
        Stripe MeterEvent response

    Raises:
        StripeNotConfiguredError: If Stripe is not configured
        StripeMeterEventError: If the API call fails
    """
    if not STRIPE_METER_EVENTS_ENABLED:
        logger.debug("Stripe MeterEvents disabled - skipping meter reporting")
        return report_meter_eventResult.model_validate({"skipped": True, "reason": "disabled"})  # type: ignore[no-any-return]

    stripe = get_stripe()

    # Map internal metric to Stripe event name
    stripe_event_name = STRIPE_METER_EVENT_MAP.get(metric_name, metric_name)

    # Prepare payload
    if quantity != int(quantity):
        logger.warning(
            f"Quantity {quantity} has fractional part, truncating to {int(quantity)} for Stripe MeterEvent"
        )
    payload: dict[str, Any] = {
        "event_name": stripe_event_name,
        "payload": {
            "value": str(int(quantity)),  # Stripe requires string integer
            "stripe_customer_id": stripe_customer_id,
        },
        "identifier": event_id or f"evt_{stripe_customer_id}_{datetime.now(UTC).timestamp()}",
    }

    # Add timestamp if provided
    if timestamp:
        payload["timestamp"] = int(timestamp.timestamp())

    try:
        # Use meter events API
        meter_event = stripe.billing.meter_event.create(**payload)
        logger.debug(
            f"MeterEvent reported: {stripe_event_name}={quantity} for {stripe_customer_id}"
        )
        return report_meter_eventResult.model_validate({  # type: ignore[no-any-return]
            "id": meter_event.id,
            "event_name": meter_event.event_name,
            "status": meter_event.status,
            "stripe_customer_id": stripe_customer_id,
        })


    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Failed to report meter event: {e}")
        raise StripeMeterEventError(f"Stripe MeterEvent failed: {e}") from e


def get_billing_meter(
    meter_id: str | None = None,
    meter_name: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Get or list Stripe billing meters.

    Args:
        meter_id: Specific meter ID to retrieve
        meter_name: Filter meters by name

    Returns:
        Meter details or None
    """
    if not STRIPE_METER_EVENTS_ENABLED:
        return None

    stripe = get_stripe()

    try:
        if meter_id:
            meter = stripe.billing.meter.retrieve(meter_id)
            return get_billing_meterResult.model_validate({  # type: ignore[no-any-return]
                "id": meter.id,
                "display_name": meter.display_name,
                "event_name": meter.event_name,
                "status": meter.status,
            })


        else:
            # List meters
            meters = stripe.billing.meter.list()
            return [
                {
                    "id": m.id,
                    "display_name": m.display_name,
                    "event_name": m.event_name,
                    "status": m.status,
                }
                for m in meters.data
            ]

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Failed to get billing meter: {e}")
        return None


async def sync_usage_to_stripe(
    db_session: Any,
    tenant_id: str,
    customer_id: str,
    metric_name: str,
    stripe_customer_id: str,
) -> dict[str, Any]:
    """Sync pending usage events to Stripe MeterEvents.

    This is a background task that aggregates pending usage and reports
    to Stripe for metered billing.

    Args:
        db_session: Database session for querying events
        tenant_id: Tenant ID for scoping
        customer_id: Internal customer ID
        metric_name: Metric to sync
        stripe_customer_id: Stripe customer ID

    Returns:
        Sync summary with counts
    """
    from sqlalchemy import func, select

    from ..models.billing import BillingUsageEvent, UsageEventStatus

    # Query pending events
    query = select(
        func.sum(BillingUsageEvent.quantity).label("total"),
        func.count(BillingUsageEvent.id).label("count"),
    ).where(
        BillingUsageEvent.tenant_id == tenant_id,
        BillingUsageEvent.customer_id == customer_id,
        BillingUsageEvent.metric_name == metric_name,
        BillingUsageEvent.status == UsageEventStatus.PENDING,
    )

    result = await db_session.execute(query)
    row = result.one()
    total_quantity = float(row.total or 0)
    event_count = row.count or 0

    if total_quantity <= 0:
        return sync_usage_to_stripeResult.model_validate({"synced": 0, "total_quantity": 0, "stripe_response": None})  # type: ignore[no-any-return]

    # Report to Stripe
    try:
        stripe_response = report_meter_event(
            stripe_customer_id=stripe_customer_id,
            metric_name=metric_name,
            quantity=total_quantity,
        )

        # Mark events as processed
        update_query = select(BillingUsageEvent).where(
            BillingUsageEvent.tenant_id == tenant_id,
            BillingUsageEvent.customer_id == customer_id,
            BillingUsageEvent.metric_name == metric_name,
            BillingUsageEvent.status == UsageEventStatus.PENDING,
        )

        events_result = await db_session.execute(update_query)
        events = events_result.scalars().all()

        processed_at = datetime.now(UTC)
        for event in events:
            event.status = UsageEventStatus.PROCESSED
            event.processed_at = processed_at

        await db_session.flush()

        return sync_usage_to_stripeResult.model_validate({  # type: ignore[no-any-return]
            "synced": event_count,
            "total_quantity": total_quantity,
            "stripe_response": stripe_response,
        })


    except StripeMeterEventError as e:
        logger.error(f"Failed to sync usage to Stripe: {e}")
        return sync_usage_to_stripeResult.model_validate({"synced": 0, "total_quantity": total_quantity, "error": "STRIPE_SYNC_ERROR"})  # type: ignore[no-any-return]
