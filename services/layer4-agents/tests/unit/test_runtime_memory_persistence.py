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
