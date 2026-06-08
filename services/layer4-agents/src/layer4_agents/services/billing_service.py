from __future__ import annotations

"""Billing service for Stripe integration.

Handles customer management, subscription lifecycle, and entitlement checks.
Minimal scope: subscription status, customer portal, plan enforcement.
"""


import asyncio
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling import sanitize_log_error

logger = logging.getLogger(__name__)

from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config.plans import check_entitlement, get_entitlements_response
from ..models.billing import (
    BillingCustomer,
    BillingInvoice,
    BillingInvoiceItem,
    BillingSubscription,
    BillingUsageEvent,
    BillingWebhookEvent,
    SubscriptionStatus,
    UsageEventStatus,
)
from .plan_version_service import PlanVersionService
from .stripe_client import StripeError, StripeNotConfiguredError, get_price_id, get_stripe

# Constants for webhook processing
MAX_WEBHOOK_RETRY_ATTEMPTS = 5


class WebhookErrorCode(str, Enum):
    INVALID_SIGNATURE = "WEBHOOK_INVALID_SIGNATURE"
    INVALID_PAYLOAD = "WEBHOOK_INVALID_PAYLOAD"
    MALFORMED_PAYLOAD = "WEBHOOK_MALFORMED_PAYLOAD"
    PROVIDER_ERROR = "WEBHOOK_PROVIDER_ERROR"
    INTERNAL_ERROR = "WEBHOOK_INTERNAL_ERROR"


class WebhookValidationError(ValueError):
    def __init__(self, message: str, *, code: WebhookErrorCode, error_class: str) -> None:
        super().__init__(message)
        self.code = code
        self.error_class = error_class


class BillingService_create_checkout_sessionResult(TypedDictModel):
    session_id: Any
    url: Any

class BillingService_create_portal_sessionResult(TypedDictModel):
    url: Any


class BillingService_cancel_subscriptionResult(TypedDictModel):
    canceled: bool
    cancel_at_period_end: bool
    current_period_end: Any
    subscription_id: Any


class BillingService_update_subscriptionResult(TypedDictModel):
    previous_plan_id: str
    subscription_id: Any
    updated: bool


class BillingService_reactivate_subscriptionResult(TypedDictModel):
    reactivated: bool
    subscription_id: Any


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

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    def _retry_delay_seconds(self, attempt_count: int) -> int:
        return min(300, 2 ** max(0, attempt_count - 1))

    def _emit_webhook_metric(self, metric: str, **extra: Any) -> None:
        """Emit structured webhook operational metric."""
        logger.info(f"billing.webhook.metric.{metric}", extra={"metric": metric, **extra})

    @staticmethod
    def _classify_webhook_exception(exc: Exception) -> tuple[WebhookErrorCode, str, str]:
        exc_name = type(exc).__name__
        if exc_name == "SignatureVerificationError":
            return (WebhookErrorCode.INVALID_SIGNATURE, "Invalid signature", exc_name)
        if isinstance(exc, ValueError):
            return (WebhookErrorCode.INVALID_PAYLOAD, "Invalid payload", exc_name)
        if isinstance(exc, (TypeError, KeyError)):
            return (WebhookErrorCode.MALFORMED_PAYLOAD, "Malformed webhook payload", exc_name)
        if isinstance(exc, StripeError):
            return (WebhookErrorCode.PROVIDER_ERROR, "Webhook provider error", exc_name)
        return (WebhookErrorCode.INTERNAL_ERROR, "Invalid payload", exc_name)

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

                stripe_customer_id = None
                sync_status = "pending"
                sync_error = None
                attempted_at = self._utc_now()
                try:
                    stripe = _get_stripe()
                    stripe_customer = stripe.Customer.create(
                        email=email,
                        name=name or email,
                        metadata={"app_customer_id": customer_id},
                    )
                    stripe_customer_id = stripe_customer.id
                    sync_status = "synced"
                except (StripeNotConfiguredError, StripeError) as e:
                    sync_status = "failed"
                    sync_error = sanitize_log_error(e)
                    logger.warning("Stripe customer creation failed", extra={"customer_id": customer_id, "tenant_id": tenant_id, "error_code": "STRIPE_CUSTOMER_ERROR", "error": sync_error})

                # Create local customer record first; Stripe sync state is explicit
                customer = BillingCustomer(
                    id=customer_id,
                    tenant_id=tenant_id,
                    stripe_customer_id=stripe_customer_id,
                    stripe_sync_status=sync_status,
                    stripe_sync_error=sync_error,
                    stripe_sync_attempted_at=attempted_at,
                    email=email,
                    name=name,
                )
                self.db.add(customer)
                await self.db.flush()

                # Explicitly assign free entitlement as fallback until paid state exists.
                await self._create_free_subscription(customer_id, tenant_id, fallback_entitlement=True)
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
                    logger.error(
                        "POTENTIAL_STRIPE_ORPHAN",
                        extra={
                            "stripe_customer_id": stripe_customer_id,
                            "customer_id": customer_id,
                            "error_code": "STRIPE_ORPHAN_ERROR",
                            "error": sanitize_log_error(e),
                            "action_required": "Reconcile Stripe customer or delete if unused",
                        }
                    )
                raise

        # Should never reach here
        raise RuntimeError(f"Failed to create customer after {max_retries} attempts")

    async def _create_free_subscription(
        self, customer_id: str, tenant_id: str | None = None, fallback_entitlement: bool = True
    ) -> BillingSubscription:
        """Create a free tier subscription for a customer.

        Args:
            customer_id: Internal customer/user ID
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        free_subscription_id = f"free_fallback_{customer_id}" if fallback_entitlement else f"free_{customer_id}"
        subscription = BillingSubscription(
            id=free_subscription_id,
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

    async def reconcile_customer_sync(self, batch_size: int = 100) -> dict[str, int]:
        """Retry failed/pending Stripe sync and emit reconciliation metrics."""
        result = await self.db.execute(
            select(BillingCustomer)
            .where(BillingCustomer.stripe_sync_status.in_(["pending", "failed"]))
            .order_by(BillingCustomer.created_at.asc())
            .limit(batch_size)
        )
        customers = list(result.scalars().all())
        synced = 0
        failed = 0
        for customer in customers:
            customer.stripe_sync_attempted_at = self._utc_now()
            try:
                stripe = _get_stripe()
                stripe_customer = stripe.Customer.create(
                    email=customer.email,
                    name=customer.name or customer.email,
                    metadata={"app_customer_id": customer.id},
                )
                customer.stripe_customer_id = stripe_customer.id
                customer.stripe_sync_status = "synced"
                customer.stripe_sync_error = None
                synced += 1
            except (StripeNotConfiguredError, StripeError) as e:
                customer.stripe_sync_status = "failed"
                customer.stripe_sync_error = sanitize_log_error(e)
                failed += 1

        backlog = len(customers) - synced
        orphan_count = failed
        logger.info(
            "billing.customer_sync_reconciliation",
            extra={
                "reconciliation_backlog": backlog,
                "stripe_orphan_count": orphan_count,
                "synced_count": synced,
                "failed_count": failed,
            },
        )
        await self.db.flush()
        return {"processed": len(customers), "synced": synced, "failed": failed, "backlog": backlog, "orphan_count": orphan_count}

    async def get_active_subscription(self, customer_id: str, tenant_id: str | None = None) -> BillingSubscription | None:
        """Get the active subscription for a customer."""
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .where(BillingSubscription.tenant_id == tenant_id if tenant_id else True)
            .where(BillingSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]))
            .order_by(BillingSubscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_subscription(self, customer_id: str, tenant_id: str | None = None) -> BillingSubscription | None:
        """Get the most recent subscription for a customer (any status)."""
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .where(BillingSubscription.tenant_id == tenant_id if tenant_id else True)
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

    async def ingest_usage_event(
        self,
        *,
        tenant_id: str,
        customer_id: str,
        event_id: str,
        event_name: str,
        metric_name: str,
        quantity: float,
        timestamp: datetime,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BillingUsageEvent:
        """Persist a usage event with tenant-scoped idempotency."""
        usage_event = BillingUsageEvent(
            id=f"usage_{tenant_id}_{event_id}",
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_id=event_id,
            event_name=event_name,
            metric_name=metric_name,
            quantity=quantity,
            unit=unit,
            timestamp=timestamp,
            status=UsageEventStatus.PENDING,
            event_metadata=metadata,
        )
        self.db.add(usage_event)
        try:
            await self.db.flush()
            return usage_event
        except IntegrityError:
            await self.db.rollback()
            result = await self.db.execute(
                select(BillingUsageEvent).where(
                    BillingUsageEvent.tenant_id == tenant_id,
                    BillingUsageEvent.event_id == event_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise

    async def handle_webhook(self, payload: bytes, signature: str, webhook_secret: str) -> BillingWebhookEvent:
        """Persist Stripe webhook event and return inbox entry."""
        # Validate signature is present
        if not signature:
            raise ValueError("Invalid signature: missing signature header")

        try:
            stripe = _get_stripe()
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except Exception as e:
            code, base_message, error_class = self._classify_webhook_exception(e)
            sanitized_error = sanitize_log_error(e)
            logger.warning(
                "billing.webhook.validation_failed",
                extra={"error_code": code.value, "error_class": error_class, "error": sanitized_error},
            )
            self._emit_webhook_metric("validation_failed", error_code=code.value, error_class=error_class)
            raise WebhookValidationError(
                f"{base_message}: {sanitized_error}",
                code=code,
                error_class=error_class,
            ) from e

        event_id = event["id"]
        event_type = event["type"]

        now = self._utc_now()
        payload_hash = hashlib.sha256(payload).hexdigest()
        stmt = (
            insert(BillingWebhookEvent)
            .values(
                id=event_id,
                type=event_type,
                status="pending",
                attempt_count=0,
                payload_hash=payload_hash,
                next_retry_at=now,
            )
            .on_conflict_do_update(
                index_elements=[BillingWebhookEvent.id],
                set_={
                    "status": "pending",
                    "next_retry_at": now,
                    "payload_hash": payload_hash,
                    "type": event_type,
                },
                where=(BillingWebhookEvent.status.in_(["failed", "retryable"])),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        result = await self.db.execute(select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id))
        inbox = result.scalar_one()
        await self.db.commit()
        if inbox.status == "processed":
            logger.info("billing.webhook.duplicate_processed", extra={"event_id": event_id, "event_type": event_type, "duplicate_count": 1})
            self._emit_webhook_metric("duplicate", event_id=event_id, event_type=event_type)
        else:
            self._emit_webhook_metric("accepted", event_id=event_id, event_type=event_type, status=inbox.status)
        return inbox

    async def process_webhook_event(self, event_id: str, payload: bytes, signature: str, webhook_secret: str) -> None:
        """Process persisted webhook inbox event with bounded retries and guaranteed rollback on failure."""
        stripe = _get_stripe()
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        event_type = event["type"]
        # Fetch inside implicit transaction
        result = await self.db.execute(select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id))
        inbox = result.scalar_one_or_none()
        if inbox is None or inbox.status == "processed":
            if inbox is not None:
                self._emit_webhook_metric("duplicate", event_id=event_id, event_type=event_type)
            return
        
        try:
            started_at = self._utc_now()
            inbox.status = "processing"
            inbox.attempt_count += 1
            if event_type == "checkout.session.completed":
                await self._handle_checkout_completed(event["data"]["object"])
            elif event_type == "customer.subscription.created":
                await self._handle_subscription_created(event["data"]["object"])
            elif event_type == "customer.subscription.updated":
                await self._handle_subscription_updated(event["data"]["object"])
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event["data"]["object"])
            elif event_type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(event["data"]["object"])
            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(event["data"]["object"])

            inbox.status = "processed"
            inbox.processed_at = self._utc_now()
            inbox.next_retry_at = None
            inbox.last_error = None
            invoice_obj = event.get("data", {}).get("object", {})
            logger.info(
                "billing.webhook_reconciliation_artifact",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "invoice_id": invoice_obj.get("id"),
                    "invoice_amount_paid": invoice_obj.get("amount_paid"),
                    "invoice_status": invoice_obj.get("status"),
                    "subscription_id": invoice_obj.get("subscription"),
                    "latency_ms": int((self._utc_now() - started_at).total_seconds() * 1000),
                },
            )
            await self.db.flush()
            await self.db.commit()
            self._emit_webhook_metric("processed", event_id=event_id, event_type=event_type, attempt_count=inbox.attempt_count)
        except Exception as exc:
            await self.db.rollback()
            # Record failure state in separate transaction if needed
            transient = isinstance(exc, (StripeError, SQLAlchemyError, asyncio.TimeoutError))
            error_message = sanitize_log_error(exc)
            
            # Re-fetch inbox in new transaction to avoid stale object from rollback
            try:
                await self.db.begin()
                result = await self.db.execute(select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id))
                inbox = result.scalar_one_or_none()
                
                if inbox:
                    inbox.last_error = error_message
                    if transient and inbox.attempt_count < MAX_WEBHOOK_RETRY_ATTEMPTS:
                        inbox.status = "retryable"
                        inbox.next_retry_at = self._utc_now() + timedelta(seconds=self._retry_delay_seconds(inbox.attempt_count))
                        logger.warning("billing.webhook.retry_scheduled", extra={"event_id": event_id, "attempt_count": inbox.attempt_count})
                        self._emit_webhook_metric("retried", event_id=event_id, event_type=event_type, attempt_count=inbox.attempt_count)
                    else:
                        inbox.status = "failed"
                        inbox.next_retry_at = None
                        logger.error("billing.webhook.terminal_failure", extra={"event_id": event_id, "attempt_count": inbox.attempt_count})
                        logger.error("billing.webhook.dlq_routed", extra={"event_id": event_id, "event_type": event_type, "last_error": inbox.last_error, "attempt_count": inbox.attempt_count})
                        self._emit_webhook_metric("failed", event_id=event_id, event_type=event_type, attempt_count=inbox.attempt_count)
                    await self.db.flush()
                await self.db.commit()
            except Exception:
                # If we can't even record the failure, log and continue
                logger.error("billing.webhook.failure_recording_failed", extra={"event_id": event_id}, exc_info=True)
            raise

    async def process_due_webhook_retries(self, payload_lookup: dict[str, bytes], signature: str, webhook_secret: str, limit: int = 100) -> int:
        """Durable retry queue worker for retryable inbox rows.

        Rows in `retryable` with due `next_retry_at` are dequeued and re-processed.
        Failed rows remain as durable DLQ entries with `status=failed`.
        """
        now = self._utc_now()
        due = await self.db.execute(
            select(BillingWebhookEvent)
            .where(BillingWebhookEvent.status == "retryable", BillingWebhookEvent.next_retry_at.is_not(None), BillingWebhookEvent.next_retry_at <= now)
            .order_by(BillingWebhookEvent.next_retry_at.asc())
            .limit(limit)
        )
        processed = 0
        for inbox in due.scalars().all():
            payload = payload_lookup.get(inbox.id)
            if not payload:
                logger.error("billing.webhook.retry_payload_missing", extra={"event_id": inbox.id})
                continue
            await self.process_webhook_event(inbox.id, payload, signature, webhook_secret)
            processed += 1
        return processed

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

        # Extract plan from items (Stripe sends items array with price IDs)
        plan_id = None
        items = stripe_subscription.get("items", {})
        data = items.get("data", [])
        if data:
            price_id = data[0].get("price", {}).get("id")
            if price_id:
                from ..config.plans import PLANS
                for pid, plan in PLANS.items():
                    if getattr(plan, "stripe_price_id", None) == price_id:
                        plan_id = pid
                        break

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
            if plan_id:
                subscription.plan_id = plan_id
            if current_period_start:
                subscription.current_period_start = datetime.fromtimestamp(current_period_start, tz=UTC)
            if current_period_end:
                subscription.current_period_end = datetime.fromtimestamp(current_period_end, tz=UTC)
            await self.db.flush()

    async def _handle_subscription_deleted(self, stripe_subscription: dict[str, Any]) -> None:
        """Handle customer.subscription.deleted event.

        Marks subscription as canceled and downgrades customer to free tier.
        """
        stripe_sub_id = stripe_subscription["id"]

        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            await self.db.flush()
            # Downgrade to free to ensure entitlement checks don't grant paid features
            await self._downgrade_to_free(
                subscription.customer_id, subscription.tenant_id
            )

    async def _handle_subscription_created(self, stripe_subscription: dict[str, Any]) -> None:
        """Handle customer.subscription.created event."""
        stripe_sub_id = stripe_subscription["id"]
        customer_id = stripe_subscription.get("customer")
        status = stripe_subscription.get("status", "incomplete")
        current_period_start = stripe_subscription.get("current_period_start")
        current_period_end = stripe_subscription.get("current_period_end")

        # Find local customer by Stripe customer ID
        result = await self.db.execute(
            select(BillingCustomer)
            .where(BillingCustomer.stripe_customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            logger.warning(
                f"Customer not found for Stripe customer {customer_id} on subscription {stripe_sub_id}"
            )
            return

        # Determine plan from subscription items
        plan_id = "free"
        items = stripe_subscription.get("items", {})
        data = items.get("data", [])
        if data:
            price_id = data[0].get("price", {}).get("id")
            if price_id:
                from ..config.plans import PLANS
                for pid, plan in PLANS.items():
                    if getattr(plan, "stripe_price_id", None) == price_id:
                        plan_id = pid
                        break

        # Create or update subscription record
        result = await self.db.execute(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            subscription = BillingSubscription(
                id=f"sub_{customer.id}_{plan_id}",
                tenant_id=customer.tenant_id,
                customer_id=customer.id,
                stripe_subscription_id=stripe_sub_id,
                plan_id=plan_id,
                status=SubscriptionStatus(status),
            )
            self.db.add(subscription)

        if current_period_start:
            subscription.current_period_start = datetime.fromtimestamp(current_period_start, tz=UTC)
        if current_period_end:
            subscription.current_period_end = datetime.fromtimestamp(current_period_end, tz=UTC)

        await self.db.flush()

    async def _handle_payment_succeeded(self, invoice: dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded event."""
        stripe_invoice_id = invoice.get("id")
        if not stripe_invoice_id:
            return
        result = await self.db.execute(
            select(BillingInvoice).where(BillingInvoice.stripe_invoice_id == stripe_invoice_id)
        )
        local_invoice = result.scalar_one_or_none()
        if local_invoice:
            local_invoice.status = "paid"
            raw_paid = invoice.get("amount_paid")
            raw_due = invoice.get("amount_due")
            raw_total = invoice.get("total")
            local_invoice.amount_paid = int(raw_paid if raw_paid is not None else local_invoice.amount_paid)
            local_invoice.amount_due = int(raw_due if raw_due is not None else local_invoice.amount_due)
            local_invoice.total = int(raw_total if raw_total is not None else local_invoice.total)
            local_invoice.paid_at = self._utc_now()
            await self.db.flush()

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

    async def reconcile_invoice_usage(self, tenant_id: str, invoice_id: str) -> dict[str, Any]:
        """Compare internal usage ledger totals vs invoice metered line items."""
        result = await self.db.execute(
            select(BillingInvoice).where(
                BillingInvoice.id == invoice_id,
                BillingInvoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Invoice not found")

        usage_result = await self.db.execute(
            select(BillingUsageEvent).where(
                BillingUsageEvent.tenant_id == tenant_id,
                BillingUsageEvent.customer_id == invoice.customer_id,
                BillingUsageEvent.timestamp >= invoice.period_start,
                BillingUsageEvent.timestamp <= invoice.period_end,
            )
        )
        usage_events = usage_result.scalars().all()
        usage_totals: dict[str, float] = {}
        for event in usage_events:
            usage_totals[event.metric_name] = usage_totals.get(event.metric_name, 0.0) + float(event.quantity)

        items_result = await self.db.execute(
            select(BillingInvoiceItem).where(
                BillingInvoiceItem.invoice_id == invoice_id,
                BillingInvoiceItem.tenant_id == tenant_id,
            )
        )
        invoice_items = items_result.scalars().all()
        billed_totals: dict[str, float] = {}
        for item in invoice_items:
            metric = item.usage_metric
            if not metric:
                continue
            quantity = (
                item.usage_quantity
                if item.usage_quantity is not None
                else item.quantity
                if item.quantity is not None
                else 0.0
            )
            billed_totals[metric] = billed_totals.get(metric, 0.0) + float(quantity)

        mismatches = []
        for metric in set(usage_totals) | set(billed_totals):
            ledger_value = usage_totals.get(metric, 0.0)
            billed_value = billed_totals.get(metric, 0.0)
            if abs(ledger_value - billed_value) > 1e-9:
                mismatches.append(
                    {"metric_name": metric, "ledger_quantity": ledger_value, "invoice_quantity": billed_value}
                )

        return {"invoice_id": invoice_id, "mismatch_count": len(mismatches), "mismatches": mismatches}

    async def cancel_subscription(
        self,
        customer_id: str,
        tenant_id: str | None = None,
        cancel_immediately: bool = False,
    ) -> dict[str, Any]:
        """Cancel a customer's subscription.

        Args:
            customer_id: Internal customer/user ID
            tenant_id: Optional tenant ID for multi-tenant isolation
            cancel_immediately: If True, cancel immediately; otherwise at period end

        Returns:
            Cancellation result with subscription ID and period end
        """
        subscription = await self.get_active_subscription(customer_id, tenant_id)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found for customer")

        try:
            stripe = _get_stripe()
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=not cancel_immediately,
            )

            subscription.cancel_at_period_end = not cancel_immediately
            if cancel_immediately:
                subscription.status = SubscriptionStatus.CANCELED
                # Downgrade to free immediately
                await self._downgrade_to_free(customer_id, tenant_id)
            else:
                # Mark as will-cancel but keep plan until period end
                subscription.status = SubscriptionStatus.ACTIVE

            await self.db.flush()

            current_period_end = (
                datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC)
                if stripe_sub.current_period_end
                else subscription.current_period_end
            )

            return BillingService_cancel_subscriptionResult.model_validate({
                "canceled": True,
                "cancel_at_period_end": not cancel_immediately,
                "current_period_end": current_period_end,
                "subscription_id": subscription.id,
            })

        except StripeError:
            raise ValueError("Subscription cancellation failed due to a billing provider error") from None

    async def _downgrade_to_free(
        self, customer_id: str, tenant_id: str | None = None
    ) -> BillingSubscription:
        """Create a free-tier subscription for a customer after cancellation.

        Ensures entitlement checks always have a valid subscription record.
        """
        free_sub = await self._create_free_subscription(
            customer_id, tenant_id, fallback_entitlement=False
        )
        return free_sub

    async def update_subscription_plan(
        self,
        customer_id: str,
        new_plan_id: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Update a customer's subscription plan.

        Args:
            customer_id: Internal customer/user ID
            new_plan_id: Target plan ('pro', 'enterprise')
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            Update result with previous and current plan IDs
        """
        subscription = await self.get_active_subscription(customer_id, tenant_id)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found for customer")

        previous_plan_id = subscription.plan_id
        if previous_plan_id == new_plan_id:
            raise ValueError("Customer is already on the requested plan")

        price_id = get_price_id(new_plan_id)
        if not price_id:
            raise ValueError(f"Plan not available: {new_plan_id}")

        try:
            stripe = _get_stripe()
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{"price": price_id, "quantity": 1}],
                proration_behavior="create_prorations",
            )

            subscription.plan_id = new_plan_id
            await self.db.flush()

            return BillingService_update_subscriptionResult.model_validate({
                "previous_plan_id": previous_plan_id,
                "subscription_id": subscription.id,
                "updated": True,
            })

        except StripeError:
            raise ValueError("Plan change failed due to a billing provider error") from None

    async def reactivate_subscription(
        self,
        customer_id: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Reactivate a subscription that was scheduled to cancel at period end.

        Args:
            customer_id: Internal customer/user ID
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            Reactivation result
        """
        stmt = (
            select(BillingSubscription)
            .where(BillingSubscription.customer_id == customer_id)
            .where(BillingSubscription.cancel_at_period_end.is_(True))
            .where(BillingSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]))
            .order_by(BillingSubscription.created_at.desc())
        )
        if tenant_id is not None:
            stmt = stmt.where(BillingSubscription.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No scheduled-to-cancel subscription found for customer")

        try:
            stripe = _get_stripe()
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            subscription.cancel_at_period_end = False
            await self.db.flush()

            return BillingService_reactivate_subscriptionResult.model_validate({
                "reactivated": True,
                "subscription_id": subscription.id,
            })

        except StripeError:
            raise ValueError("Subscription reactivation failed due to a billing provider error") from None

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
