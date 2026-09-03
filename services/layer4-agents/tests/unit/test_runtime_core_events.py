"""Phase 5 emission-wiring tests for AgentRuntimeImpl lifecycle events.

Covers the observability events the runtime core publishes through a
configured ``EventSink``: RUN_STARTED + terminal status event on submit, the
FAILED-zombie record + RUN_FAILED event on dispatch failure, RUN_RESUMED on
resume, RUN_CANCELLED on cancel, and TOOL_CALLED / TOOL_DENIED around tool
execution.
"""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    AgentRuntimeError,
    AgentRuntimeImpl,
    AuthzDecision,
    ResumeRequest,
    RunRequest,
    RunStatus,
    RuntimeContext,
    RuntimeEvent,
    ToolForbiddenError,
    ToolResult,
    WorkflowResult,
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


class _RecordingSink:
    """EventSink recording every published event in order."""

    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    async def publish(self, event: RuntimeEvent) -> None:
        self.events.append(event)


class _EngineDouble:
    """WorkflowEnginePort double whose execute/resume results are scripted."""

    def __init__(
        self,
        *,
        execute_result: WorkflowResult | None = None,
        resume_result: WorkflowResult | None = None,
        execute_error: AgentRuntimeError | None = None,
    ) -> None:
        self._execute_result = execute_result or WorkflowResult(status=RunStatus.PAUSED)
        self._resume_result = resume_result or WorkflowResult(
            status=RunStatus.COMPLETED, output={"done": True}
        )
        self._execute_error = execute_error
        self.execute_calls = 0
        self.resume_calls = 0

    def get_supported_types(self) -> set[str]:
        return {"demo"}

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Any | None = None,
    ) -> WorkflowResult:
        self.execute_calls += 1
        if self._execute_error is not None:
            raise self._execute_error
        return self._execute_result

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        self.resume_calls += 1
        return self._resume_result


def _kinds(events: list[RuntimeEvent]) -> list[str]:
    return [e.kind for e in events]


async def test_submit_run_emits_run_started_then_completed() -> None:
    engine = _EngineDouble(
        execute_result=WorkflowResult(status=RunStatus.COMPLETED, output={"ok": True})
    )
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)
    ctx = _ctx()

    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)

    assert _kinds(sink.events) == ["run.started", "run.completed"]
    started = sink.events[0]
    assert started.run_id == envelope.run_id
    assert started.tenant_id == "tenant-a"
    assert started.workflow_type == "demo"
    assert started.status == RunStatus.PENDING.value
    assert started.payload == {"workflow_id": envelope.workflow_id}
    completed = sink.events[1]
    assert completed.run_id == envelope.run_id
    assert completed.status == RunStatus.COMPLETED.value


async def test_submit_run_that_pauses_emits_run_paused_after_started() -> None:
    engine = _EngineDouble()  # default execute result is PAUSED
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)

    await runtime.submit_run(RunRequest(workflow_type="demo"), _ctx())

    assert _kinds(sink.events) == ["run.started", "run.paused"]
    assert sink.events[1].status == RunStatus.PAUSED.value


async def test_submit_run_dispatch_failure_emits_failed_and_leaves_failed_record() -> None:
    engine = _EngineDouble(
        execute_error=AgentRuntimeError(
            "provider exploded", code="PROVIDER_CALL_FAILED", details={}
        )
    )
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)
    ctx = _ctx()

    with pytest.raises(AgentRuntimeError) as exc_info:
        await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)

    assert exc_info.value.code == "PROVIDER_CALL_FAILED"
    assert _kinds(sink.events) == ["run.started", "run.failed"]
    failed_event = sink.events[1]
    assert failed_event.status == RunStatus.FAILED.value
    assert failed_event.payload == {"error_code": "PROVIDER_CALL_FAILED"}
    # The dispatch failure must leave a terminal FAILED record (no zombie).
    run_id = failed_event.run_id
    assert run_id is not None
    stored = await runtime.get_run(run_id, "tenant-a")
    assert stored is not None and stored.status == RunStatus.FAILED
    assert stored.error == {
        "code": "PROVIDER_CALL_FAILED",
        "message": "provider exploded",
    }


async def test_resume_run_emits_resumed_then_terminal_status_event() -> None:
    engine = _EngineDouble()  # execute pauses; resume completes
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)
    ctx = _ctx()
    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)
    assert _kinds(sink.events) == ["run.started", "run.paused"]

    result = await runtime.resume_run(envelope.run_id, "tenant-a", ResumeRequest())

    assert result.status == RunStatus.COMPLETED
    assert _kinds(sink.events) == [
        "run.started",
        "run.paused",
        "run.resumed",
        "run.completed",
    ]
    resumed = sink.events[2]
    assert resumed.run_id == envelope.run_id
    assert resumed.status == RunStatus.COMPLETED.value


async def test_resume_run_emits_resumed_paused_when_still_resumable() -> None:
    engine = _EngineDouble(
        resume_result=WorkflowResult(status=RunStatus.PAUSED, output={"partial": True})
    )
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)
    ctx = _ctx()
    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), ctx)

    result = await runtime.resume_run(envelope.run_id, "tenant-a", ResumeRequest())

    assert result.status == RunStatus.PAUSED
    # After RUN_RESUMED, the stored paused status yields a RUN_PAUSED status event.
    assert _kinds(sink.events) == [
        "run.started",
        "run.paused",
        "run.resumed",
        "run.paused",
    ]


async def test_cancel_run_emits_cancelled_status_event() -> None:
    engine = _EngineDouble()  # execute pauses so the run is cancellable
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(workflow_engine=engine, event_bus=sink)
    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), _ctx())

    cancelled = await runtime.cancel_run(envelope.run_id, "tenant-a")

    assert cancelled.status == RunStatus.CANCELLED
    assert _kinds(sink.events) == ["run.started", "run.paused", "run.cancelled"]
    assert sink.events[-1].status == RunStatus.CANCELLED.value


class _AuthzAllowAll:
    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        return AuthzDecision(allowed=True)


class _AuthzDenyAll:
    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        return AuthzDecision(allowed=False, reason="policy denied")


class _EchoToolRegistry:
    """ToolRegistryPort conformance double echoing tool name/arguments."""

    def register(self, tool: Any) -> None:
        pass

    def get_schema(self, name: str, tenant_id: str) -> None:
        return None

    def list_tools(self, tenant_id: str) -> list[Any]:
        return []

    async def execute(
        self, name: str, arguments: dict[str, Any], ctx: RuntimeContext
    ) -> ToolResult:
        return ToolResult(status="success", data={"tool": name, "args": arguments})


async def test_call_tool_emits_tool_called_on_success() -> None:
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(
        tool_registry=_EchoToolRegistry(),
        authz=_AuthzAllowAll(),
        event_bus=sink,
    )
    ctx = _ctx(run_id="run-tool", workflow_type="roi")

    result = await runtime.call_tool("calculate_roi", {"prospect_id": "p1"}, ctx)

    assert result.status == "success"
    assert _kinds(sink.events) == ["tool.called"]
    called = sink.events[0]
    assert called.tool_name == "calculate_roi"
    assert called.tenant_id == "tenant-a"
    assert called.run_id == "run-tool"
    assert called.workflow_type == "roi"


async def test_call_tool_denied_emits_tool_denied_and_raises() -> None:
    sink = _RecordingSink()
    runtime = AgentRuntimeImpl(
        tool_registry=_EchoToolRegistry(),
        authz=_AuthzDenyAll(),
        event_bus=sink,
    )
    ctx = _ctx(run_id="run-tool")

    with pytest.raises(ToolForbiddenError) as exc_info:
        await runtime.call_tool("admin_delete", {}, ctx)

    assert exc_info.value.code == "TOOL_FORBIDDEN"
    assert _kinds(sink.events) == ["tool.denied"]
    denied = sink.events[0]
    assert denied.tool_name == "admin_delete"
    assert denied.tenant_id == "tenant-a"
    # No tool.called event may follow a denial.
    assert "tool.called" not in _kinds(sink.events)


async def test_without_event_bus_no_events_are_published() -> None:
    engine = _EngineDouble(
        execute_result=WorkflowResult(status=RunStatus.COMPLETED)
    )
    runtime = AgentRuntimeImpl(workflow_engine=engine)  # no event_bus

    envelope = await runtime.submit_run(RunRequest(workflow_type="demo"), _ctx())

    # Default runtime has no event bus; submit still works and stores the result.
    stored = await runtime.get_run(envelope.run_id, "tenant-a")
    assert stored is not None and stored.status == RunStatus.COMPLETED
