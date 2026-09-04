"""Phase 1 tests for Agent Runtime adapters: legacy registry bridge and policy authz."""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    AgentRuntimeError,
    AgentRuntimeImpl,
    AuthzDecision,
    RuntimeContext,
    ToolDef,
)
from layer4_agents.runtime.adapters import LegacyToolRegistryAdapter, PolicyAuthzPort
from layer4_agents.runtime.ports import AuthzPort, ToolRegistryPort
from layer4_agents.tools.calculation_tools import CalculateROITool


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


def _roi_tool_def(**overrides: Any) -> ToolDef:
    tool = CalculateROITool()
    return ToolDef(
        name="calculate_roi",
        description=tool.description,
        handler=tool,
        **overrides,
    )


@pytest.mark.unit
def test_adapters_satisfy_runtime_ports() -> None:
    registry = LegacyToolRegistryAdapter()
    authz = PolicyAuthzPort()

    assert isinstance(registry, ToolRegistryPort)
    assert isinstance(authz, AuthzPort)


@pytest.mark.unit
def test_register_and_get_schema_round_trips_calculate_roi() -> None:
    adapter = LegacyToolRegistryAdapter()

    adapter.register(_roi_tool_def())
    schema = adapter.get_schema("calculate_roi", "tenant-a")

    assert schema is not None
    assert schema.name == "calculate_roi"
    assert schema.category == "calculation"
    assert schema.tenant_scoped is False
    properties = schema.parameters.get("properties", {})
    assert {"investment", "returns", "time_periods", "discount_rate"} <= set(properties)
    assert "investment" in schema.required


@pytest.mark.unit
def test_register_rejects_handler_that_is_not_a_base_tool() -> None:
    adapter = LegacyToolRegistryAdapter()
    tool = ToolDef(name="not_a_tool", description="Invalid handler", handler="not-a-BaseTool")

    with pytest.raises(AgentRuntimeError) as exc_info:
        adapter.register(tool)

    assert exc_info.value.code == "INVALID_TOOL_HANDLER"
    assert exc_info.value.details["tool_name"] == "not_a_tool"
    assert exc_info.value.details["handler_type"] == "str"


@pytest.mark.unit
def test_register_duplicate_tool_raises_already_registered() -> None:
    adapter = LegacyToolRegistryAdapter()
    adapter.register(_roi_tool_def())

    with pytest.raises(AgentRuntimeError) as exc_info:
        adapter.register(_roi_tool_def())

    assert exc_info.value.code == "TOOL_ALREADY_REGISTERED"
    assert exc_info.value.details["tool_name"] == "calculate_roi"


@pytest.mark.unit
def test_get_schema_for_unregistered_tool_returns_none() -> None:
    adapter = LegacyToolRegistryAdapter()

    assert adapter.get_schema("missing_tool", "tenant-a") is None


@pytest.mark.unit
def test_list_tools_reports_registered_schema() -> None:
    adapter = LegacyToolRegistryAdapter()
    adapter.register(_roi_tool_def())

    schemas = adapter.list_tools("tenant-a")

    assert len(schemas) == 1
    assert schemas[0].name == "calculate_roi"
    assert schemas[0].tenant_scoped is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_ungated_tool_is_allowed() -> None:
    authz = PolicyAuthzPort()
    ctx = _ctx()

    decision: AuthzDecision = await authz.authorize_tool("calculate_roi", ctx)

    assert decision.allowed is True
    assert decision.reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_gated_tool_denies_without_grants() -> None:
    authz = PolicyAuthzPort()
    ctx = _ctx()

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is False
    assert decision.reason == "INSUFFICIENT_SCOPE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_gated_tool_allows_with_scope_grant() -> None:
    authz = PolicyAuthzPort()
    ctx = _ctx(metadata={"service_account_scopes": ["read:search"]})

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is True
    assert decision.reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_ignores_dict_scope_metadata_fail_closed() -> None:
    authz = PolicyAuthzPort()
    # A dict would iterate its keys; "read:search" must NOT become a grant.
    ctx = _ctx(metadata={"service_account_scopes": {"read:search": True}})

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is False
    assert decision.reason == "INSUFFICIENT_SCOPE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_ignores_string_scope_metadata_fail_closed() -> None:
    authz = PolicyAuthzPort()
    # A str would iterate its characters; the raw string must NOT become a grant.
    ctx = _ctx(metadata={"service_account_scopes": "read:search"})

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is False
    assert decision.reason == "INSUFFICIENT_SCOPE"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_accepts_tuple_grants_of_strings() -> None:
    authz = PolicyAuthzPort()
    ctx = _ctx(metadata={"service_account_scopes": ("read:search",)})

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is True
    assert decision.reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_grant_lists_skip_non_string_entries() -> None:
    authz = PolicyAuthzPort()
    # Mixed-type sequences keep only string entries; non-strings cannot
    # fabricate grants.
    ctx = _ctx(
        metadata={"service_account_scopes": ["read:search", 123, None, b"write"]}
    )

    decision: AuthzDecision = await authz.authorize_tool("get_entity", ctx)

    assert decision.allowed is True
    assert decision.reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorize_denies_when_tenant_context_is_missing() -> None:
    authz = PolicyAuthzPort()
    # RuntimeContext rejects empty tenant_id at validation; the guard must
    # still deny an unvalidated context (model_construct) — defense in depth.
    ctx = RuntimeContext.model_construct(
        tenant_id="", trace_id="trace-1", run_id="run-1", workflow_id="wf-1", workflow_type="demo"
    )

    decision: AuthzDecision = await authz.authorize_tool("calculate_roi", ctx)

    assert decision.allowed is False
    assert decision.reason == "missing_tenant"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_roi_executes_end_to_end_through_runtime() -> None:
    adapter = LegacyToolRegistryAdapter()
    adapter.register(_roi_tool_def())
    runtime = AgentRuntimeImpl(tool_registry=adapter, authz=PolicyAuthzPort())
    ctx = _ctx()

    result = await runtime.call_tool(
        "calculate_roi", {"investment": 1000, "returns": [1100]}, ctx
    )

    assert result.status == "success"
    assert result.data is not None
    assert result.data["total_return"] == 1100.0
    assert result.data["simple_roi_percent"] == 10.0
    assert result.data["npv"] == 0.0
