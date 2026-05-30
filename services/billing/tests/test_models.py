"""Tests for billing service ORM models."""

from __future__ import annotations

import pytest_asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from billing.models import Base, BillingCustomer, BillingWebhookEvent, PlanId, SubscriptionStatus


class TestModels:
    def test_subscription_status_values(self):
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.TRIALING.value == "trialing"
        assert SubscriptionStatus.CANCELED.value == "canceled"

    def test_plan_id_values(self):
        assert PlanId.FREE.value == "free"
        assert PlanId.ENTERPRISE.value == "enterprise"

    @pytest.mark.asyncio
    async def test_customer_created_at_auto_set(self, db_session):
        customer = BillingCustomer(
            id="u_test",
            tenant_id="t_test",
            email_hash="a" * 64,
            stripe_sync_status="pending",
        )
        db_session.add(customer)
        await db_session.flush()
        assert customer.created_at is not None

    @pytest.mark.asyncio
    async def test_webhook_event_model(self, db_session):
        event = BillingWebhookEvent(
            id="evt_model_test",
            tenant_id="t1",
            event_type="invoice.paid",
            livemode=False,
            raw_payload={"amount": 100},
        )
        db_session.add(event)
        await db_session.flush()
        assert event.id == "evt_model_test"
        assert event.processed_at is not None
