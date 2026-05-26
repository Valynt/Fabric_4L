from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from harness.gate_timeout_scheduler import (
    DEFAULT_GATE_TIMEOUT_SECONDS,
    GateTimeoutScheduler,
    create_gate_timeout_scheduler,
)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.committed = False

    async def execute(self, _stmt):
        return _FakeResult(self._rows)

    async def commit(self):
        self.committed = True


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_create_gate_timeout_scheduler_uses_default_when_env_absent(monkeypatch):
    monkeypatch.delenv("LAYER4_AGENT_GATE_TIMEOUT_SECONDS", raising=False)

    from config.settings import Settings

    monkeypatch.setattr("harness.gate_timeout_scheduler.settings", Settings())
    scheduler = create_gate_timeout_scheduler(_FakeSessionFactory(_FakeSession([])))

    assert scheduler._timeout_seconds == DEFAULT_GATE_TIMEOUT_SECONDS


def test_create_gate_timeout_scheduler_uses_env_override(monkeypatch):
    monkeypatch.setenv("LAYER4_AGENT_GATE_TIMEOUT_SECONDS", "900")

    from config.settings import Settings

    monkeypatch.setattr("harness.gate_timeout_scheduler.settings", Settings())
    scheduler = create_gate_timeout_scheduler(_FakeSessionFactory(_FakeSession([])))

    assert scheduler._timeout_seconds == 900


async def test_expire_overdue_gates_transitions_pending_rows_to_expired():
    stale_gate = SimpleNamespace(
        status="pending",
        created_at=datetime.now(UTC) - timedelta(seconds=301),
        decision_by=None,
        decision_reason=None,
        decided_at=None,
    )
    session = _FakeSession([stale_gate])
    scheduler = GateTimeoutScheduler(_FakeSessionFactory(session), timeout_seconds=300)

    await scheduler._expire_overdue_gates()

    assert session.committed is True
    assert stale_gate.status == "expired"
    assert stale_gate.decision_by == "system"
    assert stale_gate.decision_reason == "Gate expired after 300s timeout"
    assert stale_gate.decided_at is not None
