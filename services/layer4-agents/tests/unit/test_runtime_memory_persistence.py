"""Phase 3 tests for AgentRuntimeImpl memory persistence and resume wiring.

Covers run-envelope snapshots persisted through a configured MemoryPort, the
runtime ``resume_run`` -> WorkflowEnginePort.resume delegation (with tenant and
configuration fail-closed paths), and runtime-context propagation through both
submit and resume paths.
"""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    AgentRuntimeError,
    AgentRuntimeImpl,
    InMemoryMemoryAdapter,
    ResumeRequest,
    RunNotFoundError,
    RunRequest,
    RunStatus,
    RuntimeContext,
    TenantRequiredError,
    WorkflowResult,
    get_tenant_id,
)

pytestmark = pytest.mark.unit


def _ctx(tenant_id: str = "tenant-a", **overrides: Any) -> RuntimeContext:
    base = {
        "tenant_id": tenant_id,
        "trace_id": "trace-1",
        "run_id": "run-1",
        "workflow_id": "wf-1",
        "workflow_type": "demo",
    }
    base.update(overrides)
    return RuntimeContext(**base)


class _EngineDouble:
    """Minimal WorkflowEnginePort double that records tenant/context visibility."""

    def __init__(
        self,
        *,
        execute_result: WorkflowResult | None = None,
        resume_result: WorkflowResult | None = None,
        resume_error: Exception | None = None,
    ) -> None:
        self._execute_result = execute_result or WorkflowResult(status=RunStatus.PAUSED)
        self._resume_result = resume_result or WorkflowResult(
            status=RunStatus.COMPLETED, output={"done": True}
        )
        self._resume_error = resume_error
        self.calls: list[dict[str, Any]] = []

    def get_supported_types(self) -> set[str]:
        return {"demo"}

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Any | None = None,
    ) -> WorkflowResult:
        self.calls.append(
            {
                "op": "execute",
                "workflow_type": workflow_type,
                "run_id": ctx.run_id,
                "workflow_id": ctx.workflow_id,
                "ctx_tenant": get_tenant_id(),
            }
        )
        return self._execute_result

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        self.calls.append(
            {
                "op": "resume",
                "workflow_type": workflow_type,
                "run_id": run_id,
                "resume_request": resume_request,
                "ctx_run_id": ctx.run_id,
                "ctx_tenant": get_tenant_id(),
                "ctx_workflow_type": ctx.workflow_type,
                "ctx_workflow_id": ctx.workflow_id,
            }
        )
        if self._resume_error is not None:
            raise self._resume_error
        return self._resume_result


async def _submit_paused(
    engine: _EngineDouble, ctx: RuntimeContext
) -> tuple[AgentRuntimeImpl, str]:
    """Submit a run that pauses at the engine layer.

    Returns the runtime that owns the in-memory run store together with the
    run id, so resume tests act on the same instance.
    """
    runtime = AgentRuntimeImpl(workflow_engine=engine)
    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)
    return runtime, envelope.run_id


@pytest.mark.asyncio
async def test_submit_run_persists_envelope_snapshot_to_memory() -> None:
    engine = _EngineDouble(execute_result=WorkflowResult(status=RunStatus.COMPLETED, output={"ok": True}))
    memory = InMemoryMemoryAdapter()
    runtime = AgentRuntimeImpl(workflow_engine=engine, memory=memory)
    ctx = _ctx()

    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)

    snapshot = await memory.get_thread_state(envelope.run_id, "tenant-a")
    assert snapshot is not None
    assert snapshot["run_id"] == envelope.run_id
    assert snapshot["workflow_type"] == "demo"
    assert snapshot["tenant_id"] == "tenant-a"
    assert snapshot["status"] == "completed"
    assert snapshot["error_code"] is None


@pytest.mark.asyncio
async def test_resume_run_delegates_to_engine_and_returns_updated_result() -> None:
    engine = _EngineDouble()
    runtime, run_id = await _submit_paused(engine, _ctx())
    resume = ResumeRequest(resume_data={"answer": "yes"})

    result = await runtime.resume_run(run_id, "tenant-a", resume)

    assert result.status == RunStatus.COMPLETED
    assert result.output == {"done": True}
    assert result.run_id == run_id
    calls = [c for c in engine.calls if c["op"] == "resume"]
    assert calls == [
        {
            "op": "resume",
            "workflow_type": "demo",
            "run_id": run_id,
            "resume_request": resume,
            "ctx_run_id": run_id,
            "ctx_tenant": "tenant-a",
            "ctx_workflow_type": "demo",
            "ctx_workflow_id": run_id,
            # captured via current_context() inside the engine resume path
        }
    ]
    # The stored run record reflects the resumed terminal state.
    stored = await runtime.get_run(run_id, "tenant-a")
    assert stored is not None and stored.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_resume_run_requires_tenant_and_fails_closed() -> None:
    runtime = AgentRuntimeImpl(workflow_engine=_EngineDouble())

    with pytest.raises(TenantRequiredError) as exc_info:
        await runtime.resume_run("run-1", "", ResumeRequest())

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_resume_run_without_engine_fails_closed() -> None:
    runtime = AgentRuntimeImpl()

    with pytest.raises(AgentRuntimeError) as exc_info:
        await runtime.resume_run("run-1", "tenant-a", ResumeRequest())

    assert exc_info.value.code == "RESUME_UNAVAILABLE"


@pytest.mark.asyncio
async def test_resume_run_unknown_run_raises_not_found() -> None:
    runtime = AgentRuntimeImpl(workflow_engine=_EngineDouble())

    with pytest.raises(RunNotFoundError) as exc_info:
        await runtime.resume_run("no-such-run", "tenant-a", ResumeRequest())

    assert exc_info.value.code == "RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_resume_run_denies_cross_tenant_run() -> None:
    engine = _EngineDouble()
    runtime, run_id = await _submit_paused(engine, _ctx(tenant_id="tenant-a"))

    with pytest.raises(RunNotFoundError):
        await runtime.resume_run(run_id, "tenant-b", ResumeRequest())

    # The engine must never see the cross-tenant resume attempt.
    assert [c for c in engine.calls if c["op"] == "resume"] == []


@pytest.mark.asyncio
async def test_resume_run_persists_updated_snapshot_to_memory() -> None:
    engine = _EngineDouble()
    memory = InMemoryMemoryAdapter()
    runtime = AgentRuntimeImpl(workflow_engine=engine, memory=memory)
    ctx = _ctx()
    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)

    before = await memory.get_thread_state(envelope.run_id, "tenant-a")
    assert before is not None and before["status"] == "paused"

    await runtime.resume_run(envelope.run_id, "tenant-a", ResumeRequest())

    after = await memory.get_thread_state(envelope.run_id, "tenant-a")
    assert after is not None and after["status"] == "completed"


@pytest.mark.asyncio
async def test_context_propagates_into_engine_during_submit() -> None:
    engine = _EngineDouble()
    ctx = _ctx(tenant_id="tenant-a")
    await _submit_paused(engine, ctx)

    execute_call = [c for c in engine.calls if c["op"] == "execute"][0]
    assert execute_call["ctx_tenant"] == "tenant-a"
    assert execute_call["ctx_tenant"] == ctx.tenant_id


@pytest.mark.asyncio
async def test_submit_run_dispatches_under_authoritative_run_id() -> None:
    engine = _EngineDouble()
    runtime, run_id = await _submit_paused(engine, _ctx())

    # The engine must observe the runtime's authoritative run/workflow ids,
    # never the caller-supplied context's (run-1/wf-1 here).
    execute_call = [c for c in engine.calls if c["op"] == "execute"][0]
    assert execute_call["run_id"] == run_id
    assert execute_call["workflow_id"] == run_id
    assert execute_call["run_id"] != "run-1"
    assert execute_call["workflow_id"] != "wf-1"


@pytest.mark.asyncio
async def test_resume_run_propagates_context_and_engine_failure_keeps_run_paused() -> None:
    engine = _EngineDouble(
        resume_error=AgentRuntimeError(
            "Run is not resumable", code="RUN_NOT_RESUMABLE", details={"run_id": "x"}
        )
    )
    runtime, run_id = await _submit_paused(engine, _ctx())

    with pytest.raises(AgentRuntimeError) as exc_info:
        await runtime.resume_run(run_id, "tenant-a", ResumeRequest())

    assert exc_info.value.code == "RUN_NOT_RESUMABLE"
    # The stored record is untouched by a failed resume.
    stored = await runtime.get_run(run_id, "tenant-a")
    assert stored is not None and stored.status == RunStatus.PAUSED


# --- get_run read-through from MemoryPort (multi-worker / restart safety) ---


@pytest.mark.asyncio
async def test_paused_run_persisted_by_worker_a_is_visible_to_worker_b() -> None:
    memory = InMemoryMemoryAdapter()
    runtime_a = AgentRuntimeImpl(workflow_engine=_EngineDouble(), memory=memory)
    envelope = await runtime_a.submit_run(RunRequest(workflow_type="demo"), _ctx())

    # A second runtime instance (fresh process) sharing the memory adapter.
    runtime_b = AgentRuntimeImpl(memory=memory)
    restored = await runtime_b.get_run(envelope.run_id, "tenant-a")

    assert restored is not None
    assert restored.run_id == envelope.run_id
    assert restored.tenant_id == "tenant-a"
    assert restored.workflow_type == "demo"
    assert restored.status == RunStatus.PAUSED
    assert restored.trace_id == "trace-1"
    # The persisted snapshot is a reduced envelope: no output body survives.
    assert restored.output is None


@pytest.mark.asyncio
async def test_failed_run_restores_with_structured_error_code_only() -> None:
    engine = _EngineDouble(
        execute_result=WorkflowResult(
            status=RunStatus.FAILED, error={"code": "BOOM", "message": "kaput"}
        )
    )
    memory = InMemoryMemoryAdapter()
    runtime_a = AgentRuntimeImpl(workflow_engine=engine, memory=memory)
    envelope = await runtime_a.submit_run(RunRequest(workflow_type="demo"), _ctx())

    runtime_b = AgentRuntimeImpl(memory=memory)
    restored = await runtime_b.get_run(envelope.run_id, "tenant-a")

    assert restored is not None
    assert restored.status == RunStatus.FAILED
    assert restored.output is None
    # Only the structured error code survives the reduced snapshot.
    assert restored.error == {"code": "BOOM"}


@pytest.mark.asyncio
async def test_run_restored_from_memory_resumes_on_second_worker() -> None:
    memory = InMemoryMemoryAdapter()
    runtime_a = AgentRuntimeImpl(workflow_engine=_EngineDouble(), memory=memory)
    envelope = await runtime_a.submit_run(RunRequest(workflow_type="demo"), _ctx())

    engine_b = _EngineDouble()
    runtime_b = AgentRuntimeImpl(workflow_engine=engine_b, memory=memory)
    result = await runtime_b.resume_run(envelope.run_id, "tenant-a", ResumeRequest())

    assert result.status == RunStatus.COMPLETED
    assert result.output == {"done": True}
    # The resume actually dispatched through worker B's engine.
    assert [c for c in engine_b.calls if c["op"] == "resume"]
    # The resumed terminal state is mirrored back to memory.
    snapshot = await memory.get_thread_state(envelope.run_id, "tenant-a")
    assert snapshot is not None and snapshot["status"] == "completed"


@pytest.mark.asyncio
async def test_get_run_restore_is_tenant_scoped() -> None:
    memory = InMemoryMemoryAdapter()
    runtime_a = AgentRuntimeImpl(workflow_engine=_EngineDouble(), memory=memory)
    envelope = await runtime_a.submit_run(
        RunRequest(workflow_type="demo"), _ctx(tenant_id="tenant-a")
    )

    runtime_b = AgentRuntimeImpl(memory=memory)
    # Worker B under another tenant must not see tenant A's run.
    assert await runtime_b.get_run(envelope.run_id, "tenant-b") is None


@pytest.mark.asyncio
async def test_get_run_without_memory_returns_none_for_unknown_run() -> None:
    runtime = AgentRuntimeImpl()
    assert await runtime.get_run("no-such-run", "tenant-a") is None


@pytest.mark.asyncio
async def test_malformed_snapshot_fails_closed_on_restore() -> None:
    memory = InMemoryMemoryAdapter()
    await memory.save_thread_state("run-bad", "tenant-a", {"run_id": "run-bad"})

    runtime = AgentRuntimeImpl(memory=memory)
    assert await runtime.get_run("run-bad", "tenant-a") is None


@pytest.mark.asyncio
async def test_snapshot_with_unknown_status_fails_closed_on_restore() -> None:
    memory = InMemoryMemoryAdapter()
    await memory.save_thread_state(
        "run-x",
        "tenant-a",
        {
            "run_id": "run-x",
            "workflow_id": "wf-1",
            "trace_id": "trace-1",
            "tenant_id": "tenant-a",
            "workflow_type": "demo",
            "status": "bogus-status",
            "created_at": "2024-01-01T00:00:00+00:00",
        },
    )

    runtime = AgentRuntimeImpl(memory=memory)
    assert await runtime.get_run("run-x", "tenant-a") is None


# --- cancel persistence (cross-worker terminal-state consistency) ---


@pytest.mark.asyncio
async def test_cancel_run_persists_cancellation_visible_across_workers() -> None:
    memory = InMemoryMemoryAdapter()
    runtime_a = AgentRuntimeImpl(workflow_engine=_EngineDouble(), memory=memory)
    envelope = await runtime_a.submit_run(RunRequest(workflow_type="demo"), _ctx())

    cancelled = await runtime_a.cancel_run(envelope.run_id, "tenant-a")
    assert cancelled.status == RunStatus.CANCELLED

    # The terminal state is mirrored through memory...
    snapshot = await memory.get_thread_state(envelope.run_id, "tenant-a")
    assert snapshot is not None and snapshot["status"] == "cancelled"

    # ...so a second worker observes CANCELLED, not a stale in-flight run.
    runtime_b = AgentRuntimeImpl(memory=memory)
    restored = await runtime_b.get_run(envelope.run_id, "tenant-a")
    assert restored is not None and restored.status == RunStatus.CANCELLED
    assert restored.completed_at is not None
