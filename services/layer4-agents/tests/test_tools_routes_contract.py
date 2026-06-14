from __future__ import annotations

from types import SimpleNamespace

import pytest

from layer4_agents.api.routes import tools
from layer4_agents.models.tool_schemas import ToolCategory


class _StubTool:
    def get_schema(self):
        return SimpleNamespace(
            name="stub_tool",
            category=ToolCategory.UTILITY,
            description="stub",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
            output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
            timeout_seconds=15,
            requires_auth=True,
            examples=[{"input": {"x": 1}, "output": {"ok": True}}],
        )


class _StubRegistry:
    def has_tool(self, tool_name: str) -> bool:
        return tool_name == "stub_tool"

    def get(self, _tool_name: str) -> _StubTool:
        return _StubTool()


@pytest.mark.asyncio
async def test_get_tool_schema_returns_typed_shape() -> None:
    response = await tools.get_tool_schema(
        tool_name="stub_tool",
        registry=_StubRegistry(),
        ctx=SimpleNamespace(tenant_id="tenant-1"),
    )

    payload = response.model_dump()
    assert isinstance(payload["category"], str)
    assert payload["category"] == "utility"
    assert isinstance(payload["input_schema"], dict)
    assert isinstance(payload["output_schema"], dict)
    assert isinstance(payload["examples"], list)
    assert payload["examples"], "expected at least one example"
    assert set(payload["examples"][0].keys()) == {"input", "output"}
    assert isinstance(payload["examples"][0]["input"], dict)
    assert isinstance(payload["examples"][0]["output"], dict)
    assert isinstance(payload["timeout_seconds"], int)
    assert isinstance(payload["requires_auth"], bool)


@pytest.mark.asyncio
async def test_list_tool_categories_returns_typed_items() -> None:
    response = await tools.list_tool_categories(ctx=SimpleNamespace(tenant_id="tenant-1"))

    payload = response.model_dump()
    assert isinstance(payload["categories"], list)
    assert payload["categories"], "expected at least one category"
    assert set(payload.keys()) == {"categories"}
    for category in payload["categories"]:
        assert set(category.keys()) == {"id", "name"}
        assert isinstance(category["id"], str)
        assert isinstance(category["name"], str)
