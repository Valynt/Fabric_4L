"""Unit tests for Layer 7 billing repository (P0-004)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from layer7_billing import repository

pytestmark = [pytest.mark.unit]


class TestRepository:
    """Billing repository operations with mocked AsyncSession."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        s = AsyncMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        return s

    async def test_upsert_plan(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock()
        result = await repository.upsert_plan(
            session, "tenant-1", "plan-pro", "Pro Plan", ["feature_a"]
        )
        assert result["plan_id"] == "plan-pro"
        assert result["tenant_id"] == "tenant-1"
        session.execute.assert_awaited_once()

    async def test_get_plan_entitlements_found(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=["feature_a", "feature_b"])
        )
        result = await repository.get_plan_entitlements(session, "tenant-1", "plan-pro")
        assert result == ["feature_a", "feature_b"]

    async def test_get_plan_entitlements_none_returns_empty(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await repository.get_plan_entitlements(session, "tenant-1", "plan-pro")
        assert result == []

    async def test_insert_usage_event_new(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(rowcount=1)
        result = await repository.insert_usage_event(session, "tenant-1", {"event_id": "evt-1"})
        assert result is True

    async def test_insert_usage_event_duplicate(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(rowcount=0)
        result = await repository.insert_usage_event(session, "tenant-1", {"event_id": "evt-1"})
        assert result is False

    async def test_increment_aggregate(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock()
        await repository.increment_aggregate(session, "tenant-1", "api_calls", 10.0)
        session.execute.assert_awaited_once()

    async def test_get_usage_aggregates(self, session: AsyncMock) -> None:
        Row = MagicMock()
        Row.metric = "api_calls"
        Row.total_quantity = 100.0
        session.execute.return_value = MagicMock(all=MagicMock(return_value=[Row]))
        result = await repository.get_usage_aggregates(session, "tenant-1")
        assert result == {"api_calls": 100.0}

    async def test_list_invoices(self, session: AsyncMock) -> None:
        inv = MagicMock()
        inv.invoice_id = "inv-1"
        inv.payload = {"amount": 100}
        inv.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[inv])))
        )
        result = await repository.list_invoices(session, "tenant-1")
        assert len(result) == 1
        assert result[0]["invoice_id"] == "inv-1"

    async def test_get_payment_state_found(self, session: AsyncMock) -> None:
        row = MagicMock()
        row.tenant_id = "tenant-1"
        row.state_key = "current"
        row.state = "paid"
        row.payload = {"method": "card"}
        session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=row)
        )
        result = await repository.get_payment_state(session, "tenant-1")
        assert result["state"] == "paid"
        assert result["payload"] == {"method": "card"}

    async def test_get_payment_state_not_found(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await repository.get_payment_state(session, "tenant-1")
        assert result["state"] == "pending"
        assert result["payload"] == {}
        assert result["tenant_id"] == "tenant-1"

    async def test_get_payment_state_custom_key(self, session: AsyncMock) -> None:
        session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await repository.get_payment_state(session, "tenant-1", state_key="archive")
        assert result["state_key"] == "archive"
