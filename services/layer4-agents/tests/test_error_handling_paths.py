from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import SQLAlchemyError

from layer4_agents.services.usage_service import UsageService
from layer4_agents.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_usage_ingest_event_rolls_back_and_surfaces_db_error():
    db = AsyncMock()
    db.flush.side_effect = SQLAlchemyError("db down")
    service = UsageService(db, tenant_id="tenant-1")

    with pytest.raises(SQLAlchemyError):
        await service.ingest_event("evt-1", "cust-1", "api_call", "tokens", 1)

    db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_billing_webhook_malformed_payload_translates_to_value_error():
    db = AsyncMock()
    service = BillingService(db)

    with patch("src.services.billing_service._get_stripe") as get_stripe:
        stripe = get_stripe.return_value
        stripe.Webhook.construct_event.side_effect = KeyError("missing signature")

        with pytest.raises(ValueError, match="Invalid signature|Malformed webhook payload"):
            await service.handle_webhook(b"{}", "sig", "secret")


@pytest.mark.asyncio
async def test_webhook_db_failure_not_swallowed():
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.flush.side_effect = SQLAlchemyError("write failed")
    service = BillingService(db)

    with patch("src.services.billing_service._get_stripe") as get_stripe:
        stripe = get_stripe.return_value
        stripe.Webhook.construct_event.return_value = {
            "id": "evt_1",
            "type": "invoice.payment_succeeded",
            "data": {"object": {}},
        }

        with pytest.raises(SQLAlchemyError):
            await service.handle_webhook(b"{}", "sig", "secret")

    db.rollback.assert_awaited()
