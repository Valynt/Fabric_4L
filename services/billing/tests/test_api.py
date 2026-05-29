"""Tests for the billing service FastAPI HTTP layer."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from billing.api.main import app, _get_billing_service
from billing.database import get_session
from billing.models import SubscriptionStatus
from billing.service import BillingService


# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------


def _make_customer(user_id: str = "u1", tenant_id: str = "t1") -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        tenant_id=tenant_id,
        stripe_customer_id=None,
        stripe_sync_status="pending",
        stripe_sync_error=None,
        email_hash="abc" * 20 + "ab",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_subscription(sub_id: str = "sub-1", user_id: str = "u1", tenant_id: str = "t1") -> SimpleNamespace:
    return SimpleNamespace(
        id=sub_id,
        user_id=user_id,
        tenant_id=tenant_id,
        plan_id="pro",
        status=SubscriptionStatus.ACTIVE.value,
        stripe_subscription_id=None,
        stripe_price_id="price_pro",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_test_client(svc: BillingService) -> TestClient:
    mock_session = MagicMock()

    async def _fake_session():
        yield mock_session

    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[_get_billing_service] = lambda: svc
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self):
        with patch("billing.api.main.init_db", new=AsyncMock()), patch("billing.api.main.close_db", new=AsyncMock()):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------


class TestCreateCustomer:
    def test_missing_tenant_header_returns_422(self):
        svc = MagicMock(spec=BillingService)
        client = _make_test_client(svc)
        resp = client.post("/v1/customers", json={"user_id": "u1", "tenant_id": "t1", "email": "u@e.com"})
        assert resp.status_code == 422

    def test_creates_customer_successfully(self):
        svc = MagicMock(spec=BillingService)
        customer = _make_customer()
        svc.get_or_create_customer = AsyncMock(return_value=customer)

        client = _make_test_client(svc)
        resp = client.post(
            "/v1/customers",
            json={"user_id": "u1", "tenant_id": "t1", "email": "u@e.com"},
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == "u1"
        assert data["stripe_sync_status"] == "pending"


# ---------------------------------------------------------------------------
# Subscription endpoints
# ---------------------------------------------------------------------------


class TestSubscriptionEndpoints:
    def test_create_subscription(self):
        svc = MagicMock(spec=BillingService)
        sub = _make_subscription()
        svc.create_subscription = AsyncMock(return_value=sub)

        client = _make_test_client(svc)
        resp = client.post(
            "/v1/subscriptions",
            json={"user_id": "u1", "tenant_id": "t1", "plan_id": "pro", "stripe_price_id": "price_pro"},
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["plan_id"] == "pro"

    def test_get_active_subscription_returns_none(self):
        svc = MagicMock(spec=BillingService)
        svc.get_active_subscription = AsyncMock(return_value=None)

        client = _make_test_client(svc)
        resp = client.get(
            "/v1/subscriptions/active?user_id=u_nobody",
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 200
        assert resp.json() is None

    def test_get_active_subscription_returns_sub(self):
        svc = MagicMock(spec=BillingService)
        sub = _make_subscription()
        svc.get_active_subscription = AsyncMock(return_value=sub)

        client = _make_test_client(svc)
        resp = client.get(
            "/v1/subscriptions/active?user_id=u1",
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "sub-1"

    def test_cancel_subscription_not_found(self):
        svc = MagicMock(spec=BillingService)
        svc.cancel_subscription = AsyncMock(side_effect=ValueError("Subscription 'x' not found for tenant 't1'"))

        client = _make_test_client(svc)
        resp = client.delete("/v1/subscriptions/x", headers={"X-Tenant-Id": "t1"})
        assert resp.status_code == 404

    def test_cancel_subscription_success(self):
        svc = MagicMock(spec=BillingService)
        sub = _make_subscription()
        sub.cancel_at_period_end = True
        svc.cancel_subscription = AsyncMock(return_value=sub)

        client = _make_test_client(svc)
        resp = client.delete("/v1/subscriptions/sub-1", headers={"X-Tenant-Id": "t1"})
        assert resp.status_code == 200
        assert resp.json()["cancel_at_period_end"] is True


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    def test_processes_new_event(self):
        svc = MagicMock(spec=BillingService)
        svc.process_webhook = AsyncMock(return_value=True)

        client = _make_test_client(svc)
        resp = client.post(
            "/v1/webhooks/stripe",
            json={
                "id": "evt_001",
                "type": "customer.subscription.updated",
                "livemode": False,
                "data": {"object": {}},
                "created": 1700000000,
            },
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    def test_duplicate_event(self):
        svc = MagicMock(spec=BillingService)
        svc.process_webhook = AsyncMock(return_value=False)

        client = _make_test_client(svc)
        resp = client.post(
            "/v1/webhooks/stripe",
            json={
                "id": "evt_dup",
                "type": "invoice.paid",
                "livemode": False,
                "data": {},
                "created": 1700000000,
            },
            headers={"X-Tenant-Id": "t1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"
