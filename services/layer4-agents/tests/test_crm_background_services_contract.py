from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import layer4_agents.services.crm_sync_job_runner as runner_module
import layer4_agents.services.crm_sync_scheduler as scheduler_module
from layer4_agents.models.account import CRMProvider
from layer4_agents.models.crm_sync_job import CRMSyncJobStatus
from layer4_agents.services.crm_sync_job_runner import CRMSyncJobRunner
from layer4_agents.services.crm_sync_scheduler import CRMSyncScheduler


class ScalarResult:
    def __init__(self, value=None, values=()):
        self.value = value
        self.values = list(values)

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)

    def all(self):
        return self.values


class Session:
    def __init__(self, results=()):
        self.results = list(results)
        self.commits = 0
        self.info = {}

    async def execute(self, _query):
        return self.results.pop(0)

    async def commit(self):
        self.commits += 1


class Scheduler:
    def __init__(self):
        self.started = self.stopped = 0
        self.scheduled = []
        self.cancelled = []

    async def start(self):
        self.started += 1

    async def stop(self):
        self.stopped += 1

    async def schedule_task(self, task):
        self.scheduled.append(task)
        return f"scheduled-{len(self.scheduled)}"

    async def cancel_task(self, task_id):
        self.cancelled.append(task_id)

    def get_stats(self):
        return {"queued": len(self.scheduled)}


def session_context(session):
    @asynccontextmanager
    async def context(*_args, **_kwargs):
        yield session

    return context


@pytest.mark.asyncio
async def test_runner_lifecycle_recovery_and_payload_loop(monkeypatch) -> None:
    redis = SimpleNamespace()
    runner = CRMSyncJobRunner(redis)
    recovered = []
    handled = []
    job = SimpleNamespace(id="job", tenant_id="tenant", provider=CRMProvider.SALESFORCE)
    session = Session([ScalarResult(values=[job])])
    monkeypatch.setattr(runner_module, "get_session_factory", lambda: session_context(session))
    monkeypatch.setattr(
        runner_module,
        "enqueue_crm_sync_job",
        lambda **kwargs: _record(recovered, kwargs),
    )
    await runner.recover_pending_jobs()
    assert recovered == [
        {"redis_client": redis, "job_id": "job", "tenant_id": "tenant", "provider": "salesforce"}
    ]

    items = [("queue", json.dumps({"job_id": "job"})), None]

    async def brpop(*_args, **_kwargs):
        item = items.pop(0)
        if item is None:
            runner._stopping.set()
        return item

    redis.brpop = brpop
    monkeypatch.setattr(runner, "_handle_payload", lambda payload: _record(handled, payload))
    await runner._run()
    assert handled == [json.dumps({"job_id": "job"})]

    runner._stopping.clear()
    monkeypatch.setattr(runner, "recover_pending_jobs", lambda: _record(handled, "recover"))
    await runner.start()
    assert runner._task is not None
    await runner.stop()


@pytest.mark.asyncio
async def test_runner_handles_missing_integration_and_sync_outcomes(monkeypatch) -> None:
    runner = CRMSyncJobRunner(SimpleNamespace())
    observations = []
    audits = []
    current = {}
    session = Session()
    monkeypatch.setattr(runner_module, "db_session_for_context", session_context(session))
    monkeypatch.setattr(
        runner_module, "apply_observation", lambda *_args: _record(observations, _args[-1])
    )
    monkeypatch.setattr(runner_module, "emit_audit_event", lambda **kwargs: _record(audits, kwargs))

    class IntegrationService:
        def __init__(self, _db):
            pass

        async def get_integration(self, *_args):
            return current.get("integration")

    class SyncService:
        def __init__(self, _db):
            pass

        async def sync_provider(self, *_args, **_kwargs):
            outcome = current["outcome"]
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    monkeypatch.setattr(
        "layer4_agents.services.integration_service.IntegrationService", IntegrationService
    )
    monkeypatch.setattr("layer4_agents.services.crm_sync_service.CRMSyncService", SyncService)

    def job(status=CRMSyncJobStatus.QUEUED):
        return SimpleNamespace(
            id="job",
            tenant_id="tenant",
            provider=CRMProvider.SALESFORCE,
            status=status,
            requested_by="user",
            started_at=None,
        )

    payload = json.dumps({"job_id": "job", "tenant_id": "tenant", "provider": "salesforce"})
    missing = job()
    session.results = [ScalarResult(missing)]
    await runner._handle_payload(payload)
    assert missing.status == CRMSyncJobStatus.FAILED and "integration" in missing.error_summary

    cancelled = job(CRMSyncJobStatus.CANCELLED)
    session.results = [ScalarResult(cancelled)]
    await runner._handle_payload(payload)

    for outcome, expected in [
        ({"synced": 2, "updated": 1, "failed": 0, "errors": []}, CRMSyncJobStatus.SUCCEEDED),
        ({"synced": 1, "updated": 0, "failed": 2, "errors": ["safe"]}, CRMSyncJobStatus.FAILED),
        (RuntimeError("secret must not leak"), CRMSyncJobStatus.FAILED),
    ]:
        integration = SimpleNamespace()
        current.update(integration=integration, outcome=outcome)
        value = job()
        session.results = [ScalarResult(value)]
        await runner._handle_payload(payload)
        assert value.status == expected
        if isinstance(outcome, Exception):
            assert value.error_summary == "RuntimeError: sync_job_failed"


@pytest.mark.asyncio
async def test_scheduler_lifecycle_status_and_sweep(monkeypatch) -> None:
    backend = Scheduler()
    service = CRMSyncScheduler(backend)
    await service.start()
    await service.start()
    assert backend.started == 1 and len(backend.scheduled) == 1
    status = service.get_status()
    assert (
        status.running and status.scheduled_tasks == 1 and status.scheduler_stats == {"queued": 1}
    )
    await service.stop()
    await service.stop()
    assert backend.cancelled == ["scheduled-1"] and backend.stopped == 1

    rows = [
        SimpleNamespace(tenant_id="a", provider="salesforce"),
        SimpleNamespace(tenant_id="b", provider="invalid"),
        SimpleNamespace(tenant_id="c", provider="hubspot"),
    ]
    session = Session([ScalarResult(values=rows)])
    monkeypatch.setattr(scheduler_module, "get_session_factory", lambda: session_context(session))
    monkeypatch.setattr(scheduler_module, "_clear_local_tenant_context", lambda _db: _completed())
    calls = []

    async def sync(tenant, provider):
        calls.append((tenant, provider))
        if tenant == "c":
            raise RuntimeError("failed")
        return {}

    monkeypatch.setattr(service, "_execute_sync_for_tenant", sync)
    service._running = True
    result = await service._execute_tenant_sweep()
    assert result["tenants_checked"] == 3 and result["syncs_triggered"] == 1
    assert len(result["errors"]) == 2 and calls[0] == ("a", CRMProvider.SALESFORCE)


@pytest.mark.asyncio
async def test_scheduler_tenant_sync_paths(monkeypatch) -> None:
    service = CRMSyncScheduler(Scheduler())
    session = Session()
    monkeypatch.setattr(scheduler_module, "db_session_for_context", session_context(session))
    observations = []
    monkeypatch.setattr(
        scheduler_module, "apply_observation", lambda *_args: _record(observations, _args[-1])
    )
    current = {"integration": None, "outcome": {}}

    class IntegrationService:
        def __init__(self, _db):
            pass

        async def get_integration(self, *_args):
            return current["integration"]

    class SyncService:
        def __init__(self, _db, batch_size):
            assert batch_size == service._batch_size

        async def sync_provider(self, *_args, **_kwargs):
            outcome = current["outcome"]
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    monkeypatch.setattr(scheduler_module, "IntegrationService", IntegrationService)
    monkeypatch.setattr(scheduler_module, "CRMSyncService", SyncService)
    assert (await service._execute_sync_for_tenant("tenant", CRMProvider.HUBSPOT))[
        "reason"
    ] == "not_configured"
    current["integration"] = SimpleNamespace(enabled=False)
    assert (await service._execute_sync_for_tenant("tenant", CRMProvider.HUBSPOT))[
        "reason"
    ] == "disabled"

    for outcome in [
        {"synced": 2, "updated": 1, "failed": 0, "errors": []},
        {"synced": 0, "updated": 1, "failed": 2, "errors": ["safe"]},
    ]:
        current["integration"] = SimpleNamespace(enabled=True)
        current["outcome"] = outcome
        assert await service._execute_sync_for_tenant("tenant", CRMProvider.HUBSPOT) == outcome

    current["integration"] = SimpleNamespace(enabled=True)
    current["outcome"] = RuntimeError("secret")
    with pytest.raises(RuntimeError, match="secret"):
        await service._execute_sync_for_tenant("tenant", CRMProvider.HUBSPOT)
    assert current["integration"].last_error_message == "RuntimeError: sync_failed"

    invalid = await service._execute_sync("bad")
    assert invalid.error == "Invalid provider: bad"
    deprecated = await service._execute_sync("salesforce")
    assert deprecated.skipped and deprecated.reason == "deprecated_path"


@pytest.mark.asyncio
async def test_scheduler_manual_trigger_and_singleton(monkeypatch) -> None:
    service = CRMSyncScheduler(Scheduler())
    monkeypatch.setattr(service, "_execute_sync_for_tenant", lambda *_args: _value({"one": 1}))
    monkeypatch.setattr(service, "_execute_tenant_sweep", lambda: _value({"all": 1}))
    assert await service.trigger_sync_now("tenant", CRMProvider.SALESFORCE) == {"one": 1}
    assert await service.trigger_sync_now() == {"all": 1}
    monkeypatch.setattr(scheduler_module, "_crm_sync_scheduler", None)
    assert (
        await scheduler_module.get_crm_sync_scheduler()
        is await scheduler_module.get_crm_sync_scheduler()
    )


async def _record(target, value):
    target.append(value)


async def _completed():
    return None


async def _value(value):
    return value
