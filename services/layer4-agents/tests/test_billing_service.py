"""
Tests for BillingService and billing API routes.

Covers:
- Customer creation and Stripe sync
- Subscription lifecycle management
- Webhook handling with idempotency
- Entitlement checks
- Plan configuration
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.layer4.api.main import app
from value_fabric.layer4.models.billing import (
    BillingCustomer,
    BillingInvoice,
    BillingInvoiceItem,
    BillingSubscription,
    BillingUsageEvent,
    BillingWebhookEvent,
    SubscriptionStatus,
)

from value_fabric.layer4.services.billing_service import BillingService
from value_fabric.layer4.services.stripe_client import StripeError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def override_app_db_dependency(mock_db):
    """Override FastAPI get_db dependency to use the mock session."""
    from value_fabric.layer4.database import get_db_from_context
    from value_fabric.shared.identity.dependencies import require_authenticated
    from value_fabric.shared.identity.context import RequestContext

    async def _override_db():
        yield mock_db

    async def _override_auth():
        return RequestContext(
            tenant_id="tenant_abc123",
            user_id="user_123",
            roles=["admin"],
            permissions=["billing:read", "billing:write"],
        )

    app.dependency_overrides[get_db_from_context] = _override_db
    app.dependency_overrides[require_authenticated] = _override_auth
    yield
    app.dependency_overrides.pop(get_db_from_context, None)
    app.dependency_overrides.pop(require_authenticated, None)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_customer():
    """Sample billing customer for tests."""
    return BillingCustomer(
        id="user_123",
        tenant_id="tenant_abc123",
        stripe_customer_id="cus_test123",
        email="test@example.com",
        name="Test User",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_subscription():
    """Sample billing subscription for tests."""
    return BillingSubscription(
        id="sub_123",
        tenant_id="tenant_abc123",
        customer_id="user_123",
        stripe_subscription_id="sub_stripe123",
        plan_id="pro",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC),
        cancel_at_period_end=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# =============================================================================
# BillingService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_or_create_customer_new(mock_db):
    """Test creating a new customer."""
    # Setup mock result to return None (customer doesn't exist)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    # Mock Stripe customer creation
    mock_stripe = MagicMock()
    mock_customer = MagicMock()
    mock_customer.id = "cus_new123"
    mock_stripe.Customer.create.return_value = mock_customer

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        customer = await service.get_or_create_customer(
            customer_id="user_new",
            email="new@example.com",
            name="New User",
        )

    assert customer.id == "user_new"
    assert customer.email == "new@example.com"
    assert customer.name == "New User"
    assert customer.stripe_customer_id == "cus_new123"
    assert customer.stripe_sync_status == "synced"
    mock_db.add.assert_called()
    mock_db.flush.assert_called()

@pytest.mark.asyncio
async def test_get_or_create_customer_stripe_unavailable_marks_sync_failed(mock_db):
    """Stripe failure should persist explicit failed sync state."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_stripe.Customer.create.side_effect = StripeError("stripe unavailable")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        customer = await service.get_or_create_customer(
            customer_id="user_pending",
            email="pending@example.com",
            name="Pending User",
        )

    assert customer.stripe_customer_id is None
    assert customer.stripe_sync_status == "failed"
    assert customer.stripe_sync_error is not None


@pytest.mark.asyncio
async def test_get_or_create_customer_logs_orphan_on_db_failure_after_stripe_success(mock_db):
    """DB failure after Stripe success should log orphan compensation signal."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.flush.side_effect = [None, Exception("db flush failed")]

    mock_stripe = MagicMock()
    mock_customer = MagicMock()
    mock_customer.id = "cus_orphan_123"
    mock_stripe.Customer.create.return_value = mock_customer

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe), patch('src.services.billing_service.logger') as mock_logger:
        service = BillingService(mock_db)
        with pytest.raises(Exception):
            await service.get_or_create_customer(
                customer_id="user_orphan",
                email="orphan@example.com",
                name="Orphan User",
            )
    assert mock_logger.warning.called


@pytest.mark.asyncio
async def test_reconcile_customer_sync_retry_recovers_failed_customer(mock_db):
    """Failed sync should recover via reconciliation retry."""
    customer = BillingCustomer(
        id="user_retry",
        tenant_id="tenant_abc123",
        stripe_customer_id=None,
        stripe_sync_status="failed",
        stripe_sync_error="timeout",
        email="retry@example.com",
        name="Retry User",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [customer]
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_remote = MagicMock()
    mock_remote.id = "cus_recovered_1"
    mock_stripe.Customer.create.return_value = mock_remote
    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.reconcile_customer_sync(batch_size=10)

    assert customer.stripe_customer_id == "cus_recovered_1"
    assert customer.stripe_sync_status == "synced"
    assert customer.stripe_sync_error is None
    assert result["synced"] == 1


@pytest.mark.asyncio
async def test_get_or_create_customer_existing(mock_db, sample_customer):
    """Test retrieving an existing customer."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_customer
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    customer = await service.get_or_create_customer(
        customer_id="user_123",
        email="updated@example.com",  # Different email
        name="Updated Name",
    )

    assert customer.id == "user_123"
    assert customer.email == "updated@example.com"  # Should be updated
    assert customer.name == "Updated Name"  # Should be updated


@pytest.mark.asyncio
async def test_get_active_subscription(mock_db, sample_subscription):
    """Test fetching active subscription."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    subscription = await service.get_active_subscription("user_123")

    assert subscription is not None
    assert subscription.plan_id == "pro"
    assert subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_check_entitlement_pro_has_advanced_models(mock_db, sample_subscription):
    """Test that pro plan has advanced_models feature."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is True


@pytest.mark.asyncio
async def test_check_entitlement_free_no_advanced_models(mock_db):
    """Test that free plan does not have advanced_models feature."""
    free_subscription = BillingSubscription(
        id="free_123",
        customer_id="user_123",
        plan_id="free",
        status=SubscriptionStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = free_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is False


@pytest.mark.asyncio
async def test_handle_webhook_checkout_completed(mock_db):
    """Test handling checkout.session.completed webhook."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing subscription
    mock_db.execute.return_value = mock_result

    # Mock webhook event
    event_id = "evt_test123"
    event_type = "checkout.session.completed"
    session_data = {
        "id": "sess_123",
        "metadata": {
            "customer_id": "user_123",
            "plan_id": "pro",
        },
        "subscription": "sub_stripe123",
    }

    mock_event = {
        "id": event_id,
        "type": event_type,
        "data": {"object": session_data},
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = mock_event

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="test_sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    mock_db.add.assert_called()
    mock_db.flush.assert_called()


@pytest.mark.asyncio
async def test_handle_webhook_idempotency(mock_db):
    """Test that duplicate webhook events are ignored."""
    event_id = "evt_duplicate"

    # First call returns existing event
    existing_event = BillingWebhookEvent(id=event_id, type="test")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_event
    mock_db.execute.return_value = mock_result

    mock_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": {}},
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = mock_event

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="test_sig",
            webhook_secret="whsec_test",
        )

    assert result is True  # Returns True even though already processed


@pytest.mark.asyncio
async def test_create_checkout_session_no_customer(mock_db):
    """Test checkout creation fails if customer not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)

    with pytest.raises(ValueError, match="Customer not found"):
        await service.create_checkout_session(
            customer_id="unknown_user",
            plan_id="pro",
            success_url="http://success",
            cancel_url="http://cancel",
        )


@pytest.mark.asyncio
async def test_create_checkout_session_no_stripe_sync(mock_db, sample_customer):
    """Test checkout creation fails if customer not synced with Stripe."""
    sample_customer.stripe_customer_id = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_customer
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)

    with pytest.raises(ValueError, match="not synced with Stripe"):
        await service.create_checkout_session(
            customer_id="user_123",
            plan_id="pro",
            success_url="http://success",
            cancel_url="http://cancel",
        )


@pytest.mark.asyncio
async def test_webhook_invalid_signature(mock_db):
    """Test webhook rejects invalid signatures."""
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.side_effect = Exception("Invalid signature")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        with pytest.raises(ValueError, match="Invalid signature"):
            await service.handle_webhook(
                payload=b'{"test": "payload"}',
                signature="invalid_sig",
                webhook_secret="whsec_test",
            )


@pytest.mark.asyncio
async def test_handle_payment_failed_updates_status(mock_db):
    """Test payment failure marks subscription as past_due."""
    subscription = BillingSubscription(
        id="sub_123",
        customer_id="user_123",
        stripe_subscription_id="sub_stripe123",
        plan_id="pro",
        status=SubscriptionStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    await service._handle_payment_failed({"subscription": "sub_stripe123"})

    assert subscription.status == SubscriptionStatus.PAST_DUE


# =============================================================================
# API Route Tests
# =============================================================================

def test_get_subscription_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/subscription endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/subscription?customer_id=user_123")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "pro"
    assert data["status"] == "active"


def test_get_subscription_no_customer(client, mock_db):
    """Test GET /billing/subscription returns free tier default."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/subscription?customer_id=new_user")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "free"
    assert data["status"] == "active"


def test_get_entitlements_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/entitlements endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/entitlements?customer_id=user_123")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "pro"
    assert "features" in data
    assert data["features"]["advanced_models"]["enabled"] is True


def test_check_feature_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/check-feature endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/check-feature?customer_id=user_123&feature_id=advanced_models")

    assert response.status_code == 200
    data = response.json()
    assert data["feature_id"] == "advanced_models"
    assert data["has_access"] is True


# =============================================================================
# Plan Configuration Tests
# =============================================================================

def test_plan_configuration():
    """Test that plan configuration is correctly defined."""
    from value_fabric.layer4.config.plans import PLANS, FEATURES, get_plan, check_entitlement

    # Test plan existence
    assert get_plan("free") is not None
    assert get_plan("pro") is not None
    assert get_plan("enterprise") is not None
    assert get_plan("nonexistent") is None

    # Test feature definitions
    assert "basic_extraction" in FEATURES
    assert "advanced_models" in FEATURES

    # Test entitlement checks
    assert check_entitlement("free", "basic_extraction") is True
    assert check_entitlement("free", "advanced_models") is False
    assert check_entitlement("pro", "advanced_models") is True
    assert check_entitlement("enterprise", "any_feature") is True  # Enterprise has "*"


def test_plan_features_list():
    """Test getting list of features for a plan."""
    from value_fabric.layer4.config.plans import get_plan_features

    free_features = get_plan_features("free")
    assert len(free_features) == 3  # basic_extraction, knowledge_graph, formula_builder

    pro_features = get_plan_features("pro")
    assert len(pro_features) == 6  # All free features + advanced_models, priority_support, team_collaboration

    enterprise_features = get_plan_features("enterprise")
    assert len(enterprise_features) == 9  # All features


def test_invalid_plan_returns_no_features():
    """Test that invalid plan returns empty feature list."""
    from value_fabric.layer4.config.plans import get_plan_features, check_entitlement, get_plan

    assert get_plan_features("invalid") == []
    assert check_entitlement("invalid", "basic_extraction") is False
    assert get_plan("invalid") is None


def test_subscription_is_active_property():
    """Test subscription is_active property with various statuses."""
    from value_fabric.layer4.models.billing import BillingSubscription, SubscriptionStatus

    # Active statuses
    for status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
        sub = BillingSubscription(id="1", status=status, plan_id="pro")
        assert sub.is_active is True

    # Inactive statuses
    for status in [SubscriptionStatus.CANCELED, SubscriptionStatus.UNPAID, SubscriptionStatus.PAST_DUE]:
        sub = BillingSubscription(id="1", status=status, plan_id="pro")
        assert sub.is_active is False


def test_subscription_is_canceled_property():
    """Test subscription is_canceled property."""
    from value_fabric.layer4.models.billing import BillingSubscription, SubscriptionStatus

    # Explicitly canceled
    sub = BillingSubscription(id="1", status=SubscriptionStatus.CANCELED, plan_id="pro")
    assert sub.is_canceled is True

    # Will cancel at period end
    sub = BillingSubscription(
        id="1",
        status=SubscriptionStatus.ACTIVE,
        plan_id="pro",
        cancel_at_period_end=True
    )
    assert sub.is_canceled is True

    # Active, not canceling
    sub = BillingSubscription(
        id="1",
        status=SubscriptionStatus.ACTIVE,
        plan_id="pro",
        cancel_at_period_end=False
    )
    assert sub.is_canceled is False


# =============================================================================
# Subscription Lifecycle Tests
# =============================================================================

@pytest.mark.asyncio
async def test_cancel_subscription_at_period_end(mock_db, sample_subscription):
    """Test canceling a subscription at period end."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_stripe_sub = MagicMock()
    mock_stripe_sub.current_period_end = 1893456000  # ~2030-01-01
    mock_stripe.Subscription.modify.return_value = mock_stripe_sub

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.cancel_subscription(
            customer_id="user_123",
            tenant_id="tenant_abc123",
            cancel_immediately=False,
        )

    assert result["canceled"] is True
    assert result["cancel_at_period_end"] is True
    assert sample_subscription.status == SubscriptionStatus.ACTIVE
    assert sample_subscription.cancel_at_period_end is True
    mock_stripe.Subscription.modify.assert_called_once_with(
        "sub_stripe123",
        cancel_at_period_end=True,
    )


@pytest.mark.asyncio
async def test_cancel_subscription_immediately_downgrades_to_free(mock_db, sample_subscription):
    """Test immediate cancel downgrades to free tier."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_stripe_sub = MagicMock()
    mock_stripe_sub.current_period_end = None
    mock_stripe.Subscription.modify.return_value = mock_stripe_sub

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.cancel_subscription(
            customer_id="user_123",
            tenant_id="tenant_abc123",
            cancel_immediately=True,
        )

    assert result["canceled"] is True
    assert result["cancel_at_period_end"] is False
    assert sample_subscription.status == SubscriptionStatus.CANCELED
    mock_db.add.assert_called()  # Free subscription added


@pytest.mark.asyncio
async def test_cancel_subscription_no_active_subscription(mock_db):
    """Test cancel fails when no active subscription exists."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    with pytest.raises(ValueError, match="No active subscription found"):
        await service.cancel_subscription(customer_id="user_123")


@pytest.mark.asyncio
async def test_update_subscription_plan(mock_db, sample_subscription):
    """Test updating a subscription plan."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe), \
         patch('value_fabric.layer4.services.billing_service.get_price_id', return_value="price_enterprise"):
        service = BillingService(mock_db)
        result = await service.update_subscription_plan(
            customer_id="user_123",
            new_plan_id="enterprise",
        )

    assert result["updated"] is True
    assert result["previous_plan_id"] == "pro"
    assert sample_subscription.plan_id == "enterprise"
    mock_stripe.Subscription.modify.assert_called_once_with(
        "sub_stripe123",
        items=[{"price": "price_enterprise", "quantity": 1}],
        proration_behavior="create_prorations",
    )


@pytest.mark.asyncio
async def test_update_subscription_plan_same_plan(mock_db, sample_subscription):
    """Test plan update fails when already on requested plan."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    with pytest.raises(ValueError, match="already on the requested plan"):
        await service.update_subscription_plan(
            customer_id="user_123",
            new_plan_id="pro",
        )


@pytest.mark.asyncio
async def test_reactivate_subscription(mock_db):
    """Test reactivating a subscription scheduled to cancel."""
    scheduled_sub = BillingSubscription(
        id="sub_123",
        customer_id="user_123",
        stripe_subscription_id="sub_stripe123",
        plan_id="pro",
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scheduled_sub
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.reactivate_subscription(customer_id="user_123")

    assert result["reactivated"] is True
    assert scheduled_sub.cancel_at_period_end is False
    mock_stripe.Subscription.modify.assert_called_once_with(
        "sub_stripe123",
        cancel_at_period_end=False,
    )


@pytest.mark.asyncio
async def test_reactivate_subscription_not_scheduled(mock_db):
    """Test reactivation fails when subscription is not scheduled to cancel."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    with pytest.raises(ValueError, match="No scheduled-to-cancel subscription"):
        await service.reactivate_subscription(customer_id="user_123")


# =============================================================================
# Webhook Lifecycle Tests
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_subscription_created(mock_db):
    """Test customer.subscription.created webhook creates subscription."""
    customer = BillingCustomer(
        id="user_123",
        tenant_id="tenant_abc123",
        stripe_customer_id="cus_test123",
        email="test@example.com",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [None, customer, None]
    mock_db.execute.return_value = mock_result

    event = {
        "id": "evt_sub_created",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_new123",
                "customer": "cus_test123",
                "status": "active",
                "items": {
                    "data": [{"price": {"id": "price_pro"}}]
                },
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_webhook_subscription_updated_plan_change(mock_db, sample_subscription):
    """Test subscription.updated webhook updates plan_id."""
    # First query: idempotency check (no existing event)
    # Second query: find subscription by stripe_subscription_id
    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = None
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.side_effect = [idempotency_result, subscription_result]

    event = {
        "id": "evt_sub_updated",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe123",
                "status": "active",
                "items": {
                    "data": [{"price": {"id": "price_enterprise"}}]
                },
                "current_period_start": 1704067200,
                "current_period_end": 1893456000,
                "cancel_at_period_end": False,
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe), \
         patch('value_fabric.layer4.config.plans.PLANS', {
             "enterprise": MagicMock(stripe_price_id="price_enterprise"),
             "pro": MagicMock(stripe_price_id="price_pro"),
         }):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    assert sample_subscription.plan_id == "enterprise"


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_downgrades_to_free(mock_db, sample_subscription):
    """Test subscription.deleted webhook downgrades to free tier."""
    # First query: idempotency check (no existing event)
    # Second query: find subscription by stripe_subscription_id
    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = None
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.side_effect = [idempotency_result, subscription_result]

    event = {
        "id": "evt_sub_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe123",
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    assert sample_subscription.status == SubscriptionStatus.CANCELED
    mock_db.add.assert_called()  # Free subscription added


@pytest.mark.asyncio
async def test_webhook_replay_idempotency_explicit(mock_db):
    """Test that replayed webhook events are idempotent."""
    event_id = "evt_replay_123"

    # First: simulate already processed event
    existing_event = BillingWebhookEvent(id=event_id, type="customer.subscription.updated")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_event
    mock_db.execute.return_value = mock_result

    event = {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_stripe123", "status": "active"}},
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    # Should not call add for subscription update since already processed
    mock_db.add.assert_not_called()


# =============================================================================
# Secure Error Envelope Tests
# =============================================================================

@pytest.mark.asyncio
async def test_stripe_error_does_not_leak_to_client(mock_db, sample_subscription):
    """Test that Stripe errors are masked with generic messages."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_stripe.Subscription.modify.side_effect = StripeError("raw stripe error: card declined")

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        with pytest.raises(ValueError) as exc_info:
            await service.cancel_subscription(customer_id="user_123")

    assert "raw stripe error" not in str(exc_info.value).lower()
    assert "billing provider error" in str(exc_info.value).lower()


# =============================================================================
# API Route Tests
# =============================================================================

def test_cancel_subscription_endpoint(client, mock_db, sample_subscription):
    """Test POST /billing/subscription/cancel endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()
    mock_stripe_sub = MagicMock()
    mock_stripe_sub.current_period_end = 1893456000
    mock_stripe.Subscription.modify.return_value = mock_stripe_sub

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        response = client.post(
            "/v1/billing/subscription/cancel?customer_id=user_123",
            json={"cancel_immediately": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["canceled"] is True
    assert data["cancel_at_period_end"] is True


def test_update_plan_endpoint(client, mock_db, sample_subscription):
    """Test POST /billing/subscription/update-plan endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe), \
         patch('value_fabric.layer4.services.billing_service.get_price_id', return_value="price_enterprise"):
        response = client.post(
            "/v1/billing/subscription/update-plan?customer_id=user_123",
            json={"plan_id": "enterprise"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["updated"] is True
    assert data["previous_plan_id"] == "pro"


def test_reactivate_subscription_endpoint(client, mock_db):
    """Test POST /billing/subscription/reactivate endpoint."""
    scheduled_sub = BillingSubscription(
        id="sub_123",
        customer_id="user_123",
        stripe_subscription_id="sub_stripe123",
        plan_id="pro",
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scheduled_sub
    mock_db.execute.return_value = mock_result

    mock_stripe = MagicMock()

    with patch('value_fabric.layer4.services.billing_service._get_stripe', return_value=mock_stripe):
        response = client.post(
            "/v1/billing/subscription/reactivate?customer_id=user_123",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reactivated"] is True


@pytest.mark.asyncio
async def test_ingest_usage_event_duplicate_returns_existing(mock_db):
    mock_db.flush.side_effect = [IntegrityError("dup", None, None), None]
    existing = BillingUsageEvent(
        id="usage_tenant_abc123_evt_1",
        tenant_id="tenant_abc123",
        customer_id="user_123",
        event_id="evt_1",
        event_name="api_call",
        metric_name="tokens",
        quantity=5,
        timestamp=datetime.now(UTC),
    )
    q = MagicMock()
    q.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = q
    service = BillingService(mock_db)
    result = await service.ingest_usage_event(
        tenant_id="tenant_abc123",
        customer_id="user_123",
        event_id="evt_1",
        event_name="api_call",
        metric_name="tokens",
        quantity=5,
        timestamp=datetime.now(UTC),
    )
    assert result.id == existing.id


@pytest.mark.asyncio
async def test_reconcile_invoice_usage_mismatch(mock_db):
    invoice = BillingInvoice(
        id="inv_1",
        tenant_id="tenant_abc123",
        customer_id="user_123",
        invoice_number="INV-1",
        status="open",
        currency="USD",
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2026, 1, 31, tzinfo=UTC),
    )
    usage = BillingUsageEvent(
        id="usage_1",
        tenant_id="tenant_abc123",
        customer_id="user_123",
        event_id="evt_2",
        event_name="eval",
        metric_name="tokens",
        quantity=100,
        timestamp=datetime(2026, 1, 10, tzinfo=UTC),
    )
    item = BillingInvoiceItem(
        id="item_1",
        tenant_id="tenant_abc123",
        invoice_id="inv_1",
        type="metered",
        description="tokens",
        quantity=1,
        unit_amount=1,
        amount=1,
        usage_quantity=90,
        usage_metric="tokens",
    )
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = invoice
    r2 = MagicMock(); r2.scalars.return_value.all.return_value = [usage]
    r3 = MagicMock(); r3.scalars.return_value.all.return_value = [item]
    mock_db.execute.side_effect = [r1, r2, r3]
    service = BillingService(mock_db)
    reconciled = await service.reconcile_invoice_usage("tenant_abc123", "inv_1")
    assert reconciled["mismatch_count"] == 1
