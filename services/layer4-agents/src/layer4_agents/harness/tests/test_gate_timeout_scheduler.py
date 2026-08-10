from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from layer4_agents.harness.gate_timeout_scheduler import (
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

    def scalar_one_or_none(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows, tenant_settings=None):
        self._rows = rows
        self._tenant_settings = tenant_settings or {}
        self.committed = False

    async def execute(self, stmt):
        text = str(stmt)
        if "SELECT tenants.settings" in text:
            tenant_id = str(stmt.compile().params.get("id_1"))
            return _FakeResult(self._tenant_settings.get(tenant_id))
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

    from layer4_agents.config.settings import get_settings as get_layer4_settings

    layer4_settings = get_layer4_settings()
    monkeypatch.setattr(layer4_settings, "agent_gate_timeout_seconds", DEFAULT_GATE_TIMEOUT_SECONDS)
    scheduler = create_gate_timeout_scheduler(_FakeSessionFactory(_FakeSession([])))

    assert scheduler._default_timeout_seconds == DEFAULT_GATE_TIMEOUT_SECONDS


def test_create_gate_timeout_scheduler_uses_env_override(monkeypatch):
    from layer4_agents.config.settings import get_settings as get_layer4_settings

    layer4_settings = get_layer4_settings()
    monkeypatch.setattr(layer4_settings, "agent_gate_timeout_seconds", 900)
    scheduler = create_gate_timeout_scheduler(_FakeSessionFactory(_FakeSession([])))

    assert scheduler._default_timeout_seconds == 900


async def test_expire_overdue_gates_uses_default_timeout_when_no_override():
    stale_gate = SimpleNamespace(
        status="pending",
        tenant_id="tenant_a",
        created_at=datetime.now(UTC) - timedelta(seconds=301),
        decision_by=None,
        decision_reason=None,
        decided_at=None,
    )
    session = _FakeSession([stale_gate], tenant_settings={})
    scheduler = GateTimeoutScheduler(_FakeSessionFactory(session), timeout_seconds=300)

    await scheduler._expire_overdue_gates()

    assert session.committed is True
    assert stale_gate.status == "expired"
    assert stale_gate.decision_reason == "Gate expired after 300s timeout"


async def test_expire_overdue_gates_applies_tenant_override():
    stale_gate = SimpleNamespace(
        status="pending",
        tenant_id="tenant_b",
        created_at=datetime.now(UTC) - timedelta(seconds=401),
        decision_by=None,
        decision_reason=None,
        decided_at=None,
    )
    session = _FakeSession(
        [stale_gate],
        tenant_settings={"tenant_b": {"agent_gate": {"timeout_seconds": 400}}},
    )
    scheduler = GateTimeoutScheduler(_FakeSessionFactory(session), timeout_seconds=300)

    await scheduler._expire_overdue_gates()

    assert stale_gate.status == "expired"
    assert stale_gate.decision_reason == "Gate expired after 400s timeout"


async def test_expire_overdue_gates_rejects_out_of_range_override_and_falls_back_to_default():
    stale_gate = SimpleNamespace(
        status="pending",
        tenant_id="tenant_c",
        created_at=datetime.now(UTC) - timedelta(seconds=301),
        decision_by=None,
        decision_reason=None,
        decided_at=None,
    )
    session = _FakeSession(
        [stale_gate],
        tenant_settings={"tenant_c": {"agent_gate": {"timeout_seconds": 10}}},
    )
    scheduler = GateTimeoutScheduler(_FakeSessionFactory(session), timeout_seconds=300)

    await scheduler._expire_overdue_gates()

    assert stale_gate.status == "expired"
    assert stale_gate.decision_reason == "Gate expired after 300s timeout"
