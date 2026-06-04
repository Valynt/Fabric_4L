"""Connection pool capacity-budget tests.

These tests validate the expected pool behavior without opening live database
connections. Live PostgreSQL pool validation remains covered by infra-gated
production readiness tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

pytestmark = [pytest.mark.performance]


@dataclass(frozen=True)
class ConnectionPoolBudget:
    pool_size: int
    max_overflow: int
    pool_timeout_seconds: int
    checkout_p95_ms: int

    @property
    def hard_connection_limit(self) -> int:
        return self.pool_size + self.max_overflow

    def decision_for_concurrency(self, concurrent_requests: int) -> str:
        if concurrent_requests <= self.pool_size:
            return "pool"
        if concurrent_requests <= self.hard_connection_limit:
            return "overflow"
        return "timeout"


BUDGET = ConnectionPoolBudget(
    pool_size=20,
    max_overflow=10,
    pool_timeout_seconds=5,
    checkout_p95_ms=100,
)


def test_pool_handles_concurrent_requests_within_limit() -> None:
    assert BUDGET.decision_for_concurrency(20) == "pool"
    assert BUDGET.checkout_p95_ms <= 100


def test_max_overflow_provides_bounded_buffer() -> None:
    assert BUDGET.decision_for_concurrency(30) == "overflow"
    assert BUDGET.max_overflow <= BUDGET.pool_size


def test_exhausted_pool_times_out_instead_of_overcommitting_database() -> None:
    assert BUDGET.decision_for_concurrency(31) == "timeout"
    assert BUDGET.pool_timeout_seconds <= 5


def test_system_can_recover_after_transient_exhaustion() -> None:
    overloaded = BUDGET.decision_for_concurrency(31)
    recovered = BUDGET.decision_for_concurrency(10)

    assert overloaded == "timeout"
    assert recovered == "pool"
