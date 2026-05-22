"""Billing service for Stripe integration.

Handles customer management, subscription lifecycle, and entitlement checks.
Minimal scope: subscription status, customer portal, plan enforcement.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config.plans import check_entitlement, get_entitlements_response
from ..models.billing import (
    BillingPlanVersion,
    BillingCustomer,
    BillingSubscription,
    BillingWebhookEvent,
    SubscriptionStatus,
)
from .plan_version_service import PlanVersionService
from .stripe_client import StripeError, StripeNotConfiguredError, get_price_id, get_stripe


class BillingService_create_checkout_sessionResult(TypedDictModel):
    session_id: Any
    url: Any

class BillingService_create_portal_sessionResult(TypedDictModel):
    url: Any

# Lazy-loaded stripe module
_stripe = None

def _get_stripe():
    """Get stripe module (lazy loaded)."""
    global _stripe
    if _stripe is None:
        _stripe = get_stripe()
    return _stripe


class BillingService:
    """Service for billing operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.plan_versions = PlanVersionService(db)

    async def get_or_create_customer(
        self,
        customer_id: str,
        email: str,
        name: str | None = None,
        tenant_id: str | None = None,
    ) -> BillingCustomer:
        """Get existing customer or create new one with Stripe sync.

        Uses retry loop with exponential backoff to handle race conditions
        where multiple concurrent requests attempt to create the same customer.

        Args:
            customer_id: Internal customer/user ID
            email: Customer email address
            name: Optional customer name
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        max_retries = 3
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Check local DB first (within transaction)
                # Note: RLS filters by tenant_id automatically when app.tenant_id is set
                result = await self.db.execute(
                    select(BillingCustomer).where(BillingCustomer.id == customer_id)
                )
                customer = result.scalar_one_or_none()

                if customer:
                    # Update email/name if changed
                    if customer.email != email or (name and customer.name != name):
                        customer.email = email
                        if name:
                            customer.name = name
                        await self.db.flush()
                    return customer

                # Create Stripe customer first (idempotent operation)
                stripe_customer_id = None
                try:
                    stripe = _get_stripe()
                    stripe_customer = stripe.Customer.create(
                        email=email,
                        name=name or email,
                        metadata={"app_customer_id": customer_id},
                    )
                    stripe_customer_id = stripe_customer.id
                except StripeNotConfiguredError as e:
                    # Log but continue - we can retry Stripe sync later
                    logger.warning(f"Stripe customer creation failed: {e}")

                # Create local customer record within transaction
                customer = BillingCustomer(
                    id=customer_id,
                    tenant_id=tenant_id,
                    stripe_customer_id=stripe_customer_id,
                    email=email,
                    name=name,
                )
                self.db.add(customer)
                await self.db.flush()

                # Create default free subscription with tenant_id
                await self._create_free_subscription(customer_id, tenant_id)
                # Note: Caller (billing.py) handles transaction commit

                return customer

            except IntegrityError:
                # Race condition: another request created the customer
                await self.db.rollback()
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"Customer creation race detected, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                # Last attempt failed, re-raise
                raise
            except SQLAlchemyError as e:
                await self.db.rollback()
                logger.error("Billing customer creation failed", extra={"customer_id": customer_id, "tenant_id": tenant_id, "error_type": type(e).__name__}, exc_info=True)
                # Compensation: Log potential Stripe orphan for cleanup
                # If stripe_customer_id was created but DB failed, we have an orphan
                if stripe_customer_id:
                    logger.warning(
                        "POTENTIAL_STRIPE_ORPHAN",
                        extra={
                            "stripe_customer_id": stripe_customer_id,
                            "customer_id": customer_id,
                            "error": str(e),
                            "action_required": "Reconcile Stripe customer or delete if unused",
                        }
                    )
                raise

        # Should never reach here
        raise RuntimeError(f"Failed to create customer after {max_retries} attempts")

    async def _create_free_subscription(
        self, customer_id: str, tenant_id: str | None = None
    ) -> BillingSubscription:
        """Create a free tier subscription for a customer.

        Args:
            customer_id: Internal customer/user ID
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        subscription = BillingSubscription(
            id=f"free_{customer_id}",
            tenant_id=tenant_id,
            customer_id=customer_id,
            plan_id="free",
            status=SubscriptionStatus.ACTIVE,
            stripe_subscription_id=None,
        )
        plan_version = await self.plan_versions.get_effective_plan_version("free", datetime.now(UTC))
        if plan_version:
            subscription.plan_version_id = plan_version.id
        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def get_active_subscription(self, customer_id: str) -> BillingSubscription | None:
        """Get the active subscription for a customer."""
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .where(BillingSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]))
            .order_by(BillingSubscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_subscription(self, customer_id: str) -> BillingSubscription | None:
        """Get the most recent subscription for a customer (any status)."""
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .order_by(BillingSubscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def create_checkout_session(
        self,
        customer_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create a Stripe checkout session for subscription."""
        # Get or create customer
        result = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer or not customer.stripe_customer_id:
            raise ValueError("Customer not found or not synced with Stripe")

        price_id = get_price_id(plan_id)
        if not price_id:
            raise ValueError(f"No Stripe price configured for plan: {plan_id}")

        try:
            stripe = _get_stripe()
            session = stripe.checkout.Session.create(
                customer=customer.stripe_customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"plan_id": plan_id, "customer_id": customer_id},
            )
            return BillingService_create_checkout_sessionResult.model_validate({
                "session_id": session.id,
                "url": session.url,
            })


        except StripeError as e:
            raise ValueError(f"Failed to create checkout session: {e}") from e

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> dict[str, Any]:
        """Create a Stripe customer portal session."""
        result = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer or not customer.stripe_customer_id:
            raise ValueError("Customer not found or not synced with Stripe")

        try:
            stripe = _get_stripe()
            session = stripe.billing_portal.Session.create(
                customer=customer.stripe_customer_id,
                return_url=return_url,
            )
            return BillingService_create_portal_sessionResult.model_validate({"url": session.url})
        except StripeError as e:
            raise ValueError(f"Failed to create portal session: {e}") from e

    async def handle_webhook(self, payload: bytes, signature: str, webhook_secret: str) -> bool:
        """Handle Stripe webhook event with idempotency check."""
        # Validate signature is present
        if not signature:
            raise ValueError("Invalid signature: missing signature header")

        try:
            stripe = _get_stripe()
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except ValueError as e:
            raise ValueError(f"Invalid payload: {e}") from e
        except (TypeError, KeyError) as e:
            if "signature" in str(e).lower():
                raise ValueError(f"Invalid signature: {e}") from e
            raise ValueError(f"Malformed webhook payload: {e}") from e

        event_id = event["id"]
        event_type = event["type"]

        # Check idempotency (SELECT check is a cache optimization)
        result = await self.db.execute(
            select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id)
        )
        if result.scalar_one_or_none():
            logger.info(f"Webhook {event_id} already processed (idempotent)")
            return True  # Already processed

        # Process event with transaction safety
        try:
            if event_type == "checkout.session.completed":
                await self._handle_checkout_completed(event["data"]["object"])
            elif event_type == "customer.subscription.updated":
                await self._handle_subscription_updated(event["data"]["object"])
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event["data"]["object"])
            elif event_type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(event["data"]["object"])
            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(event["data"]["object"])

            # Record event as processed
            webhook_event = BillingWebhookEvent(
                id=event_id,
                type=event_type,
                tenant_id=None,  # Set during event processing if available
            )
            self.db.add(webhook_event)
            await self.db.flush()

            return True

        except IntegrityError:
            # Race condition: another request processed this event concurrently
            # The unique constraint on BillingWebhookEvent.id caught it
            await self.db.rollback()
            logger.info(f"Webhook {event_id} processed concurrently (idempotent)")
            return True
        except SQLAlchemyError as exc:
            # Database error - rollback to maintain consistency
            await self.db.rollback()
            logger.error("Webhook persistence failure", extra={"event_id": event_id, "event_type": event_type, "error_type": type(exc).__name__}, exc_info=True)
            raise

    async def _handle_checkout_completed(self, session: dict[str, Any]) -> None:
        """Handle checkout.session.completed event.

        SECURITY: Verifies customer exists in database before creating subscription
        to prevent metadata spoofing attacks.
        """
        customer_id = session.get("metadata", {}).get("customer_id")
        plan_id = session.get("metadata", {}).get("plan_id")
        subscription_id = session.get("subscription")

        if not customer_id or not plan_id:
            logger.warning(f"Missing customer_id or plan_id in checkout session: {session.get('id')}")
            return

        # SECURITY: Verify customer exists - prevents spoofed metadata
        customer_result = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()

        if not customer:
            logger.warning(
                f"Customer {customer_id} not found for checkout session {session.get('id')}. "
                f"Possible spoofed metadata."
            )
            return

        tenant_id = customer.tenant_id

        # Update or create subscription
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .where(BillingSubscription.plan_id == plan_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.stripe_subscription_id = subscription_id
            subscription.status = SubscriptionStatus.ACTIVE
            plan_version = await self.plan_versions.get_effective_plan_version(plan_id, datetime.now(UTC))
            if plan_version:
                subscription.plan_version_id = plan_version.id
        else:
            plan_version = await self.plan_versions.get_effective_plan_version(plan_id, datetime.now(UTC))
            subscription = BillingSubscription(
                id=f"sub_{customer_id}_{plan_id}",
                tenant_id=tenant_id,
                customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_id=plan_id,
                plan_version_id=plan_version.id if plan_version else None,
                status=SubscriptionStatus.ACTIVE,
            )
            self.db.add(subscription)
            logger.info(f"Created subscription for customer {customer_id}, plan {plan_id}")

        await self.db.flush()

    async def _handle_subscription_updated(self, stripe_subscription: dict[str, Any]) -> None:
        """Handle customer.subscription.updated event."""
        stripe_sub_id = stripe_subscription["id"]
        status = stripe_subscription["status"]
        current_period_start = stripe_subscription.get("current_period_start")
        current_period_end = stripe_subscription.get("current_period_end")
        cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

        # Find local subscription
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Validate status against known enum values
            try:
                subscription.status = SubscriptionStatus(status)
            except ValueError:
                logger.warning(f"Unknown subscription status from Stripe: {status}")
                # Keep existing status if unknown
            subscription.cancel_at_period_end = cancel_at_period_end
            if current_period_start:
                subscription.current_period_start = datetime.fromtimestamp(current_period_start, tz=UTC)
            if current_period_end:
                subscription.current_period_end = datetime.fromtimestamp(current_period_end, tz=UTC)
            await self.db.flush()

    async def _handle_subscription_deleted(self, stripe_subscription: dict[str, Any]) -> None:
        """Handle customer.subscription.deleted event."""
        stripe_sub_id = stripe_subscription["id"]

        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            await self.db.flush()

    async def _handle_payment_succeeded(self, invoice: dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded event."""
        # Could track payment history here if needed
        pass

    async def _handle_payment_failed(self, invoice: dict[str, Any]) -> None:
        """Handle invoice.payment_failed event."""
        # Could trigger notifications here if needed
        subscription_id = invoice.get("subscription")
        if subscription_id:
            result = await self.db.execute(
                select(BillingSubscription)
                .where(BillingSubscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                subscription.status = SubscriptionStatus.PAST_DUE
                await self.db.flush()

    async def check_entitlement(self, customer_id: str, feature_id: str) -> bool:
        """Check if customer has access to a feature."""
        # Get subscription
        subscription = await self.get_active_subscription(customer_id)
        plan_id = subscription.plan_id if subscription else "free"

        await self.plan_versions.ensure_bootstrap_defaults()
        plan_version = await self.plan_versions.get_subscription_plan_version(subscription, datetime.now(UTC))
        if plan_version:
            feature_ids = set((plan_version.features or {}).get("ids", []))
            return feature_id in feature_ids or "*" in feature_ids
        return check_entitlement(plan_id, feature_id)

    async def get_entitlements(self, customer_id: str) -> dict[str, Any]:
        """Get all entitlements for a customer."""
        subscription = await self.get_active_subscription(customer_id)
        plan_id = subscription.plan_id if subscription else "free"

        await self.plan_versions.ensure_bootstrap_defaults()
        plan_version = await self.plan_versions.get_subscription_plan_version(subscription, datetime.now(UTC))
        if plan_version:
            feature_ids = set((plan_version.features or {}).get("ids", []))
            return {
                "plan_id": plan_id,
                "plan_name": plan_id.title(),
                "features": {feature: {"enabled": True} for feature in feature_ids},
                "plan_version_id": plan_version.id,
                "plan_version": plan_version.version,
            }
        return get_entitlements_response(plan_id)
