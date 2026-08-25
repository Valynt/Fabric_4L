"""Unit tests for billing_helpers serialization and utility functions."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from layer4_agents.api.routes.billing_helpers import (
    dt_iso,
    get_client_ip,
    is_stripe_webhook_ip,
    serialize_customer,
    serialize_invoice_item,
    serialize_subscription,
)


def test_dt_iso_and_ip_checks():
    assert dt_iso(None) is None
    dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
    assert dt_iso(dt) == "2025-01-15T12:00:00+00:00"

    assert is_stripe_webhook_ip("3.18.12.63") is True
    assert is_stripe_webhook_ip("127.0.0.1") is True
    assert is_stripe_webhook_ip("192.168.1.1") is False

    # Test client IP resolution from Request mock
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
    assert get_client_ip(req) == "203.0.113.195"

    req2 = MagicMock()
    req2.headers = {"X-Real-IP": "198.51.100.1"}
    assert get_client_ip(req2) == "198.51.100.1"


def test_serialize_subscription_default_and_populated():
    assert serialize_subscription(None) == {
        "id": None,
        "plan_id": "free",
        "status": "active",
        "current_period_start": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
    }

    sub = MagicMock()
    sub.id = "sub_123"
    sub.plan_id = "enterprise"
    sub.status = "active"
    sub.current_period_start = datetime(2025, 1, 1, tzinfo=UTC)
    sub.current_period_end = datetime(2025, 2, 1, tzinfo=UTC)
    sub.cancel_at_period_end = True

    serialized = serialize_subscription(sub)
    assert serialized["id"] == "sub_123"
    assert serialized["plan_id"] == "enterprise"
    assert serialized["cancel_at_period_end"] is True
    assert "2025-01-01" in serialized["current_period_start"]


def test_serialize_invoice_item_and_customer():
    item = MagicMock()
    item.id = "item_1"
    item.type = "metered"
    item.description = "API Calls"
    item.quantity = 100
    item.unit_amount = 5
    item.amount = 500
    item.amount_dollars = 5.0
    item.period_start = None
    item.period_end = None
    item.usage_quantity = 100
    item.usage_metric = "api_calls"
    item.tax_amount = 0
    item.discount_amount = 0

    s_item = serialize_invoice_item(item)
    assert s_item["id"] == "item_1"
    assert s_item["amount_dollars"] == 5.0

    cust = MagicMock()
    cust.id = "cust_1"
    cust.tenant_id = "tenant_a"
    cust.email = "test@example.com"
    cust.name = "Test User"
    cust.stripe_customer_id = "cus_stripe"

    s_cust = serialize_customer(cust)
    assert s_cust["id"] == "cust_1"
    assert s_cust["email"] == "test@example.com"
