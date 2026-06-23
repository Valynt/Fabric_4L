"""Queue throughput and backlog budget tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

pytestmark = [pytest.mark.performance]


@dataclass(frozen=True)
class QueueEnvelope:
    name: str
    arrival_rate_per_sec: int
    worker_count: int
    worker_throughput_per_sec: int
    max_backlog: int
    max_drain_seconds: int

    @property
    def service_rate_per_sec(self) -> int:
        return self.worker_count * self.worker_throughput_per_sec

    def backlog_after(self, seconds: int) -> int:
        return max(0, (self.arrival_rate_per_sec - self.service_rate_per_sec) * seconds)

    def drain_seconds_after_burst(self, burst_seconds: int) -> float:
        backlog = self.backlog_after(burst_seconds)
        return backlog / max(1, self.service_rate_per_sec)


NORMAL_LOAD = QueueEnvelope(
    name="l1_ingestion_normal",
    arrival_rate_per_sec=20,
    worker_count=6,
    worker_throughput_per_sec=5,
    max_backlog=100,
    max_drain_seconds=30,
)

BURST_LOAD = QueueEnvelope(
    name="l1_ingestion_burst",
    arrival_rate_per_sec=60,
    worker_count=8,
    worker_throughput_per_sec=6,
    max_backlog=800,
    max_drain_seconds=120,
)

BACKGROUND_LOAD = QueueEnvelope(
    name="l4_agent_background",
    arrival_rate_per_sec=12,
    worker_count=5,
    worker_throughput_per_sec=4,
    max_backlog=180,
    max_drain_seconds=60,
)


@pytest.mark.parametrize("envelope", [NORMAL_LOAD, BACKGROUND_LOAD])
def test_steady_state_queue_has_spare_capacity(envelope: QueueEnvelope) -> None:
    assert envelope.service_rate_per_sec > envelope.arrival_rate_per_sec
    assert envelope.backlog_after(60) == 0


def test_burst_backlog_stays_within_capacity_budget() -> None:
    backlog = BURST_LOAD.backlog_after(seconds=60)

    assert backlog <= BURST_LOAD.max_backlog
    assert BURST_LOAD.drain_seconds_after_burst(burst_seconds=60) <= BURST_LOAD.max_drain_seconds


def test_queue_budget_prevents_unbounded_arrival_rate() -> None:
    unsafe = QueueEnvelope(
        name="unsafe",
        arrival_rate_per_sec=80,
        worker_count=8,
        worker_throughput_per_sec=6,
        max_backlog=800,
        max_drain_seconds=120,
    )

    assert unsafe.backlog_after(60) > unsafe.max_backlog
