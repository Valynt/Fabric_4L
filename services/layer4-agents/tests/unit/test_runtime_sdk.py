"""Phase 4 SDK tests: client round-trips, tenant scoping, and agent helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from layer4_agents.runtime import (
    AgentRuntimeImpl,
    Checkpoint,
    ModelProviderPort,
    ResumeRequest,
    RunEnvelope,
    RunRequest,
    RunResult,
    RunStatus,
    RunSummary,
    RuntimeContext,
    TenantRequiredError,
    ToolDef,
    WorkflowResult,
)
from layer4_agents.runtime.errors import RunNotFoundError
from layer4_agents.runtime.ports import WorkflowFactory
from layer4_agents.runtime.sdk import (
    Agent,
    AgentRuntimeClient,
    AgentSpec,
    SDKTimeoutError,
    create_agent,
)

pytestmark = pytest.mark.unit


def _echo_factory(status: RunStatus = RunStatus.COMPLETED) -> WorkflowFactory:
    async def factory(
        workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext
    ) -> WorkflowResult:
        return WorkflowResult(
            status=status,
            output={
                "workflow_type": workflow_type,
                "input": input_data,
                "tenant_id": ctx.tenant_id,
            },
        )

    return factory


def _runtime_with_factory(status: RunStatus = RunStatus.COMPLETED) -> AgentRuntimeImpl:
    runtime = AgentRuntimeImpl()
    runtime.register_workflow_type("echo", _echo_factory(status))
    return runtime


class _PausingEngine:
    """WorkflowEnginePort double: execute pauses, resume completes."""

    def get_supported_types(self) -> set[str]:
        return {"echo"}

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Checkpoint | None = None,
    ) -> WorkflowResult:
        return WorkflowResult(status=RunStatus.PAUSED, output={"phase": "paused"})

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        return WorkflowResult(
            status=RunStatus.COMPLETED,
            output={
                "resumed": True,
                "resume_data": resume_request.resume_data,
                "run_id": run_id,
            },
        )


class _FakeRuntime:
    """AgentRuntime stand-in whose runs never auto-finalize on submit."""

    def __init__(self) -> None:
        self._runs: dict[str, RunResult] = {}
        self._next_id = 1
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def submit_run(self, request: RunRequest, ctx: RuntimeContext) -> RunEnvelope:
        run_id = f"fake-{self._next_id}"
        self._next_id += 1
        now = datetime.now(UTC).isoformat()
        self._runs[run_id] = RunResult(
            run_id=run_id,
            workflow_id=ctx.workflow_id,
            trace_id=ctx.trace_id,
            tenant_id=ctx.tenant_id,
            workflow_type=request.workflow_type,
            status=RunStatus.PENDING,
            created_at=now,
        )
        return RunEnvelope(
            run_id=run_id,
            workflow_id=ctx.workflow_id,
            trace_id=ctx.trace_id,
            tenant_id=ctx.tenant_id,
            workflow_type=request.workflow_type,
            status=RunStatus.PENDING,
            created_at=now,
        )

    async def get_run(self, run_id: str, tenant_id: str) -> RunResult | None:
        result = self._runs.get(run_id)
        if result is None or result.tenant_id != tenant_id:
            return None
        return result

    async def list_runs(
        self,
        tenant_id: str,
        *,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        summaries: list[RunSummary] = []
        for run in self._runs.values():
            if run.tenant_id != tenant_id:
                continue
            if workflow_type and run.workflow_type != workflow_type:
                continue
            if status and run.status.value != status:
                continue
            summaries.append(
                RunSummary(
                    run_id=run.run_id,
                    workflow_id=run.workflow_id,
                    workflow_type=run.workflow_type,
                    status=run.status,
                    created_at=run.created_at,
                )
            )
        return summaries

    async def cancel_run(self, run_id: str, tenant_id: str) -> RunResult:
        raise NotImplementedError

    async def resume_run(self, run_id: str, tenant_id: str, resume: ResumeRequest) -> RunResult:
        raise NotImplementedError

    def register_tool(self, tool: ToolDef) -> None:
        return None

    def register_workflow_type(self, workflow_type: str, factory: WorkflowFactory) -> None:
        return None

    def register_model_provider(self, name: str, provider: ModelProviderPort) -> None:
        return None

    async def complete_run(self, run_id: str, tenant_id: str) -> None:
        result = self._runs[run_id]
        assert result.tenant_id == tenant_id
        self._runs[run_id] = result.model_copy(
            update={
                "status": RunStatus.COMPLETED,
                "output": {"ok": True},
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )


async def test_client_submit_returns_identity_envelope() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    envelope = await client.submit_run("echo", {"n": 1})
    assert isinstance(envelope, RunEnvelope)
    assert envelope.tenant_id == "tenant-a"
    assert envelope.workflow_type == "echo"
    assert envelope.status == RunStatus.PENDING
    assert envelope.run_id


async def test_client_submit_wait_round_trip() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    envelope = await client.submit_run("echo", {"n": 1})
    result = await client.wait_for_run(envelope.run_id)
    assert isinstance(result, RunResult)
    assert result.run_id == envelope.run_id
    assert result.status == RunStatus.COMPLETED
    assert result.output == {
        "workflow_type": "echo",
        "input": {"n": 1},
        "tenant_id": "tenant-a",
    }


async def test_client_context_manager_starts_and_stops_runtime() -> None:
    fake = _FakeRuntime()
    client = AgentRuntimeClient(fake, default_tenant_id="tenant-a")
    assert fake.started is False
    async with client:
        assert fake.started is True
    assert fake.stopped is True


async def test_client_missing_tenant_fails_closed() -> None:
    client = AgentRuntimeClient(_runtime_with_factory())
    with pytest.raises(TenantRequiredError) as exc_info:
        await client.submit_run("echo", {})
    assert exc_info.value.code == "TENANT_REQUIRED"


async def test_client_get_run_is_tenant_scoped() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    envelope = await client.submit_run("echo", {"x": 1})
    found = await client.get_run(envelope.run_id)
    assert found is not None
    assert found.status == RunStatus.COMPLETED
    # Cross-tenant lookup fails closed (None, not a leak).
    assert await client.get_run(envelope.run_id, tenant_id="tenant-b") is None
    assert await client.get_run("missing", tenant_id="tenant-a") is None


async def test_client_list_runs_filters_by_tenant_type_and_status() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    first = await client.submit_run("echo", {"a": 1})
    second = await client.submit_run("echo", {"b": 2})
    assert {r.run_id for r in await client.list_runs()} == {first.run_id, second.run_id}
    assert await client.list_runs(tenant_id="tenant-b") == []
    assert len(await client.list_runs(workflow_type="echo")) == 2
    assert await client.list_runs(workflow_type="other") == []
    assert len(await client.list_runs(status="completed")) == 2
    assert await client.list_runs(status="pending") == []


async def test_client_cancel_run() -> None:
    runtime = AgentRuntimeImpl(workflow_engine=_PausingEngine())
    client = AgentRuntimeClient(runtime, default_tenant_id="tenant-a")
    envelope = await client.submit_run("echo", {"a": 1})
    assert (await client.get_run(envelope.run_id)) is not None
    cancelled = await client.cancel_run(envelope.run_id)
    assert cancelled.status == RunStatus.CANCELLED
    with pytest.raises(RunNotFoundError):
        await client.cancel_run("does-not-exist")


async def test_client_resume_run_completes_paused_run() -> None:
    runtime = AgentRuntimeImpl(workflow_engine=_PausingEngine())
    client = AgentRuntimeClient(runtime, default_tenant_id="tenant-a")
    envelope = await client.submit_run("echo", {"q": 1})
    paused = await client.get_run(envelope.run_id)
    assert paused is not None and paused.status == RunStatus.PAUSED
    resumed = await client.resume_run(envelope.run_id, resume_data={"continue": True})
    assert resumed.status == RunStatus.COMPLETED
    assert resumed.output == {
        "resumed": True,
        "resume_data": {"continue": True},
        "run_id": envelope.run_id,
    }


async def test_client_wait_polls_until_terminal() -> None:
    fake = _FakeRuntime()
    client = AgentRuntimeClient(fake, default_tenant_id="tenant-a", poll_interval=0.001)
    envelope = await client.submit_run("echo", {"n": 1})
    waiter = asyncio.create_task(client.wait_for_run(envelope.run_id, timeout_seconds=5.0))
    await asyncio.sleep(0.01)
    await fake.complete_run(envelope.run_id, "tenant-a")
    result = await asyncio.wait_for(waiter, timeout=1)
    assert result.status == RunStatus.COMPLETED
    assert result.output == {"ok": True}


async def test_client_wait_times_out_while_active() -> None:
    fake = _FakeRuntime()
    client = AgentRuntimeClient(fake, default_tenant_id="tenant-a", poll_interval=0.001)
    envelope = await client.submit_run("echo", {})
    with pytest.raises(SDKTimeoutError) as exc_info:
        await client.wait_for_run(envelope.run_id, timeout_seconds=0.05)
    assert exc_info.value.code == "SDK_WAIT_TIMEOUT"


async def test_client_wait_raises_not_found_for_missing_run() -> None:
    client = AgentRuntimeClient(_FakeRuntime(), default_tenant_id="tenant-a")
    with pytest.raises(RunNotFoundError) as exc_info:
        await client.wait_for_run("missing", timeout_seconds=0.05)
    assert exc_info.value.code == "RUN_NOT_FOUND"


async def test_client_runs_namespace_mirrors_sdk_example() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    async with client:
        run = await client.runs.submit(
            workflow_type="echo",
            input_data={"prospect_id": "123"},
            tenant_id="tenant-a",
        )
        result = await client.runs.wait(run.run_id, tenant_id="tenant-a")
    assert result.status == RunStatus.COMPLETED
    assert result.output["input"] == {"prospect_id": "123"}


async def test_submit_rejects_empty_workflow_type() -> None:
    client = AgentRuntimeClient(_FakeRuntime(), default_tenant_id="tenant-a")
    with pytest.raises(ValidationError):
        await client.submit_run("", {})


async def test_agent_run_submits_and_waits() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    agent = create_agent(
        client,
        name="roi-agent",
        workflow_type="echo",
        description="Echo agent",
        tools=("calculate_roi",),
    )
    assert agent.name == "roi-agent"
    assert agent.workflow_type == "echo"
    result = await agent.run({"prospect_id": "123"})
    assert isinstance(result, RunResult)
    assert result.status == RunStatus.COMPLETED
    assert result.output["input"] == {"prospect_id": "123"}


async def test_agent_run_without_wait_returns_envelope() -> None:
    client = AgentRuntimeClient(_runtime_with_factory(), default_tenant_id="tenant-a")
    agent = create_agent(client, name="x", workflow_type="echo")
    out = await agent.run({"a": 1}, wait=False)
    assert isinstance(out, RunEnvelope)
    assert out.status == RunStatus.PENDING


async def test_agent_uses_spec_default_tenant() -> None:
    runtime = _runtime_with_factory()
    client = AgentRuntimeClient(runtime)
    agent = Agent(
        AgentSpec(name="tenanted", workflow_type="echo", default_tenant_id="tenant-a"),
        client,
    )
    result = await agent.run({"a": 1})
    assert result.output["tenant_id"] == "tenant-a"


async def test_agent_missing_tenant_fails_closed() -> None:
    client = AgentRuntimeClient(_runtime_with_factory())
    agent = create_agent(client, name="n", workflow_type="echo")
    with pytest.raises(TenantRequiredError):
        await agent.run({"a": 1})


async def test_agent_resume_completes_paused_run() -> None:
    runtime = AgentRuntimeImpl(workflow_engine=_PausingEngine())
    client = AgentRuntimeClient(runtime, default_tenant_id="tenant-a")
    agent = create_agent(client, name="pausey", workflow_type="echo")
    envelope = await agent.run({"a": 1}, wait=False)
    resumed = await agent.resume(envelope.run_id, resume_data={"continue": True})
    assert resumed.status == RunStatus.COMPLETED


def test_sdk_public_surface_exports() -> None:
    import layer4_agents.runtime.sdk as sdk

    for name in (
        "Agent",
        "AgentRuntimeClient",
        "AgentRuntimeImpl",
        "AgentSpec",
        "RunEnvelope",
        "RunResult",
        "RunStatus",
        "RunsNamespace",
        "SDKTimeoutError",
        "create_agent",
    ):
        assert hasattr(sdk, name), name
