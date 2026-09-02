"""Phase 2 tests for the LangGraph WorkflowEnginePort adapter.

Covers execute/resume dispatch, fail-closed tenant/type validation, snapshot
persistence for resumable statuses, checkpoint-conflict handling, and one
genuine LangGraph interrupt -> resume round trip through the adapter.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt

from layer4_agents.models.agent_state import (
    BaseAgentState,
    WorkflowStatus,
    WorkflowType,
)
from layer4_agents.models.workflow_config import (
    EdgeConfig,
    NodeConfig,
    NodeType,
    WorkflowConfig,
)
from layer4_agents.runtime import (
    AgentRuntimeError,
    Checkpoint,
    CheckpointConflictError,
    InMemoryCheckpointAdapter,
    LangGraphWorkflowEngineAdapter,
    ResumeRequest,
    RunNotFoundError,
    RunStatus,
    RuntimeContext,
    TenantRequiredError,
    WorkflowTypeNotFoundError,
)
from layer4_agents.runtime.ports import CheckpointPort, WorkflowEnginePort
from layer4_agents.workflows import WORKFLOW_TYPES
from layer4_agents.workflows.base import BaseWorkflow

pytestmark = pytest.mark.unit

_SUPPORTED = {"demo"}


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


class _WorkflowDouble:
    """Minimal workflow double exposing the BaseWorkflow surface the adapter uses."""

    def __init__(
        self,
        *,
        terminal_status: WorkflowStatus = WorkflowStatus.COMPLETED,
        node_output: dict[str, Any] | None = None,
        run_error: Exception | None = None,
        calls: list[dict[str, Any]] | None = None,
    ) -> None:
        self._terminal_status = terminal_status
        self._node_output = node_output if node_output is not None else {"done": True}
        self._run_error = run_error
        self._calls = calls

    def _get_state_type(self) -> type[BaseAgentState]:
        # mypy run directly on test files (without src on MYPYPATH) resolves the
        # layer4_agents package to Any; the typed return then trips no-any-return.
        return BaseAgentState  # type: ignore[no-any-return]

    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> BaseAgentState:
        return BaseAgentState(
            tenant_id=tenant_id or "tenant-a",
            run_id=run_id or "run-1",
            trace_id=trace_id or "trace-1",
            workflow_id=workflow_id or "wf-1",
            workflow_type=WorkflowType.ROI_CALCULATOR,
            status=WorkflowStatus.PENDING,
            input_data=dict(input_data or {}),
            output_data={},
            errors=[],
        )

    async def run(
        self,
        initial_state: BaseAgentState,
        thread_id: str | None = None,
        recursion_limit: int | None = None,
        resume_data: Any = None,
        checkpoint_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseAgentState:
        if self._calls is not None:
            self._calls.append(
                {
                    "thread_id": thread_id,
                    "resume_data": resume_data,
                    "checkpoint_config": checkpoint_config,
                    "state_status": initial_state.status,
                    "input_data": initial_state.input_data,
                    "tenant_id": initial_state.tenant_id,
                    "workflow_type": initial_state.workflow_type,
                }
            )
        if self._run_error is not None:
            raise self._run_error
        final = initial_state.model_copy(deep=True)
        final.status = self._terminal_status
        final.current_node = "end"
        final.output_data = dict(initial_state.output_data or {})
        final.output_data.update(self._node_output)
        return final


def _double_factory(
    **kwargs: Any,
) -> tuple[Any, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    def factory(workflow_type: str, tool_registry: Any, checkpoint_saver: Any = None) -> _WorkflowDouble:
        return _WorkflowDouble(**kwargs, calls=calls)

    return factory, calls


def _engine(
    *,
    checkpoint_port: CheckpointPort | None = None,
    checkpoint_saver: Any = None,
    workflow_types: set[str] = _SUPPORTED,
    create_workflow_fn: Any = None,
) -> LangGraphWorkflowEngineAdapter:
    return LangGraphWorkflowEngineAdapter(
        checkpoint_port=checkpoint_port,
        checkpoint_saver=checkpoint_saver,
        workflow_types=workflow_types,
        create_workflow_fn=create_workflow_fn,
    )


def test_adapter_satisfies_workflow_engine_port() -> None:
    engine = _engine(create_workflow_fn=_double_factory()[0])
    assert isinstance(engine, WorkflowEnginePort)


def test_get_supported_types_returns_configured_set() -> None:
    engine = _engine(workflow_types={"demo", "demo2"}, create_workflow_fn=_double_factory()[0])
    assert engine.get_supported_types() == {"demo", "demo2"}


def test_default_adapter_exposes_legacy_workflow_types() -> None:
    engine = LangGraphWorkflowEngineAdapter()
    assert engine.get_supported_types() == set(WORKFLOW_TYPES)


@pytest.mark.asyncio
async def test_execute_unknown_workflow_type_fails_closed() -> None:
    factory, calls = _double_factory()
    engine = _engine(create_workflow_fn=factory)

    with pytest.raises(WorkflowTypeNotFoundError) as exc_info:
        await engine.execute("not_registered", {}, _ctx())

    assert exc_info.value.code == "WORKFLOW_TYPE_NOT_FOUND"
    assert exc_info.value.details["workflow_type"] == "not_registered"
    assert calls == []


@pytest.mark.asyncio
async def test_execute_missing_tenant_fails_closed() -> None:
    factory, calls = _double_factory()
    engine = _engine(create_workflow_fn=factory)
    ctx = _ctx(tenant_id="")

    with pytest.raises(TenantRequiredError) as exc_info:
        await engine.execute("demo", {}, ctx)

    assert exc_info.value.code == "TENANT_REQUIRED"
    assert calls == []


@pytest.mark.asyncio
async def test_execute_rejects_starting_from_existing_checkpoint() -> None:
    factory, _calls = _double_factory()
    engine = _engine(create_workflow_fn=factory)
    checkpoint = Checkpoint(
        checkpoint_id="run-1:state:aaaaaaaa",
        run_id="run-1",
        thread_id="thread-1",
        tenant_id="tenant-a",
        state_hash="aa" * 32,
    )

    with pytest.raises(AgentRuntimeError) as exc_info:
        await engine.execute("demo", {}, _ctx(), checkpoint=checkpoint)

    assert exc_info.value.code == "EXECUTE_WITH_CHECKPOINT_UNSUPPORTED"


@pytest.mark.asyncio
async def test_execute_completed_run_seeds_state_and_maps_result() -> None:
    factory, calls = _double_factory()
    engine = _engine(create_workflow_fn=factory)
    ctx = _ctx(tenant_id="tenant-a", run_id="run-seed", workflow_id="wf-seed", trace_id="trace-seed")
    input_data = {"prospect_id": "acme"}

    result = await engine.execute("demo", input_data, ctx)

    assert result.status == RunStatus.COMPLETED
    assert result.error is None
    assert result.checkpoint is None
    assert result.output == {"done": True}
    assert len(calls) == 1
    call = calls[0]
    assert call["thread_id"] == "run-seed"
    assert call["resume_data"] is None
    assert call["state_status"] == WorkflowStatus.PENDING
    assert call["tenant_id"] == "tenant-a"
    assert call["input_data"] == input_data
    assert call["workflow_type"] == WorkflowType.ROI_CALCULATOR


@pytest.mark.asyncio
async def test_execute_maps_generic_workflow_failure_to_failed_result() -> None:
    factory, _calls = _double_factory(run_error=RuntimeError("boom"))
    engine = _engine(create_workflow_fn=factory)
    ctx = _ctx(run_id="run-fail")

    result = await engine.execute("demo", {}, ctx)

    assert result.status == RunStatus.FAILED
    assert result.output is None
    assert result.checkpoint is None
    assert result.error is not None
    assert result.error["code"] == "WORKFLOW_EXECUTION_ERROR"
    assert result.error["error_type"] == "RuntimeError"
    assert result.error["run_id"] == "run-fail"
    assert "boom" in result.error["message"]


@pytest.mark.asyncio
async def test_execute_propagates_runtime_errors_unchanged() -> None:
    factory, _calls = _double_factory(
        run_error=AgentRuntimeError("policy denied", code="POLICY_DENIED")
    )
    engine = _engine(create_workflow_fn=factory)

    with pytest.raises(AgentRuntimeError) as exc_info:
        await engine.execute("demo", {}, _ctx())

    assert exc_info.value.code == "POLICY_DENIED"


@pytest.mark.asyncio
async def test_execute_interrupted_run_persists_tenant_scoped_checkpoint() -> None:
    factory, _calls = _double_factory(terminal_status=WorkflowStatus.INTERRUPTED)
    port = InMemoryCheckpointAdapter()
    engine = _engine(checkpoint_port=port, create_workflow_fn=factory)
    ctx = _ctx(run_id="run-paused")

    result = await engine.execute("demo", {"prospect_id": "acme"}, ctx)

    assert result.status == RunStatus.PAUSED
    assert result.error is None
    assert result.checkpoint is not None
    checkpoint = result.checkpoint
    assert checkpoint.run_id == "run-paused"
    assert checkpoint.thread_id == "run-paused"
    assert checkpoint.tenant_id == "tenant-a"
    assert len(checkpoint.state_hash) == 64
    assert checkpoint.metadata == {
        "workflow_type": "demo",
        "status": "paused",
        "current_node": "end",
    }

    checkpoints = await port.list("run-paused", "tenant-a")
    assert len(checkpoints) == 1
    assert checkpoints[0].checkpoint_id == checkpoint.checkpoint_id

    loaded = await port.load("run-paused", "run-paused", "tenant-a")
    assert loaded is not None
    _loaded_checkpoint, payload = loaded
    assert payload["tenant_id"] == "tenant-a"
    assert payload["workflow_type"] == "roi_calculator"
    assert payload["status"] == "interrupted"


@pytest.mark.asyncio
async def test_resume_round_trip_with_matching_checkpoint() -> None:
    factory_a, _calls_a = _double_factory(terminal_status=WorkflowStatus.INTERRUPTED)
    port = InMemoryCheckpointAdapter()
    engine_a = _engine(checkpoint_port=port, create_workflow_fn=factory_a)
    ctx = _ctx(run_id="run-resume")

    executed = await engine_a.execute("demo", {"prospect_id": "acme"}, ctx)
    assert executed.status == RunStatus.PAUSED
    assert executed.checkpoint is not None
    checkpoint = executed.checkpoint

    factory_b, calls_b = _double_factory()
    engine_b = _engine(checkpoint_port=port, create_workflow_fn=factory_b)
    resume_request = ResumeRequest(
        resume_data={"approved": True},
        checkpoint_id=checkpoint.checkpoint_id,
        checkpoint_hash=checkpoint.state_hash,
    )

    resumed = await engine_b.resume("demo", ctx.run_id, resume_request, ctx)

    assert resumed.status == RunStatus.COMPLETED
    assert resumed.error is None
    assert resumed.checkpoint is None
    assert resumed.output is not None
    assert resumed.output["resume_decision"] == {"approved": True}

    assert len(calls_b) == 1
    call = calls_b[0]
    assert call["thread_id"] == "run-resume"
    assert call["resume_data"] == {"approved": True}
    # The snapshot was re-hydrated back to the interrupted (resumable) status.
    assert call["state_status"] == WorkflowStatus.INTERRUPTED


@pytest.mark.asyncio
async def test_resume_unknown_run_raises_run_not_found() -> None:
    factory, _calls = _double_factory()
    engine = _engine(checkpoint_port=InMemoryCheckpointAdapter(), create_workflow_fn=factory)

    with pytest.raises(RunNotFoundError) as exc_info:
        await engine.resume("demo", "run-missing", ResumeRequest(resume_data={}), _ctx())

    assert exc_info.value.code == "RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_resume_cross_tenant_lookup_fails_closed() -> None:
    factory_a, _calls_a = _double_factory(terminal_status=WorkflowStatus.INTERRUPTED)
    port = InMemoryCheckpointAdapter()
    engine_a = _engine(checkpoint_port=port, create_workflow_fn=factory_a)
    ctx_a = _ctx(tenant_id="tenant-a", run_id="run-shared")

    executed = await engine_a.execute("demo", {"prospect_id": "acme"}, ctx_a)
    assert executed.status == RunStatus.PAUSED

    # Tenant B must not be able to see or resume tenant A's run.
    factory_b, _calls_b = _double_factory()
    engine_b = _engine(checkpoint_port=port, create_workflow_fn=factory_b)
    ctx_b = _ctx(tenant_id="tenant-b", run_id="run-shared")

    with pytest.raises(RunNotFoundError) as exc_info:
        await engine_b.resume("demo", "run-shared", ResumeRequest(resume_data={}), ctx_b)

    assert exc_info.value.code == "RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_resume_requires_a_configured_checkpoint_store() -> None:
    factory, _calls = _double_factory()
    engine = _engine(checkpoint_port=None, create_workflow_fn=factory)

    with pytest.raises(AgentRuntimeError) as exc_info:
        await engine.resume("demo", "run-1", ResumeRequest(resume_data={}), _ctx())

    assert exc_info.value.code == "RESUME_UNAVAILABLE"


@pytest.mark.asyncio
async def test_resume_stale_checkpoint_id_conflict_is_rejected() -> None:
    factory_a, _calls_a = _double_factory(terminal_status=WorkflowStatus.INTERRUPTED)
    port = InMemoryCheckpointAdapter()
    engine_a = _engine(checkpoint_port=port, create_workflow_fn=factory_a)
    ctx = _ctx(run_id="run-stale-id")

    executed = await engine_a.execute("demo", {}, ctx)
    assert executed.checkpoint is not None

    factory_b, _calls_b = _double_factory()
    engine_b = _engine(checkpoint_port=port, create_workflow_fn=factory_b)
    request = ResumeRequest(resume_data={}, checkpoint_id="stale-checkpoint-id")

    with pytest.raises(CheckpointConflictError) as exc_info:
        await engine_b.resume("demo", ctx.run_id, request, ctx)

    assert exc_info.value.code == "CHECKPOINT_CONFLICT"


@pytest.mark.asyncio
async def test_resume_stale_checkpoint_hash_conflict_is_rejected() -> None:
    factory_a, _calls_a = _double_factory(terminal_status=WorkflowStatus.INTERRUPTED)
    port = InMemoryCheckpointAdapter()
    engine_a = _engine(checkpoint_port=port, create_workflow_fn=factory_a)
    ctx = _ctx(run_id="run-stale-hash")

    executed = await engine_a.execute("demo", {}, ctx)
    assert executed.checkpoint is not None

    factory_b, _calls_b = _double_factory()
    engine_b = _engine(checkpoint_port=port, create_workflow_fn=factory_b)
    request = ResumeRequest(resume_data={}, checkpoint_hash="00" * 32)

    with pytest.raises(CheckpointConflictError) as exc_info:
        await engine_b.resume("demo", ctx.run_id, request, ctx)

    assert exc_info.value.code == "CHECKPOINT_CONFLICT"


@pytest.mark.asyncio
async def test_resume_non_resumable_snapshot_is_denied() -> None:
    port = InMemoryCheckpointAdapter()
    completed_state = BaseAgentState(
        tenant_id="tenant-a",
        workflow_id="wf-nr",
        run_id="run-nr",
        trace_id="trace-nr",
        workflow_type=WorkflowType.ROI_CALCULATOR,
        status=WorkflowStatus.COMPLETED,
        input_data={"x": 1},
        output_data={"done": True},
    )
    checkpoint = Checkpoint(
        checkpoint_id="run-nr:state:cccccccc",
        run_id="run-nr",
        thread_id="thread-nr",
        tenant_id="tenant-a",
        state_hash="cc" * 32,
    )
    await port.save(checkpoint, completed_state.model_dump(mode="python"))

    factory, calls = _double_factory()
    engine = _engine(checkpoint_port=port, create_workflow_fn=factory)

    with pytest.raises(AgentRuntimeError) as exc_info:
        await engine.resume(
            "demo", "run-nr", ResumeRequest(resume_data={"approved": True}), _ctx()
        )

    assert exc_info.value.code == "RUN_NOT_RESUMABLE"
    assert calls == []


@pytest.mark.asyncio
async def test_resume_reports_structured_state_reconstruction_failure() -> None:
    port = InMemoryCheckpointAdapter()
    # Snapshot missing the required tenant_id field -> reconstruction must fail closed.
    checkpoint = Checkpoint(
        checkpoint_id="run-poison:state:dddddddd",
        run_id="run-poison",
        thread_id="thread-poison",
        tenant_id="tenant-a",
        state_hash="dd" * 32,
    )
    await port.save(checkpoint, {"workflow_type": "roi_calculator"})

    factory, calls = _double_factory()
    engine = _engine(checkpoint_port=port, create_workflow_fn=factory)

    with pytest.raises(AgentRuntimeError) as exc_info:
        await engine.resume(
            "demo", "run-poison", ResumeRequest(resume_data={}), _ctx()
        )

    assert exc_info.value.code == "STATE_RECONSTRUCTION_FAILED"
    assert exc_info.value.details["run_id"] == "run-poison"
    assert calls == []


class _InterruptApprovalWorkflow(BaseWorkflow):
    """Real workflow that interrupts once for human-in-the-loop approval.

    Mirrors the canonical restart-test pattern: the second tool node raises
    ``interrupt()`` so LangGraph persists a resumable checkpoint.
    """

    def __init__(self, tool_registry: Any, checkpoint_saver: Any = None) -> None:
        config = WorkflowConfig(
            workflow_type="roi_calculator",
            name="Interrupt Approval Workflow",
            description="Interrupts once for human-in-the-loop approval",
            nodes=[
                NodeConfig(id="start", name="Start", node_type=NodeType.TOOL, tool_name="test_tool"),
                NodeConfig(id="middle", name="Middle", node_type=NodeType.TOOL, tool_name="test_tool"),
                NodeConfig(id="end", name="End", node_type=NodeType.END),
            ],
            edges=[
                EdgeConfig(source="start", target="middle"),
                EdgeConfig(source="middle", target="end"),
            ],
            entry_point="start",
        )
        super().__init__(config, tool_registry, checkpoint_saver)
        self.executed_nodes: list[str] = []

    async def _execute_tool(self, tool_name: str, state: Any, config: dict) -> dict[str, Any]:
        current_node = state.current_node
        self.executed_nodes.append(current_node)
        if len(self.executed_nodes) == 2:
            interrupt("Approval required")
        return {"result": "ok", "node": current_node, "tool": tool_name}

    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> BaseAgentState:
        return BaseAgentState(
            tenant_id=tenant_id or "tenant-a",
            run_id=run_id or "run-1",
            trace_id=trace_id or "trace-1",
            workflow_id=workflow_id or "approval-wf",
            workflow_type=WorkflowType.ROI_CALCULATOR,
            status=WorkflowStatus.PENDING,
            input_data=dict(input_data or {}),
            output_data={},
            errors=[],
        )


@pytest.mark.asyncio
async def test_execute_then_resume_with_real_langgraph_interrupt() -> None:
    """A genuine LangGraph interrupt is persisted and resumes to completion."""
    saver = InMemorySaver()
    port = InMemoryCheckpointAdapter()

    def factory(workflow_type: str, tool_registry: Any, checkpoint_saver: Any = None) -> _InterruptApprovalWorkflow:
        return _InterruptApprovalWorkflow(tool_registry, checkpoint_saver)

    engine_1 = _engine(
        checkpoint_port=port,
        checkpoint_saver=saver,
        workflow_types={"approval_demo"},
        create_workflow_fn=factory,
    )
    ctx = _ctx(run_id="run-live-1", workflow_id="wf-live-1")

    executed = await engine_1.execute("approval_demo", {"ask": "approve"}, ctx)

    assert executed.status == RunStatus.PAUSED
    assert executed.error is None
    assert executed.checkpoint is not None
    checkpoint = executed.checkpoint
    assert checkpoint.run_id == "run-live-1"
    assert checkpoint.thread_id == "run-live-1"

    # A new engine/adapter instance sharing the saver + checkpoint port simulates
    # resuming after a pod restart.
    engine_2 = _engine(
        checkpoint_port=port,
        checkpoint_saver=saver,
        workflow_types={"approval_demo"},
        create_workflow_fn=factory,
    )
    resumed = await engine_2.resume(
        "approval_demo",
        ctx.run_id,
        ResumeRequest(
            resume_data={"approved": True},
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_hash=checkpoint.state_hash,
        ),
        ctx,
    )

    assert resumed.status == RunStatus.COMPLETED
    assert resumed.error is None
    assert resumed.checkpoint is None
    assert resumed.output is not None
