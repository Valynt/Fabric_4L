from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from layer4_agents.models.billing import BillingPlanVersion, BillingSubscription, SubscriptionStatus
from layer4_agents.services.billing_service import BillingService


@pytest.fixture
def mock_db():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_entitlement_uses_pinned_plan_version_for_historical_reproducibility(mock_db):
    sub = BillingSubscription(
        id='sub_1', customer_id='cust_1', tenant_id='t1', plan_id='pro', status=SubscriptionStatus.ACTIVE, plan_version_id='pv_1'
    )
    pinned = BillingPlanVersion(
        id='pv_1', tenant_id=None, plan_id='pro', version=1,
        effective_from=datetime(2025, 1, 1, tzinfo=UTC),
        features={'ids': ['basic_extraction']},
        usage_limits={},
    )

    res1 = MagicMock(); res1.scalar_one_or_none.return_value = sub
    res2 = MagicMock(); res2.scalars.return_value.first.return_value = pinned
    mock_db.execute.side_effect = [res1, res2]

    service = BillingService(mock_db)
    has_advanced = await service.check_entitlement('cust_1', 'advanced_models')
    assert has_advanced is False
