from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.harness.gate_timeout_scheduler import GateTimeoutScheduler


@pytest.mark.asyncio
async def test_gate_timeout_scheduler_marks_system_db_bypass(monkeypatch) -> None:
    mock_row = MagicMock()
    mock_row.status = "pending"
    mock_row.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_row.created_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_row]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    clear_context = AsyncMock()
    monkeypatch.setattr(
        "layer4_agents.harness.gate_timeout_scheduler._clear_local_tenant_context",
        clear_context,
    )

    scheduler = GateTimeoutScheduler(mock_factory, timeout_seconds=600)
    monkeypatch.setattr(
        scheduler,
        "_resolve_timeout_for_tenant",
        AsyncMock(return_value=(600, "default")),
    )

    await scheduler._expire_overdue_gates()

    clear_context.assert_awaited_once_with(mock_session)
