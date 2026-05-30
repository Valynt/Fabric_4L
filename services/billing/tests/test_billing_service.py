"""Tests for BillingService – subscription management, customer sync, webhooks."""

from __future__ import annotations

import pytest

from billing.models import BillingSubscription, SubscriptionStatus
from billing.service import BillingService, _hash_email


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _svc(stripe_client=None) -> BillingService:
    return BillingService(stripe_client=stripe_client)


# ---------------------------------------------------------------------------
# Email hashing
# ---------------------------------------------------------------------------


class TestHashEmail:
    def test_deterministic(self):
        assert _hash_email("user@example.com") == _hash_email("user@example.com")

    def test_case_insensitive(self):
        assert _hash_email("User@Example.COM") == _hash_email("user@example.com")

    def test_whitespace_stripped(self):
        assert _hash_email("  user@example.com  ") == _hash_email("user@example.com")

    def test_sha256_length(self):
        assert len(_hash_email("x@y.z")) == 64


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------


class TestGetOrCreateCustomer:
    @pytest.mark.asyncio
    async def test_creates_new_customer(self, db_session):
        svc = _svc()
        customer = await svc.get_or_create_customer(
            db_session,
            user_id="u1",
            tenant_id="t1",
            email="user@example.com",
        )
        assert customer.id == "u1"
        assert customer.tenant_id == "t1"
        assert customer.stripe_sync_status == "pending"
        assert len(customer.email_hash) == 64

    @pytest.mark.asyncio
    async def test_returns_existing_customer(self, db_session):
        svc = _svc()
        first = await svc.get_or_create_customer(
            db_session, user_id="u1", tenant_id="t1", email="user@example.com"
        )
        await db_session.commit()

        second = await svc.get_or_create_customer(
            db_session, user_id="u1", tenant_id="t1", email="user@example.com"
        )
        assert first.id == second.id

    @pytest.mark.asyncio
    async def test_with_name(self, db_session):
        svc = _svc()
        customer = await svc.get_or_create_customer(
            db_session,
            user_id="u2",
            tenant_id="t2",
            email="u2@example.com",
            name="Alice",
        )
        assert customer.id == "u2"

    @pytest.mark.asyncio
    async def test_stripe_sync_called(self, db_session):
        """When a stripe_client is provided, customer is synced to Stripe."""

        class FakeStripeCustomers:
            def create(self, **kwargs):
                class _Cust:
                    id = "cus_test123"

                return _Cust()

        class FakeStripe:
            customers = FakeStripeCustomers()

        svc = _svc(stripe_client=FakeStripe())
        customer = await svc.get_or_create_customer(
            db_session,
            user_id="u3",
            tenant_id="t3",
            email="u3@example.com",
        )
        assert customer.stripe_customer_id == "cus_test123"
        assert customer.stripe_sync_status == "synced"

    @pytest.mark.asyncio
    async def test_stripe_sync_failure_marks_failed(self, db_session):
        """Stripe errors are swallowed; sync status is set to 'failed'."""

        class BrokenStripe:
            class customers:  # noqa: D106
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("stripe unavailable")

        svc = _svc(stripe_client=BrokenStripe())
        customer = await svc.get_or_create_customer(
            db_session, user_id="u4", tenant_id="t4", email="u4@example.com"
        )
        assert customer.stripe_sync_status == "failed"


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------


class TestCreateSubscription:
    @pytest.mark.asyncio
    async def test_creates_subscription(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session,
            user_id="u1",
            tenant_id="t1",
            plan_id="pro",
            stripe_price_id="price_abc",
        )
        assert sub.user_id == "u1"
        assert sub.tenant_id == "t1"
        assert sub.plan_id == "pro"
        assert sub.status == SubscriptionStatus.INCOMPLETE.value

    @pytest.mark.asyncio
    async def test_subscription_has_uuid_id(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session,
            user_id="u1",
            tenant_id="t1",
            plan_id="free",
            stripe_price_id="price_free",
        )
        import uuid
        uuid.UUID(sub.id)  # should not raise


class TestGetActiveSubscription:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_subscription(self, db_session):
        svc = _svc()
        result = await svc.get_active_subscription(db_session, user_id="nobody", tenant_id="t1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_active_subscription(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.ACTIVE.value
        await db_session.flush()

        result = await svc.get_active_subscription(db_session, user_id="u1", tenant_id="t1")
        assert result is not None
        assert result.id == sub.id

    @pytest.mark.asyncio
    async def test_returns_trialing_subscription(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u2", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.TRIALING.value
        await db_session.flush()

        result = await svc.get_active_subscription(db_session, user_id="u2", tenant_id="t1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ignores_canceled_subscription(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u3", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.CANCELED.value
        await db_session.flush()

        result = await svc.get_active_subscription(db_session, user_id="u3", tenant_id="t1")
        assert result is None


class TestCancelSubscription:
    @pytest.mark.asyncio
    async def test_cancel_at_period_end(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.ACTIVE.value
        await db_session.flush()

        cancelled = await svc.cancel_subscription(
            db_session, subscription_id=sub.id, tenant_id="t1", at_period_end=True
        )
        assert cancelled.cancel_at_period_end is True
        assert cancelled.status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_cancel_immediately(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.ACTIVE.value
        await db_session.flush()

        cancelled = await svc.cancel_subscription(
            db_session, subscription_id=sub.id, tenant_id="t1", at_period_end=False
        )
        assert cancelled.status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_cancel_wrong_tenant_raises(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        await db_session.flush()

        with pytest.raises(ValueError, match="not found"):
            await svc.cancel_subscription(
                db_session, subscription_id=sub.id, tenant_id="wrong_tenant"
            )

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_raises(self, db_session):
        svc = _svc()
        with pytest.raises(ValueError, match="not found"):
            await svc.cancel_subscription(
                db_session, subscription_id="nonexistent", tenant_id="t1"
            )

    @pytest.mark.asyncio
    async def test_stripe_cancel_called(self, db_session):
        """Cancel calls the Stripe API when a stripe_subscription_id is set."""
        calls = []

        class FakeStripeSubscriptions:
            def update(self, sub_id, **kwargs):
                calls.append((sub_id, kwargs))

        class FakeStripe:
            subscriptions = FakeStripeSubscriptions()

        svc = _svc(stripe_client=FakeStripe())
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.stripe_subscription_id = "sub_stripe_123"
        await db_session.flush()

        await svc.cancel_subscription(db_session, subscription_id=sub.id, tenant_id="t1")
        assert len(calls) == 1
        assert calls[0][0] == "sub_stripe_123"


# ---------------------------------------------------------------------------
# Webhook processing
# ---------------------------------------------------------------------------


class TestProcessWebhook:
    @pytest.mark.asyncio
    async def test_processes_new_event(self, db_session):
        svc = _svc()
        processed = await svc.process_webhook(
            db_session,
            event_id="evt_001",
            tenant_id="t1",
            event_type="customer.subscription.updated",
            livemode=False,
            raw_payload={"object": {}},
        )
        assert processed is True

    @pytest.mark.asyncio
    async def test_duplicate_event_returns_false(self, db_session):
        svc = _svc()
        await svc.process_webhook(
            db_session,
            event_id="evt_dup",
            tenant_id="t1",
            event_type="invoice.paid",
            livemode=False,
            raw_payload={},
        )
        await db_session.commit()

        processed_again = await svc.process_webhook(
            db_session,
            event_id="evt_dup",
            tenant_id="t1",
            event_type="invoice.paid",
            livemode=False,
            raw_payload={},
        )
        assert processed_again is False

    @pytest.mark.asyncio
    async def test_subscription_updated_webhook(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.stripe_subscription_id = "sub_123"
        sub.status = SubscriptionStatus.ACTIVE.value
        await db_session.flush()

        await svc.process_webhook(
            db_session,
            event_id="evt_upd_001",
            tenant_id="t1",
            event_type="customer.subscription.updated",
            livemode=False,
            raw_payload={
                "object": {
                    "id": "sub_123",
                    "status": "past_due",
                    "cancel_at_period_end": False,
                    "current_period_start": 1700000000,
                    "current_period_end": 1702592000,
                }
            },
        )
        await db_session.refresh(sub)
        assert sub.status == "past_due"

    @pytest.mark.asyncio
    async def test_subscription_deleted_webhook(self, db_session):
        svc = _svc()
        sub = await svc.create_subscription(
            db_session, user_id="u1", tenant_id="t1", plan_id="pro", stripe_price_id="price_pro"
        )
        sub.stripe_subscription_id = "sub_del_001"
        sub.status = SubscriptionStatus.ACTIVE.value
        await db_session.flush()

        await svc.process_webhook(
            db_session,
            event_id="evt_del_001",
            tenant_id="t1",
            event_type="customer.subscription.deleted",
            livemode=False,
            raw_payload={"object": {"id": "sub_del_001"}},
        )
        await db_session.refresh(sub)
        assert sub.status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_unknown_event_type_stored(self, db_session):
        """Unrecognised event types are stored without error."""
        svc = _svc()
        processed = await svc.process_webhook(
            db_session,
            event_id="evt_unknown_001",
            tenant_id="t1",
            event_type="charge.succeeded",
            livemode=True,
            raw_payload={"object": {}},
        )
        assert processed is True

    @pytest.mark.asyncio
    async def test_webhook_missing_stripe_id_safe(self, db_session):
        """Webhooks with missing Stripe subscription IDs are handled safely."""
        svc = _svc()
        processed = await svc.process_webhook(
            db_session,
            event_id="evt_no_id",
            tenant_id="t1",
            event_type="customer.subscription.updated",
            livemode=False,
            raw_payload={"object": {}},  # no 'id' in object
        )
        assert processed is True
