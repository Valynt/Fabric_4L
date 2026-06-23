"""Tests for billing service Pydantic schemas."""

from __future__ import annotations

from billing.models import PlanId, SubscriptionStatus
from billing.schemas import (
    CustomerCreateRequest,
    CustomerRead,
    ErrorResponse,
    SubscriptionCreateRequest,
    SubscriptionRead,
    WebhookPayload,
)


class TestCustomerSchemas:
    def test_create_request_required_fields(self):
        req = CustomerCreateRequest(user_id="u1", tenant_id="t1", email="u@e.com")
        assert req.user_id == "u1"
        assert req.name is None

    def test_create_request_with_name(self):
        req = CustomerCreateRequest(user_id="u1", tenant_id="t1", email="u@e.com", name="Alice")
        assert req.name == "Alice"


class TestSubscriptionSchemas:
    def test_create_request(self):
        req = SubscriptionCreateRequest(
            user_id="u1",
            tenant_id="t1",
            plan_id=PlanId.PRO,
            stripe_price_id="price_abc",
        )
        assert req.plan_id == PlanId.PRO

    def test_plan_id_enum_values(self):
        assert PlanId.FREE.value == "free"
        assert PlanId.PRO.value == "pro"
        assert PlanId.ENTERPRISE.value == "enterprise"

    def test_subscription_status_enum_values(self):
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.CANCELED.value == "canceled"


class TestWebhookPayload:
    def test_valid_payload(self):
        payload = WebhookPayload(
            id="evt_001",
            type="customer.subscription.updated",
            livemode=False,
            data={"object": {}},
            created=1700000000,
        )
        assert payload.id == "evt_001"


class TestErrorResponse:
    def test_error_only(self):
        err = ErrorResponse(error="internal_server_error")
        assert err.error == "internal_server_error"
        assert err.detail is None

    def test_error_with_detail(self):
        err = ErrorResponse(error="not_found", detail="Subscription not found")
        assert err.detail == "Subscription not found"
