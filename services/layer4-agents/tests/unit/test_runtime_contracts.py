"""Phase 0 contract tests for the Agent Runtime: schema round-trip and port conformance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from layer4_agents.runtime import (
    AgentRuntimeImpl,
    AuthzDecision,
    ResumeRequest,
    RunRequest,
    RunStatus,
    RuntimeContext,
    TenantRequiredError,
    ToolDef,
    ToolRegistryUnavailableError,
    ToolResult,
    ToolSchema,
    WorkflowResult,
    WorkflowTypeNotFoundError,
)
from layer4_agents.runtime.ports import AgentRuntime, AuthzPort, ToolRegistryPort

# File lives at services/layer4-agents/tests/unit/ → repo root is 4 levels up.
REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "contracts" / "jsonschema" / "agent-runtime" / "common.json"


def _def_validator(name: str) -> jsonschema.Draft202012Validator:
    """Validate an instance against one ``$def`` while keeping sibling ``$defs`` resolvable."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    # Root $ref into the target def; sibling $defs remain in scope for internal refs.
    schema["$ref"] = f"#/$defs/{name}"
    return jsonschema.Draft202012Validator(schema)


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


@pytest.mark.unit
def test_runtime_context_round_trips_against_json_schema() -> None:
    ctx = _ctx()
    instance = json.loads(ctx.model_dump_json())

    errors = list(_def_validator("RuntimeContext").iter_errors(instance))
    assert not errors, [e.message for e in errors]


@pytest.mark.unit
@pytest.mark.parametrize(
    "field", ["tenant_id", "trace_id", "run_id", "workflow_id", "workflow_type"]
)
def test_runtime_context_rejects_empty_required_fields(field: str) -> None:
    """The Pydantic model enforces the JSON Schema's minLength: 1 contract."""
    from pydantic import ValidationError

    valid = {
        "tenant_id": "tenant-a",
        "trace_id": "trace-1",
        "run_id": "run-1",
        "workflow_id": "wf-1",
        "workflow_type": "demo",
    }

    with pytest.raises(ValidationError):
        RuntimeContext(**{**valid, field: ""})


@pytest.mark.unit
def test_run_request_round_trips_against_json_schema() -> None:
    request = RunRequest(workflow_type="roi_calculator", input_data={"prospect_id": "123"})
    instance = json.loads(request.model_dump_json())

    errors = list(_def_validator("RunRequest").iter_errors(instance))
    assert not errors, [e.message for e in errors]


@pytest.mark.unit
def test_tool_result_round_trips_against_json_schema() -> None:
    result = ToolResult(status="success", data={"value": 1})
    instance = json.loads(result.model_dump_json())

    errors = list(_def_validator("ToolResult").iter_errors(instance))
    assert not errors, [e.message for e in errors]


class _StubToolRegistry:
    """Minimal ToolRegistryPort conformance stub."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSchema] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = ToolSchema(
            name=tool.name,
            description=tool.description,
            category=tool.category,
            tenant_scoped=tool.tenant_scoped,
            parameters=tool.parameters,
            required=tool.required,
            version=tool.version,
        )

    def get_schema(self, name: str, tenant_id: str) -> ToolSchema | None:
        return self._tools.get(name)

    def list_tools(self, tenant_id: str) -> list[ToolSchema]:
        return list(self._tools.values())

    async def execute(self, name: str, arguments: dict[str, Any], ctx: RuntimeContext) -> ToolResult:
        return ToolResult(status="success", data={"echo": arguments})


class _StubAuthz:
    """Minimal AuthzPort conformance stub that denies a specific tool."""

    def __init__(self, deny: set[str] | None = None) -> None:
        self._deny = deny or set()

    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        if tool_name in self._deny:
            return AuthzDecision(allowed=False, reason="policy denied")
        return AuthzDecision(allowed=True)


@pytest.mark.unit
def test_tool_registry_and_authz_stubs_satisfy_ports() -> None:
    registry = _StubToolRegistry()
    authz = _StubAuthz()

    assert isinstance(registry, ToolRegistryPort)
    assert isinstance(authz, AuthzPort)


@pytest.mark.unit
def test_agent_runtime_impl_satisfies_agent_runtime_port() -> None:
    runtime = AgentRuntimeImpl()

    assert isinstance(runtime, AgentRuntime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_run_fails_closed_without_tenant_id() -> None:
    runtime = AgentRuntimeImpl()
    request = RunRequest(workflow_type="demo")
    # Validation rejects empty tenant_id; the runtime guard must still fail
    # closed for an unvalidated context (model_construct) — defense in depth.
    ctx = RuntimeContext.model_construct(
        tenant_id="", trace_id="trace-1", run_id="run-1", workflow_id="wf-1", workflow_type="demo"
    )

    with pytest.raises(TenantRequiredError):
        await runtime.submit_run(request, ctx)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_run_with_unknown_workflow_type_raises_not_found() -> None:
    runtime = AgentRuntimeImpl()
    request = RunRequest(workflow_type="unregistered_type")
    ctx = _ctx(workflow_type="unregistered_type")

    with pytest.raises(WorkflowTypeNotFoundError):
        await runtime.submit_run(request, ctx)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_run_dispatches_to_registered_factory_and_persists_result() -> None:
    runtime = AgentRuntimeImpl()

    async def factory(workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext) -> WorkflowResult:
        return WorkflowResult(status=RunStatus.COMPLETED, output={"ok": True})

    runtime.register_workflow_type("demo", factory)
    request = RunRequest(workflow_type="demo")
    ctx = _ctx()

    envelope = await runtime.submit_run(request, ctx)
    result = await runtime.get_run(envelope.run_id, ctx.tenant_id)

    assert result is not None
    assert result.status == RunStatus.COMPLETED
    assert result.output == {"ok": True}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_denies_cross_tenant_lookup() -> None:
    runtime = AgentRuntimeImpl()

    async def factory(workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext) -> WorkflowResult:
        return WorkflowResult(status=RunStatus.COMPLETED)

    runtime.register_workflow_type("demo", factory)
    request = RunRequest(workflow_type="demo")
    ctx = _ctx(tenant_id="tenant-a")

    envelope = await runtime.submit_run(request, ctx)

    assert await runtime.get_run(envelope.run_id, "tenant-b") is None
    assert await runtime.get_run(envelope.run_id, "tenant-a") is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_tool_denies_forbidden_tool_via_authz_port() -> None:
    from layer4_agents.runtime import ToolForbiddenError

    registry = _StubToolRegistry()
    authz = _StubAuthz(deny={"restricted_tool"})
    runtime = AgentRuntimeImpl(tool_registry=registry, authz=authz)
    ctx = _ctx()

    with pytest.raises(ToolForbiddenError):
        await runtime.call_tool("restricted_tool", {}, ctx)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_tool_executes_allowed_tool() -> None:
    registry = _StubToolRegistry()
    authz = _StubAuthz()
    runtime = AgentRuntimeImpl(tool_registry=registry, authz=authz)
    ctx = _ctx()

    result = await runtime.call_tool("allowed_tool", {"x": 1}, ctx)

    assert result.status == "success"
    assert result.data == {"echo": {"x": 1}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_tool_without_registry_raises_tool_registry_unavailable() -> None:
    runtime = AgentRuntimeImpl()
    ctx = _ctx()

    with pytest.raises(ToolRegistryUnavailableError) as exc_info:
        await runtime.call_tool("echo", {}, ctx)

    assert exc_info.value.code == "TOOL_REGISTRY_UNAVAILABLE"
    assert exc_info.value.details["tool_name"] == "echo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_runs_filters_by_tenant_and_status() -> None:
    runtime = AgentRuntimeImpl()

    async def factory(workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext) -> WorkflowResult:
        return WorkflowResult(status=RunStatus.COMPLETED)

    runtime.register_workflow_type("demo", factory)

    ctx_a = _ctx(tenant_id="tenant-a", run_id="run-a")
    ctx_b = _ctx(tenant_id="tenant-b", run_id="run-b")
    await runtime.submit_run(RunRequest(workflow_type="demo"), ctx_a)
    await runtime.submit_run(RunRequest(workflow_type="demo"), ctx_b)

    tenant_a_runs = await runtime.list_runs("tenant-a")

    assert len(tenant_a_runs) == 1
    assert all(r.status == RunStatus.COMPLETED for r in tenant_a_runs)


@pytest.mark.unit
def test_resume_request_round_trips_against_json_schema() -> None:
    resume = ResumeRequest(resume_data={"answer": "yes"}, checkpoint_id="cp-1")
    instance = json.loads(resume.model_dump_json())

    errors = list(_def_validator("ResumeRequest").iter_errors(instance))
    assert not errors, [e.message for e in errors]


@pytest.mark.unit
def test_json_schema_required_arrays_match_pydantic_models() -> None:
    """Every object def in common.json must require exactly the fields its Pydantic model does.

    Guards against `required`-array drift: a def that over-requires a field with
    a Pydantic default (or under-requires one without) breaks round-trip parity.
    """
    from pydantic import BaseModel

    from layer4_agents.runtime import models as runtime_models

    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    defs = schema["$defs"]
    checked: list[str] = []

    for name, definition in defs.items():
        if definition.get("type") != "object":
            continue  # enums and non-object defs have no required-array contract
        model = getattr(runtime_models, name, None)
        if not isinstance(model, type) or not issubclass(model, BaseModel):
            continue  # defs without a same-named Pydantic model are out of scope here
        schema_required = set(definition.get("required", []))
        model_required = {n for n, f in model.model_fields.items() if f.is_required()}
        assert schema_required == model_required, (
            f"$defs.{name} required drift: schema={sorted(schema_required)} "
            f"model={sorted(model_required)}"
        )
        checked.append(name)

    assert len(checked) >= 10, f"parity check collapsed to {len(checked)} defs: {checked}"
