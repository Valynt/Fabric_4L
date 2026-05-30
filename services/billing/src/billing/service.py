"""BillingService – core business logic for Stripe-integrated billing.

This class owns all interactions with the Stripe API and the billing
database.  It is intentionally decoupled from FastAPI (no ``Request``
types, no dependency-injection decorators) so it can be unit-tested
without a running HTTP server.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import structlog

from .models import BillingCustomer, BillingSubscription, BillingWebhookEvent, SubscriptionStatus

logger = structlog.get_logger(__name__)


def _hash_email(email: str) -> str:
    """Return SHA-256 hex digest of the lower-cased email (for privacy)."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


class BillingService:
    """Service layer for Stripe billing operations.

    All methods accept an ``AsyncSession`` so callers control transaction
    boundaries.  No direct Stripe API calls are made unless a live
    ``stripe_client`` is injected (defaults to ``None`` for unit tests).
    """

    def __init__(self, stripe_client: Any = None) -> None:
        """Initialise the service.

        Args:
            stripe_client: Optional Stripe SDK client.  When ``None`` the
                service operates in *stub mode* and skips all Stripe calls
                (useful for unit tests and dev environments without keys).
        """
        self._stripe = stripe_client

    # ------------------------------------------------------------------
    # Customer management
    # ------------------------------------------------------------------

    async def get_or_create_customer(
        self,
        session: Any,
        *,
        user_id: str,
        tenant_id: str,
        email: str,
        name: str | None = None,
    ) -> BillingCustomer:
        """Return an existing customer or create a new one.

        If a Stripe client is configured the customer is also synced to Stripe
        asynchronously (the sync status is updated on the returned row).

        Args:
            session: SQLAlchemy ``AsyncSession``.
            user_id: Application user identifier (primary key in billing DB).
            tenant_id: Tenant that owns the customer row.
            email: Customer email address.  Stored as a SHA-256 hash.
            name: Optional display name forwarded to Stripe.

        Returns:
            The ``BillingCustomer`` ORM instance (may be newly created).
        """
        from sqlalchemy import select

        stmt = select(BillingCustomer).where(
            BillingCustomer.id == user_id,
            BillingCustomer.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer is None:
            customer = BillingCustomer(
                id=user_id,
                tenant_id=tenant_id,
                email_hash=_hash_email(email),
                stripe_sync_status="pending",
            )
            session.add(customer)
            await session.flush()
            logger.info("billing_customer_created", user_id=user_id, tenant_id=tenant_id)

        if self._stripe is not None and customer.stripe_customer_id is None:
            try:
                stripe_customer = self._stripe.customers.create(
                    email=email,
                    name=name,
                    metadata={"user_id": user_id, "tenant_id": tenant_id},
                )
                customer.stripe_customer_id = stripe_customer.id
                customer.stripe_sync_status = "synced"
                logger.info("stripe_customer_synced", stripe_id=stripe_customer.id, user_id=user_id)
            except Exception as e:
                customer.stripe_sync_status = "failed"
                logger.exception("stripe_customer_sync_failed", user_id=user_id, error_type=type(e).__name__)

        return customer

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        session: Any,
        *,
        user_id: str,
        tenant_id: str,
        plan_id: str,
        stripe_price_id: str,
    ) -> BillingSubscription:
        """Create a new subscription record.

        Args:
            session: SQLAlchemy ``AsyncSession``.
            user_id: Application user identifier.
            tenant_id: Owning tenant.
            plan_id: Internal plan name (``free`` / ``pro`` / ``enterprise``).
            stripe_price_id: Stripe Price ID to attach the subscription to.

        Returns:
            The newly created ``BillingSubscription`` ORM instance.
        """
        sub_id = str(uuid.uuid4())
        subscription = BillingSubscription(
            id=sub_id,
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            stripe_price_id=stripe_price_id,
            status=SubscriptionStatus.INCOMPLETE.value,
        )
        session.add(subscription)
        await session.flush()
        logger.info("billing_subscription_created", sub_id=sub_id, plan_id=plan_id, user_id=user_id)
        return subscription

    async def get_active_subscription(
        self,
        session: Any,
        *,
        user_id: str,
        tenant_id: str,
    ) -> BillingSubscription | None:
        """Return the most recent active/trialing subscription for a user.

        Args:
            session: SQLAlchemy ``AsyncSession``.
            user_id: Application user identifier.
            tenant_id: Owning tenant.

        Returns:
            The active ``BillingSubscription`` or ``None`` if none exists.
        """
        from sqlalchemy import select

        active_statuses = {SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value}
        stmt = (
            select(BillingSubscription)
            .where(
                BillingSubscription.user_id == user_id,
                BillingSubscription.tenant_id == tenant_id,
                BillingSubscription.status.in_(active_statuses),
            )
            .order_by(BillingSubscription.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancel_subscription(
        self,
        session: Any,
        *,
        subscription_id: str,
        tenant_id: str,
        at_period_end: bool = True,
    ) -> BillingSubscription:
        """Cancel a subscription (immediately or at period end).

        Args:
            session: SQLAlchemy ``AsyncSession``.
            subscription_id: Internal subscription UUID.
            tenant_id: Tenant that owns the subscription (for RLS enforcement).
            at_period_end: When ``True`` the subscription remains active until
                the end of the billing period before cancelling.

        Returns:
            The updated ``BillingSubscription`` ORM instance.

        Raises:
            ValueError: If the subscription is not found or belongs to a
                different tenant.
        """
        from sqlalchemy import select

        stmt = select(BillingSubscription).where(
            BillingSubscription.id == subscription_id,
            BillingSubscription.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription is None:
            raise ValueError(f"Subscription {subscription_id!r} not found for tenant {tenant_id!r}")

        if at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.status = SubscriptionStatus.CANCELED.value
            subscription.cancel_at_period_end = False

        if self._stripe is not None and subscription.stripe_subscription_id:
            try:
                self._stripe.subscriptions.update(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=at_period_end,
                )
            except Exception as e:
                logger.exception("stripe_cancel_failed", sub_id=subscription_id, error_type=type(e).__name__)

        await session.flush()
        logger.info("billing_subscription_cancelled", sub_id=subscription_id, at_period_end=at_period_end)
        return subscription

    # ------------------------------------------------------------------
    # Webhook processing
    # ------------------------------------------------------------------

    async def process_webhook(
        self,
        session: Any,
        *,
        event_id: str,
        tenant_id: str,
        event_type: str,
        livemode: bool,
        raw_payload: dict,
    ) -> bool:
        """Idempotently process a Stripe webhook event.

        Returns ``True`` if the event was processed for the first time,
        ``False`` if it was already recorded (duplicate).

        Args:
            session: SQLAlchemy ``AsyncSession``.
            event_id: Stripe event ID.
            tenant_id: Tenant context (from webhook routing).
            event_type: Stripe event type string.
            livemode: Whether this is a live-mode event.
            raw_payload: Complete deserialized webhook payload.

        Returns:
            ``True`` on first processing; ``False`` for duplicates.
        """
        from sqlalchemy import select

        stmt = select(BillingWebhookEvent).where(
            BillingWebhookEvent.id == event_id,
            BillingWebhookEvent.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            logger.info("billing_webhook_duplicate", event_id=event_id)
            return False

        webhook_record = BillingWebhookEvent(
            id=event_id,
            tenant_id=tenant_id,
            event_type=event_type,
            livemode=livemode,
            processed_at=datetime.now(UTC),
            raw_payload=raw_payload,
        )
        session.add(webhook_record)

        await self._handle_webhook_event(session, event_type=event_type, payload=raw_payload, tenant_id=tenant_id)
        await session.flush()

        logger.info("billing_webhook_processed", event_id=event_id, event_type=event_type)
        return True

    async def _handle_webhook_event(
        self,
        session: Any,
        *,
        event_type: str,
        payload: dict,
        tenant_id: str,
    ) -> None:
        """Dispatch a webhook event to the appropriate handler."""
        handlers = {
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }
        handler = handlers.get(event_type)
        if handler is not None:
            await handler(session, payload=payload, tenant_id=tenant_id)
        else:
            logger.debug("billing_webhook_unhandled_type", event_type=event_type)

    async def _handle_subscription_updated(
        self,
        session: Any,
        *,
        payload: dict,
        tenant_id: str,
    ) -> None:
        """Update subscription status from a Stripe webhook."""
        from sqlalchemy import select

        stripe_sub = payload.get("object", {})
        stripe_sub_id = stripe_sub.get("id")
        if not stripe_sub_id:
            return

        stmt = select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == stripe_sub_id,
            BillingSubscription.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub is None:
            return

        sub.status = stripe_sub.get("status", sub.status)
        sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", sub.cancel_at_period_end)

        period_start = stripe_sub.get("current_period_start")
        period_end = stripe_sub.get("current_period_end")
        if period_start is not None:
            sub.current_period_start = datetime.fromtimestamp(period_start, tz=UTC)
        if period_end is not None:
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=UTC)

    async def _handle_subscription_deleted(
        self,
        session: Any,
        *,
        payload: dict,
        tenant_id: str,
    ) -> None:
        """Mark a subscription as canceled from a Stripe webhook."""
        from sqlalchemy import select

        stripe_sub = payload.get("object", {})
        stripe_sub_id = stripe_sub.get("id")
        if not stripe_sub_id:
            return

        stmt = select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == stripe_sub_id,
            BillingSubscription.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub is not None:
            sub.status = SubscriptionStatus.CANCELED.value
