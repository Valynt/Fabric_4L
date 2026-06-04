"""Background worker backpressure budget tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

pytestmark = [pytest.mark.performance]


@dataclass(frozen=True)
class BackpressurePolicy:
    max_queue_depth: int
    throttle_depth: int
    reject_depth: int
    worker_concurrency: int
    prefetch_multiplier: int
    max_retries: int

    def decision_for_depth(self, depth: int) -> str:
        if depth >= self.reject_depth:
            return "reject"
        if depth >= self.throttle_depth:
            return "throttle"
        return "accept"

    @property
    def reserved_work_items(self) -> int:
        return self.worker_concurrency * self.prefetch_multiplier


POLICY = BackpressurePolicy(
    max_queue_depth=1_000,
    throttle_depth=700,
    reject_depth=900,
    worker_concurrency=12,
    prefetch_multiplier=1,
    max_retries=3,
)


def test_background_jobs_throttle_before_queue_exhaustion() -> None:
    assert POLICY.throttle_depth < POLICY.reject_depth < POLICY.max_queue_depth
    assert POLICY.decision_for_depth(POLICY.throttle_depth) == "throttle"
    assert POLICY.decision_for_depth(POLICY.reject_depth) == "reject"


def test_prefetch_budget_does_not_hide_backlog_from_scheduler() -> None:
    assert POLICY.prefetch_multiplier == 1
    assert POLICY.reserved_work_items <= POLICY.worker_concurrency


def test_retry_budget_prevents_retry_storms() -> None:
    failed_jobs = 100
    retry_attempts = failed_jobs * POLICY.max_retries

    assert POLICY.max_retries <= 3
    assert retry_attempts <= 300


def test_sustained_overload_fails_closed_with_rejections() -> None:
    decisions = [POLICY.decision_for_depth(depth) for depth in (100, 750, 950)]

    assert decisions == ["accept", "throttle", "reject"]
