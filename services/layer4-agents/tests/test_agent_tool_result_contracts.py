from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    set_current_context,
)

import layer4_agents.tools.registry as registry_module
from layer4_agents.models.tool_schemas import ToolCategory
from layer4_agents.tools.registry import BaseTool, ToolRegistry, ToolResult


class EchoInput(BaseModel):
    value: int
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str | None = None


class EchoTool(BaseTool):
    name = "agent_echo_contract"
    category = ToolCategory.UTILITY
    description = "Echoes validated input for contract tests."
    input_schema = EchoInput
    output_schema = BaseModel

    async def execute(self, input_data: EchoInput) -> dict[str, Any]:
        return {"value": input_data.value, "tenant_id": input_data.tenant_id}


class ExplodingInput(BaseModel):
    value: str
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str | None = None
    api_key: str | None = None


class ExplodingTool(BaseTool):
    name = "agent_exploding_contract"
    category = ToolCategory.UTILITY
    description = "Raises with a secret-bearing message to prove safe error wrapping."
    input_schema = ExplodingInput
    output_schema = BaseModel

    async def execute(self, input_data: ExplodingInput) -> dict[str, Any]:
        raise RuntimeError(f"upstream leaked secret {input_data.api_key} for tenant-b")


class SlowInput(BaseModel):
    value: str
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str | None = None


class SlowTool(BaseTool):
    name = "agent_slow_contract"
    category = ToolCategory.UTILITY
    description = "Sleeps long enough to trigger BaseTool timeout handling."
    input_schema = SlowInput
    output_schema = BaseModel
    timeout_seconds = 0.01

    async def execute(self, input_data: SlowInput) -> dict[str, Any]:
        await asyncio.sleep(1)
        return {"value": input_data.value}


class MutatingInput(BaseModel):
    value: int
    idempotency_key: str | None = None
    tenant_id: str | None = None
    approval_decision: str | None = None
    workflow_id: str | None = None


class MutatingTool(BaseTool):
    name = "agent_mutating_contract"
    category = ToolCategory.INTEGRATION
    description = "Simulates irreversible side effect."
    input_schema = MutatingInput
    output_schema = BaseModel

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.calls = 0

    async def execute(self, input_data: MutatingInput) -> dict[str, Any]:
        self.calls += 1
        return {"calls": self.calls, "value": input_data.value}


@pytest.mark.asyncio
async def test_agent_tool_success_returns_structured_result() -> None:
    result = await EchoTool(config={"tenant_id": "tenant-a"}).run(
        {"value": 42, "request_id": "req-tool", "trace_id": "trace-tool"}
    )

    assert isinstance(result, ToolResult)
    assert result.status == "success"
    assert result.error is None
    assert result.data == {"value": 42, "tenant_id": None}
    assert result.metadata["trace_id"] == "trace-tool"
    assert result.metadata["request_id"] == "req-tool"
    assert result.metadata["tenant_id"] == "tenant-a"
    assert "execution_time_ms" in result.metadata


@pytest.mark.asyncio
async def test_agent_tool_exception_returns_structured_error_result() -> None:
    result = await ExplodingTool(config={"tenant_id": "tenant-a"}).run(
        {
            "value": "explode",
            "api_key": "super-secret-api-key",
            "request_id": "req-error",
            "trace_id": "trace-error",
        }
    )

    assert result.status == "error"
    assert result.data is None
    assert result.error["code"] == "TOOL_EXECUTION_ERROR"
    assert result.error["recoverable"] is False
    assert result.error["message"] == "Tool 'agent_exploding_contract' execution failed"
    assert result.metadata["trace_id"] == "trace-error"
    assert result.metadata["request_id"] == "req-error"
    assert result.metadata["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_agent_tool_error_does_not_leak_secret_values_or_cross_tenant_data() -> None:
    result = await ExplodingTool(config={"tenant_id": "tenant-a"}).run(
        {
            "value": "explode",
            "api_key": "super-secret-api-key",
            "tenant_id": "tenant-b",
            "request_id": "req-secret",
            "trace_id": "trace-secret",
        }
    )

    dumped = result.model_dump_json()
    assert "super-secret-api-key" not in dumped
    assert "tenant-b" not in dumped
    assert "upstream leaked secret" not in dumped
    assert result.metadata["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_agent_tool_validation_error_redacts_sensitive_input_keys() -> None:
    result = await EchoTool(config={"tenant_id": "tenant-a"}).run(
        {
            "value": "not-an-int",
            "api_key": "super-secret-api-key",
            "password": "secret-password",
            "request_id": "req-validation",
            "trace_id": "trace-validation",
        }
    )

    assert result.status == "error"
    assert result.error["code"] == "INPUT_VALIDATION_ERROR"
    input_keys = result.error["details"]["input_keys"]
    assert "value" in input_keys
    assert "request_id" in input_keys
    assert "[redacted]" in input_keys
    dumped = result.model_dump_json()
    assert "api_key" not in dumped
    assert "password" not in dumped
    assert "super-secret-api-key" not in dumped
    assert "secret-password" not in dumped


@pytest.mark.asyncio
async def test_agent_tool_result_preserves_request_context() -> None:
    result = await EchoTool(config={"tenant_id": "tenant-a"}).run(
        {"value": 7, "request_id": "req-preserve", "trace_id": "trace-preserve"}
    )

    assert result.metadata["trace_id"] == "trace-preserve"
    assert result.metadata["request_id"] == "req-preserve"
    assert result.metadata["tenant_id"] == "tenant-a"
    assert result.data["value"] == 7


@pytest.mark.asyncio
async def test_agent_tool_timeout_returns_structured_degraded_response() -> None:
    result = await SlowTool(config={"tenant_id": "tenant-a"}).run(
        {"value": "slow", "request_id": "req-timeout", "trace_id": "trace-timeout"}
    )

    assert result.status == "error"
    assert result.data is None
    assert result.error["code"] == "TOOL_TIMEOUT"
    assert result.error["recoverable"] is True
    assert "timed out" in result.error["message"]
    assert result.metadata["trace_id"] == "trace-timeout"
    assert result.metadata["request_id"] == "req-timeout"
    assert result.metadata["tenant_id"] == "tenant-a"
    assert result.metadata["execution_time_ms"] >= 0


@pytest.mark.asyncio
async def test_agent_tool_execution_creates_audit_event(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_events: list[dict[str, Any]] = []
    created_tasks: list[asyncio.Task[Any]] = []

    async def capture_emit(**kwargs: Any) -> None:
        captured_events.append(kwargs)

    original_create_task = asyncio.create_task

    def capture_task(coro: Any) -> asyncio.Task[Any]:
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setenv("AUDIT_LEDGER_MODE", "enabled")
    monkeypatch.setattr("value_fabric.shared.audit.emitter.emit_audit_event", capture_emit)
    monkeypatch.setattr(registry_module.asyncio, "create_task", capture_task)

    tool = EchoTool(config={"tenant_id": "12345678-1234-1234-1234-123456789abc"})
    registry = ToolRegistry()
    registry.register(tool)

    result = await registry.execute(
        tool.name,
        {"value": 9, "request_id": "req-audit", "trace_id": "trace-audit"},
    )
    if created_tasks:
        await asyncio.gather(*created_tasks)

    assert result.status == "success"
    assert len(captured_events) == 1
    event = captured_events[0]
    assert event["resource_type"] == "tool"
    assert event["resource_id"] == tool.name
    assert str(event["tenant_id"]) == "12345678-1234-1234-1234-123456789abc"
    assert event["request_id"] == "trace-audit"
    assert event["details"]["tool_name"] == tool.name
    assert event["details"]["request_hash"]
    assert event["details"]["response_hash"]
    assert event["details"]["trace_id"] == "trace-audit"


@pytest.mark.asyncio
async def test_registry_rejects_raw_tenant_without_request_or_workflow_context() -> None:
    clear_current_context()
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)

    result = await registry.execute(
        tool.name,
        {"value": 1, "tenant_id": "12345678-1234-1234-1234-123456789abc"},
    )

    assert result.status == "error"
    assert result.error["code"] == "TENANT_CONTEXT_UNTRUSTED"


@pytest.mark.asyncio
async def test_registry_accepts_valid_internal_workflow_tenant_context() -> None:
    clear_current_context()
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)

    result = await registry.execute(
        tool.name,
        {
            "value": 1,
            "tenant_id": "12345678-1234-1234-1234-123456789abc",
            "workflow_id": "wf-1",
            "run_id": "run-1",
            "trace_id": "trace-1",
        },
    )

    assert result.status == "success"
    assert result.metadata["tenant_id"] == "12345678-1234-1234-1234-123456789abc"
    assert clear_current_context() is None


@pytest.mark.asyncio
async def test_registry_request_context_overrides_and_rejects_spoofed_tenant() -> None:
    clear_current_context()
    set_current_context(
        RequestContext(
            tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
            user_id="user-1",
        )
    )
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)

    result = await registry.execute(
        tool.name,
        {
            "value": 1,
            "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "workflow_id": "wf-1",
            "run_id": "run-1",
            "trace_id": "trace-1",
        },
    )

    assert result.status == "error"
    assert result.error["code"] == "TENANT_CONTEXT_MISMATCH"
    clear_current_context()


@pytest.mark.asyncio
async def test_agent_failed_tool_execution_creates_audit_event(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_events: list[dict[str, Any]] = []
    created_tasks: list[asyncio.Task[Any]] = []

    async def capture_emit(**kwargs: Any) -> None:
        captured_events.append(kwargs)

    original_create_task = asyncio.create_task

    def capture_task(coro: Any) -> asyncio.Task[Any]:
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setenv("AUDIT_LEDGER_MODE", "enabled")
    monkeypatch.setattr("value_fabric.shared.audit.emitter.emit_audit_event", capture_emit)
    monkeypatch.setattr(registry_module.asyncio, "create_task", capture_task)

    tool = ExplodingTool(config={"tenant_id": "12345678-1234-1234-1234-123456789abc"})
    registry = ToolRegistry()
    registry.register(tool)

    result = await registry.execute(
        tool.name,
        {
            "value": "explode",
            "api_key": "super-secret-api-key",
            "request_id": "req-failed-audit",
            "trace_id": "trace-failed-audit",
        },
    )
    if created_tasks:
        await asyncio.gather(*created_tasks)

    assert result.status == "error"
    assert len(captured_events) == 1
    event = captured_events[0]
    assert event["resource_id"] == tool.name
    assert event["request_id"] == "trace-failed-audit"
    assert event["details"]["tool_name"] == tool.name
    assert event["details"]["trace_id"] == "trace-failed-audit"
    assert event["details"]["response_hash"]


@pytest.mark.asyncio
async def test_retry_with_same_idempotency_key_executes_side_effect_once() -> None:
    clear_current_context()
    set_current_context(RequestContext(tenant_id=UUID("12345678-1234-1234-1234-123456789abc"), user_id="user-1"))
    registry = ToolRegistry()
    tool = MutatingTool(config={"tenant_id": "12345678-1234-1234-1234-123456789abc"})
    registry.register(tool)

    first = await registry.execute(
        tool.name,
        {"value": 10, "idempotency_key": "idem-1", "approval_decision": "approved", "workflow_id": "wf-1"},
    )
    second = await registry.execute(
        tool.name,
        {"value": 10, "idempotency_key": "idem-1", "approval_decision": "approved", "workflow_id": "wf-1"},
    )

    assert first.status == "success"
    assert second.status == "success"
    assert tool.calls == 1
    assert first.data == second.data
    clear_current_context()


@pytest.mark.asyncio
async def test_irreversible_tool_requires_approval_and_idempotency_key() -> None:
    clear_current_context()
    set_current_context(RequestContext(tenant_id=UUID("12345678-1234-1234-1234-123456789abc"), user_id="user-1"))
    registry = ToolRegistry()
    tool = MutatingTool(config={"tenant_id": "12345678-1234-1234-1234-123456789abc"})
    registry.register(tool)

    missing_idem = await registry.execute(tool.name, {"value": 10, "approval_decision": "approved"})
    denied = await registry.execute(tool.name, {"value": 10, "idempotency_key": "idem-2"})

    assert missing_idem.status == "error"
    assert missing_idem.error["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert denied.status == "error"
    assert denied.error["code"] == "APPROVAL_REQUIRED"
    assert tool.calls == 0
    clear_current_context()
