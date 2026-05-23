from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.jobs.freshness_reconciliation import run_once
from layer5_ground_truth.models.truth_object import TruthObject
from layer5_ground_truth.services.freshness_monitor import (
    FreshnessMonitor,
    run_freshness_check_with_leader_lock,
)


@pytest.mark.asyncio
async def test_leader_lock_skips_when_lock_not_acquired() -> None:
    monitor = FreshnessMonitor()
    monitor.check_and_mark_stale = AsyncMock(return_value={"checked": 1, "marked_stale": 1})

    db = Mock(spec=AsyncSession)
    db.bind = Mock()
    db.bind.dialect.name = "postgresql"
    lock_result = Mock()
    lock_result.scalar.return_value = False
    db.execute = AsyncMock(return_value=lock_result)

    result = await run_freshness_check_with_leader_lock(db, monitor)

    assert result is None
    monitor.check_and_mark_stale.assert_not_awaited()
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_leader_lock_runs_and_unlocks() -> None:
    monitor = FreshnessMonitor()
    expected = {"checked": 2, "marked_stale": 2}
    monitor.check_and_mark_stale = AsyncMock(return_value=expected)

    db = Mock(spec=AsyncSession)
    db.bind = Mock()
    db.bind.dialect.name = "postgresql"
    first_result = Mock()
    first_result.scalar.return_value = True
    db.execute = AsyncMock(side_effect=[first_result, Mock()])

    result = await run_freshness_check_with_leader_lock(db, monitor)

    assert result == expected
    monitor.check_and_mark_stale.assert_awaited_once()
    assert db.execute.await_count == 2

    first_query = str(db.execute.await_args_list[0].args[0])
    second_query = str(db.execute.await_args_list[1].args[0])
    assert "pg_try_advisory_lock" in first_query
    assert "pg_advisory_unlock" in second_query


@pytest.mark.asyncio
async def test_non_postgres_runs_without_lock() -> None:
    monitor = FreshnessMonitor()
    expected = {"checked": 3, "marked_stale": 1}
    monitor.check_and_mark_stale = AsyncMock(return_value=expected)

    db = Mock(spec=AsyncSession)
    db.bind = Mock()
    db.bind.dialect.name = "sqlite"
    db.execute = AsyncMock()

    result = await run_freshness_check_with_leader_lock(db, monitor)

    assert result == expected
    monitor.check_and_mark_stale.assert_awaited_once()
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_mark_stale_skips_event_after_losing_update_race() -> None:
    monitor = FreshnessMonitor()
    expired_truth = TruthObject(
        claim="Expired claim",
        claim_type="other",
        confidence=0.8,
        status="validated",
        maturity_level=4,
        is_stale=False,
    )
    expired_truth.id = "11111111-1111-1111-1111-111111111111"
    expired_truth.tenant_id = "00000000-0000-0000-0000-000000000001"
    expired_truth.sources = []
    expired_truth.expires_at = Mock(isoformat=Mock(return_value="2026-05-01T00:00:00+00:00"))

    select_result = Mock()
    select_result.scalars.return_value.all.return_value = [expired_truth]
    update_result = SimpleNamespace(rowcount=0)

    db = Mock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[select_result, update_result])
    db.add = Mock()

    result = await monitor.check_and_mark_stale(db)

    assert result["checked"] == 1
    assert result["marked_stale"] == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_run_once_reports_skip_when_lock_is_held(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock(spec=AsyncSession)

    class _SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    factory = Mock(return_value=_SessionContext())
    monkeypatch.setattr(
        "layer5_ground_truth.jobs.freshness_reconciliation.get_session_factory",
        Mock(return_value=factory),
    )
    monkeypatch.setattr(
        "layer5_ground_truth.jobs.freshness_reconciliation.run_freshness_check_with_leader_lock",
        AsyncMock(return_value=None),
    )

    result = await run_once()

    assert result["checked"] == 0
    assert result["marked_stale"] == 0
    assert result["skipped"] is True
