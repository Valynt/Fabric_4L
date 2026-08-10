from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import BaseModel
from value_fabric.shared.identity.context import RequestContext

import layer4_agents.tools.registry as module
from layer4_agents.models.tool_schemas import ToolCategory
from layer4_agents.tools.registry import (
    BaseTool,
    TenantAwareTool,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
)


class Input(BaseModel):
    value: int


class Output(BaseModel):
    doubled: int


class SampleTool(BaseTool):
    name = "sample"
    category = ToolCategory.UTILITY
    description = "Sample helper"
    input_schema = Input
    output_schema = Output

    async def execute(self, input_data):
        return Output(doubled=input_data.value * 2)


class TenantTool(TenantAwareTool):
    name = "tenant_tool"
    input_schema = Input

    async def execute(self, input_data):
        return {"value": input_data.value}


class Redis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex):
        self.values[key] = value
        self.expiry = ex


def test_result_metadata_redaction_and_canonical_conversion() -> None:
    success = ToolResult.success({"value": 1}, {"trace_id": "trace", "tenant_id": "tenant"})
    assert success.is_success() and not success.is_error()
    assert success.to_canonical().data == {"value": 1}
    failure = ToolResult.failure(
        "BAD", "safe", {"field": "value"}, trace_id="trace", recoverable=True
    )
    assert failure.is_error() and failure.error["details"] == {"field": "value"}
    assert failure.to_canonical().error.code == "BAD"
    metadata = module._safe_metadata(request_id="request", tenant_id="tenant", execution_time_ms=3)
    assert metadata == {
        "trace_id": "request",
        "request_id": "request",
        "tenant_id": "tenant",
        "execution_time_ms": 3,
    }
    assert module._safe_input_keys({"query": 1, "api_key": "secret", "password": "secret"}) == [
        "query",
        "[redacted]",
        "[redacted]",
    ]
    value = UUID("550e8400-e29b-41d4-a716-446655440000")
    assert module._coerce_uuid_string(value) == str(value)
    assert module._coerce_uuid_string("bad") is None
    assert module._has_internal_execution_envelope(
        {"workflow_id": "w", "run_id": "r", "trace_id": "t"}
    )


@pytest.mark.asyncio
async def test_base_and_tenant_tool_run_contracts(monkeypatch) -> None:
    tool = SampleTool({"tenant_id": "tenant"})
    assert tool.get_tenant_id() == "tenant" and tool.get_schema().name == "sample"
    assert (await tool.run({"value": 2}, trace_id="trace")).data == {"doubled": 4}
    invalid = await tool.run({"api_key": "secret"})
    assert invalid.error["code"] == "INPUT_VALIDATION_ERROR"
    no_schema = SampleTool()
    no_schema.input_schema = None
    assert (await no_schema.run({})).error["code"] == "CONFIGURATION_ERROR"

    failing = SampleTool()
    monkeypatch.setattr(failing, "execute", lambda _input: _raise_async(RuntimeError("secret")))
    assert (await failing.run({"value": 1})).error["code"] == "TOOL_EXECUTION_ERROR"

    tenant = TenantTool()
    assert (await tenant.run({"value": 1})).error["code"] == "TENANT_CONTEXT_MISSING"
    tenant = TenantTool({"tenant_id": "tenant"})
    assert (await tenant.run({"value": 1})).data == {"value": 1}


@pytest.mark.asyncio
async def test_registry_cache_registration_and_filtering(monkeypatch) -> None:
    registry = ToolRegistry()
    sample = SampleTool()
    registry.register(sample)
    assert registry.has_tool("sample") and registry.get("sample") is sample
    with pytest.raises(ValueError, match="already registered"):
        registry.register(sample)
    with pytest.raises(ToolNotFoundError):
        registry.get("missing")
    unnamed = SampleTool()
    unnamed.name = ""
    with pytest.raises(ValueError, match="must have a name"):
        registry.register(unnamed)
    registry.register_batch([TenantTool({"tenant_id": "tenant"})])
    assert len(registry.list_tools(category=ToolCategory.UTILITY, search="sample")) == 1
    assert set(registry.get_all_schemas()) == {"sample", "tenant_tool"}

    result = ToolResult.success({"value": 1})
    await registry._set_cached_result("tenant", "sample", "key", result)
    assert await registry._get_cached_result("tenant", "sample", "key") == result
    redis = Redis()
    remote = ToolRegistry(redis)
    await remote._set_cached_result("tenant", "sample", "key", result)
    assert (await remote._get_cached_result("tenant", "sample", "key")).data == {"value": 1}
    assert remote._idempotency_key("tenant", "sample", "key").startswith("l4:tool:idempotency:")

    assert callable(registry.get_all_tools()["sample"])
    metadata = registry.get_tool_metadata("sample")
    assert metadata.name == "sample" and metadata.category == ToolCategory.UTILITY
    context = RequestContext(tenant_id=UUID(int=1), permissions=["read"])
    assert "sample" in registry.get_available_tools(context)
    registry.unregister("sample")
    assert not registry.has_tool("sample")
    registry.clear()
    assert registry.list_tools() == []


@pytest.mark.asyncio
async def test_tool_decorator_and_global_registry() -> None:
    @module.tool(
        name="double",
        category=ToolCategory.CALCULATION,
        description="Double value",
        input_schema=Input,
        output_schema=Output,
    )
    async def double(value):
        return Output(doubled=value.value * 2)

    dynamic = double()
    assert dynamic.name == "double" and (await dynamic.execute(Input(value=3))).doubled == 6
    module.reset_global_registry()
    first = module.get_global_registry()
    assert module.get_global_registry() is first
    module.reset_global_registry()
    assert module.get_global_registry() is not first


async def _raise_async(error):
    raise error
