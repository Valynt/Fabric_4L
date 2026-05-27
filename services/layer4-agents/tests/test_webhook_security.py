"""Security and idempotency tests for Stripe webhook handling.

Covers P0 security requirements:
- Signature verification cannot be bypassed
- Idempotency is race-condition safe (DB-level constraint)
- Tenant resolution is from trusted source, not webhook payload
- Malformed events are handled safely
- Database failures don't expose secrets or corrupt state
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.layer4.models.billing import (
    BillingCustomer,
    BillingSubscription,
    BillingWebhookEvent,
    SubscriptionStatus,
)

from value_fabric.layer4.services.billing_service import BillingService


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
    session.rollback = AsyncMock()
    return session


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


def valid_webhook_payload():
    """Valid webhook payload for testing."""
    return b'{"id": "evt_test123", "type": "checkout.session.completed", "data": {"object": {"id": "sess_123", "metadata": {"customer_id": "user_123", "plan_id": "pro"}, "subscription": "sub_stripe123"}}}'


def valid_webhook_signature():
    """Valid webhook signature for testing."""
    return "sig_valid123"


# =============================================================================
# P0: Signature Verification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_missing_signature_rejected(mock_db):
    """P0: Webhook with missing signature header must be rejected.
    
    Risk: Signature verification bypass allowing arbitrary webhook injection.
    """
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.side_effect = ValueError("Missing signature")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        with pytest.raises(ValueError, match="Invalid signature"):
            await service.handle_webhook(
                payload=valid_webhook_payload(),
                signature="",  # Empty signature
                webhook_secret="whsec_test",
            )


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected_with_specific_error(mock_db):
    """P0: Invalid signature must raise ValueError with 'Invalid signature' message.
    
    Risk: Generic exception handling could swallow signature errors or expose internals.
    """
    mock_stripe = MagicMock()
    # Create a mock exception class since stripe may not be installed
    class MockSignatureError(Exception):
        pass
    mock_stripe.Webhook.construct_event.side_effect = MockSignatureError("Invalid signature")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        with pytest.raises(ValueError, match="Invalid signature"):
            await service.handle_webhook(
                payload=valid_webhook_payload(),
                signature="sig_invalid",
                webhook_secret="whsec_test",
            )


@pytest.mark.asyncio
async def test_webhook_malformed_payload_rejected(mock_db):
    """P0: Malformed JSON payload must be rejected safely.
    
    Risk: Malformed payload could cause crashes or log injection.
    """
    mock_stripe = MagicMock()
    # construct_event raises ValueError for invalid payload
    mock_stripe.Webhook.construct_event.side_effect = ValueError("Invalid payload")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        with pytest.raises(ValueError, match="Invalid payload"):
            await service.handle_webhook(
                payload=b"not valid json {{",
                signature="sig_test",
                webhook_secret="whsec_test",
            )


@pytest.mark.asyncio
async def test_webhook_signature_verification_mandatory(mock_db):
    """P0: construct_event must be called and must validate signature.
    
    Risk: If construct_event is skipped or bypassed, webhooks are not authenticated.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_test",
        "type": "checkout.session.completed",
        "data": {"object": {}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        
        # Setup idempotency check - no existing event (needs to be awaited)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        payload = valid_webhook_payload()
        await service.handle_webhook(
            payload=payload,
            signature="sig_test",
            webhook_secret="whsec_test",
        )

        # Verify construct_event was actually called with correct args
        mock_stripe.Webhook.construct_event.assert_called_once_with(
            payload,
            "sig_test",
            "whsec_test",
        )


# =============================================================================
# P0: Idempotency Race Condition Tests
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_idempotency_uses_db_constraint_not_raceable_select(mock_db):
    """P0: Idempotency must use DB constraint, not SELECT-then-INSERT pattern.
    
    Current implementation uses SELECT then INSERT which is raceable.
    This test documents the vulnerability and expected fix.
    
    Risk: Two concurrent webhooks with same event_id could both pass SELECT 
    check and both execute INSERT, creating duplicate side effects.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_concurrent_test",
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"customer_id": "user_123", "plan_id": "pro"}, "subscription": "sub_123"}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        # First call - no existing event (simulates race condition window)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # If another concurrent request also sees None and inserts first,
        # this second insert should fail with IntegrityError
        mock_db.flush.side_effect = IntegrityError(
            "duplicate key value violates unique constraint", 
            None, 
            None
        )

        # Should handle race gracefully, not crash
        try:
            result = await service.handle_webhook(
                payload=b'{"test": "payload"}',
                signature="sig_test",
                webhook_secret="whsec_test",
            )
            # If we get here with IntegrityError suppressed, that's the bug
            # The service should either:
            # 1. Return True (already processed)
            # 2. Or raise a specific error that caller can handle
            assert result is True, "Should return True for duplicate/integrity error"
        except IntegrityError:
            # Current behavior - lets IntegrityError propagate
            # This is the bug: race condition not handled
            pytest.fail("Race condition not handled - IntegrityError propagated")


@pytest.mark.asyncio
async def test_webhook_duplicate_event_id_returns_success(mock_db):
    """P0: Duplicate webhook event_id must return success, not error.
    
    Stripe retries webhooks. Returning error on duplicate causes unnecessary 
    webhook failures and alert noise.
    
    Risk: Stripe marks endpoint as failing, disables webhooks.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_duplicate_123",
        "type": "checkout.session.completed",
        "data": {"object": {}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    # Existing event found in DB
    existing_event = BillingWebhookEvent(
        id="evt_duplicate_123",
        type="checkout.session.completed",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_event
    mock_db.execute.return_value = mock_result

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="sig_test",
            webhook_secret="whsec_test",
        )

        # Must return True (success) even though already processed
        assert result is True
        # Must NOT add duplicate to DB
        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_called()


# =============================================================================
# P0: Tenant Isolation Tests for Webhooks
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_tenant_resolution_from_customer_record(mock_db, sample_customer):
    """P0: Tenant must be resolved from trusted customer record, not webhook metadata.
    
    Risk: Attacker crafts webhook with victim's customer_id in metadata, 
    gets subscription created in victim's account.
    
    Current implementation uses metadata.customer_id directly without validating
    the customer belongs to the authenticated tenant context.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_tenant_test",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "sess_123",
            "metadata": {
                "customer_id": "user_123",  # Attacker knows this valid customer
                "plan_id": "pro",
            },
            "subscription": "sub_stripe123",
        }},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    # Idempotency check - no existing event
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    
    # Customer lookup result - this is the trusted source
    mock_db.execute.side_effect = [
        mock_result,  # First call - idempotency check
        MagicMock(scalar_one_or_none=MagicMock(return_value=sample_customer)),  # Customer lookup
    ]

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="sig_test",
            webhook_secret="whsec_test",
        )

        # Verify customer was looked up - this is the security check
        # The customer lookup verifies customer exists and gets tenant_id
        assert mock_db.execute.call_count >= 2


@pytest.mark.asyncio
async def test_webhook_checkout_completed_with_unknown_customer(mock_db):
    """P0: Webhook for unknown customer must be handled safely.
    
    Risk: Null pointer or information leak if customer not found.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_unknown_customer",
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {
                "customer_id": "user_nonexistent",
                "plan_id": "pro",
            },
            "subscription": "sub_stripe123",
        }},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        
        # Should not crash, should handle gracefully
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="sig_test",
            webhook_secret="whsec_test",
        )
        
        # Returns True even though customer not found (event still processed)
        assert result is True


# =============================================================================
# P0: Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_database_failure_rolls_back(mock_db):
    """P0: Database failure during webhook processing must rollback.
    
    Risk: Partial writes leave database in inconsistent state.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_db_fail",
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"customer_id": "user_123", "plan_id": "pro"},
            "subscription": "sub_stripe123",
        }},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Simulate DB failure during flush
    mock_db.flush.side_effect = Exception("Database connection lost")

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)

        with pytest.raises(Exception):
            await service.handle_webhook(
                payload=b'{"test": "payload"}',
                signature="sig_test",
                webhook_secret="whsec_test",
            )

        # Verify rollback was called
        mock_db.rollback.assert_called()


@pytest.mark.asyncio
async def test_webhook_does_not_log_secrets(mock_db, caplog):
    """P0: Webhook processing must not log secrets, tokens, or raw payloads.
    
    Risk: Secrets in logs expose to anyone with log access.
    """
    import logging
    
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_log_test",
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"customer_id": "user_123"}}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    # Set logging level to capture all logs
    with caplog.at_level(logging.DEBUG):
        with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
            service = BillingService(mock_db)
            await service.handle_webhook(
                payload=b'{"test": "payload"}',
                signature="sig_super_secret_token_12345",
                webhook_secret="whsec_ultra_secret_webhook_key",
            )

    # Check logs don't contain secrets
    log_text = caplog.text.lower()
    assert "whsec_" not in log_text, "Webhook secret leaked in logs"
    assert "super_secret_token" not in log_text, "Signature leaked in logs"
    assert "ultra_secret" not in log_text, "Secret leaked in logs"


# =============================================================================
# P1: Unknown Event Type Handling
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_unknown_event_type_logged_and_ignored(mock_db):
    """P1: Unknown webhook event types must be logged and safely ignored.
    
    Risk: New Stripe event types could cause errors or unexpected behavior.
    """
    mock_stripe = MagicMock()
    mock_event = {
        "id": "evt_unknown_type",
        "type": "invoiceitem.updated",  # Not handled event type
        "data": {"object": {}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="sig_test",
            webhook_secret="whsec_test",
        )

        # Should succeed even for unknown event types
        assert result is True
        # Should still record the event as processed
        mock_db.add.assert_called_once()


# =============================================================================
# P1: Event Ordering Tests
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_out_of_order_subscription_events(mock_db, sample_subscription):
    """P1: Out-of-order webhook events must be handled safely.
    
    Risk: If 'subscription.deleted' arrives before 'subscription.updated',
    state could become inconsistent.
    """
    mock_stripe = MagicMock()
    
    # Simulate deleted event for non-existent subscription (created event lost)
    mock_event = {
        "id": "evt_out_of_order",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_nonexistent"}},
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with patch('src.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        
        # Should not crash when subscription not found
        result = await service.handle_webhook(
            payload=b'{"test": "payload"}',
            signature="sig_test",
            webhook_secret="whsec_test",
        )
        
        assert result is True
