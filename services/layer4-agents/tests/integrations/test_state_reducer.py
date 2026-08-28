from __future__ import annotations

from datetime import UTC, datetime

import pytest

from layer4_agents.integration.connectors.core.observations import (
    sync_interrupted,
    sync_started,
    sync_succeeded,
)
from layer4_agents.integration.connectors.core.state import (
    ErrorClass,
    ObservedStatus,
    OperationalStatus,
    reduce,
)


class TestStateReducer:
    """Unit tests for the connection state reducer."""

    def test_idle_initializes_to_idle(self) -> None:
        result = reduce(
            observed=ObservedStatus.IDLE,
            current=None,
        )
        assert result["operational_status"] == "idle"
        assert result["observed_sync_status"] == "idle"
        assert result["error_class"] == "none"
        assert result["status"] == "idle"

    def test_running_from_idle(self) -> None:
        result = reduce(
            observed=ObservedStatus.RUNNING,
            current=OperationalStatus.IDLE,
        )
        assert result["operational_status"] == "running"
        assert result["status"] == "running"

    def test_success_sets_ready_and_last_known_good(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = reduce(
            observed=ObservedStatus.SUCCESS,
            current=OperationalStatus.RUNNING,
            last_known_good_at=None,
            now=now,
        )
        assert result["operational_status"] == "ready"
        assert result["last_known_good_at"] == now
        assert result["status"] == "idle"

    def test_partial_sets_degraded(self) -> None:
        result = reduce(
            observed=ObservedStatus.PARTIAL,
            current=OperationalStatus.RUNNING,
        )
        assert result["operational_status"] == "degraded"
        assert result["status"] == "degraded"

    def test_transient_failure_sets_degraded(self) -> None:
        result = reduce(
            observed=ObservedStatus.FAILURE,
            current=OperationalStatus.READY,
            error_class=ErrorClass.TRANSIENT,
        )
        assert result["operational_status"] == "degraded"
        assert result["status"] == "degraded"

    @pytest.mark.parametrize(
        "error_class",
        [ErrorClass.AUTH, ErrorClass.PERMISSION, ErrorClass.PERMANENT],
    )
    def test_non_transient_failure_degrades_healthy_connection(self, error_class: ErrorClass) -> None:
        result = reduce(
            observed=ObservedStatus.FAILURE,
            current=OperationalStatus.READY,
            error_class=error_class,
        )
        assert result["operational_status"] == "degraded"
        assert result["status"] == "degraded"

    @pytest.mark.parametrize(
        "error_class",
        [ErrorClass.AUTH, ErrorClass.PERMISSION, ErrorClass.PERMANENT],
    )
    def test_non_transient_failure_blocks_degraded_connection(self, error_class: ErrorClass) -> None:
        result = reduce(
            observed=ObservedStatus.FAILURE,
            current=OperationalStatus.DEGRADED,
            error_class=error_class,
        )
        assert result["operational_status"] == "blocked"
        assert result["status"] == "failed"

    def test_success_from_blocked_recover(self) -> None:
        result = reduce(
            observed=ObservedStatus.SUCCESS,
            current=OperationalStatus.BLOCKED,
        )
        assert result["operational_status"] == "ready"

    def test_running_from_blocked_not_allowed_degrades(self) -> None:
        # A direct transition from blocked to running is disallowed by the state
        # machine; the reducer should degrade rather than silently jump.
        result = reduce(
            observed=ObservedStatus.RUNNING,
            current=OperationalStatus.BLOCKED,
        )
        assert result["operational_status"] == "degraded"

    def test_preserves_last_known_good_through_failure(self) -> None:
        lkg = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        result = reduce(
            observed=ObservedStatus.FAILURE,
            current=OperationalStatus.READY,
            error_class=ErrorClass.TRANSIENT,
            last_known_good_at=lkg,
        )
        assert result["last_known_good_at"] == lkg

    def test_sync_started_preserves_operational_state_and_lkg(self) -> None:
        lkg = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        result = reduce(
            observed=sync_started(),
            current=OperationalStatus.READY,
            last_known_good_at=lkg,
        )
        assert result["observed_sync_status"] == "sync_started"
        assert result["operational_status"] == "ready"
        assert result["last_known_good_at"] == lkg
        assert result["error_class"] == "none"

    @pytest.mark.parametrize(
        "current",
        [
            OperationalStatus.IDLE,
            OperationalStatus.READY,
            OperationalStatus.RUNNING,
            OperationalStatus.DEGRADED,
            OperationalStatus.BLOCKED,
        ],
    )
    def test_sync_interrupted_never_blocks(self, current: OperationalStatus) -> None:
        lkg = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        result = reduce(
            observed=sync_interrupted(),
            current=current,
            last_known_good_at=lkg,
        )
        assert result["operational_status"] != "blocked"
        assert result["observed_sync_status"] == "sync_interrupted"
        assert result["error_class"] == "interrupted"
        assert result["last_known_good_at"] == lkg

    def test_started_interrupted_succeeded_ends_ready(self) -> None:
        """sync_started → sync_interrupted → sync_succeeded ends at ready with updated LKG."""
        lkg = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 1, 2, 10, 5, 0, tzinfo=UTC)
        t3 = datetime(2026, 1, 3, 10, 0, 0, tzinfo=UTC)

        r1 = reduce(
            observed=sync_started(),
            current=OperationalStatus.READY,
            last_known_good_at=lkg,
            now=t1,
        )
        assert r1["operational_status"] == "ready"
        assert r1["last_known_good_at"] == lkg

        r2 = reduce(
            observed=sync_interrupted(),
            current=OperationalStatus(r1["operational_status"]),
            last_known_good_at=r1["last_known_good_at"],
            now=t2,
        )
        assert r2["operational_status"] != "blocked"
        assert r2["last_known_good_at"] == lkg

        r3 = reduce(
            observed=sync_succeeded(),
            current=OperationalStatus(r2["operational_status"]),
            last_known_good_at=r2["last_known_good_at"],
            now=t3,
        )
        assert r3["operational_status"] == "ready"
        assert r3["last_known_good_at"] == t3
        assert r3["error_class"] == "none"
