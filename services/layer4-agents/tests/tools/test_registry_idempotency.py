from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from layer4_agents.tools.registry import BaseTool, ToolCategory, ToolRegistry, ToolResult


class _FakeStore:
    """In-memory stand-in for an async Redis client."""

    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        self._data[key] = value


class _EchoInput(BaseModel):
    message: str


class _EchoOutput(BaseModel):
    echo: str


class _EchoTool(BaseTool):
    name = "echo_tool"
    category = ToolCategory.UTILITY
    description = "Echoes input"
    input_schema = _EchoInput
    output_schema = _EchoOutput

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.call_count = 0

    async def execute(self, input_data: _EchoInput) -> _EchoOutput:
        self.call_count += 1
        await asyncio.sleep(0)  # ensure async path
        return _EchoOutput(echo=input_data.message)


@pytest.mark.asyncio
async def test_redis_idempotency_returns_cached_result_without_re_executing():
    fake_redis = _FakeStore()
    registry = ToolRegistry(redis_client=fake_redis)
    tool = _EchoTool()
    registry.register(tool)

    result1 = await registry.execute(
        "echo_tool",
        {"message": "hello", "tenant_id": "tenant-1", "idempotency_key": "key-1"},
    )
    assert result1.is_success()
    assert result1.data == {"echo": "hello"}
    assert tool.call_count == 1

    # A second call with the same idempotency key must return the cached result
    # without invoking execute() again.
    result2 = await registry.execute(
        "echo_tool",
        {"message": "different", "tenant_id": "tenant-1", "idempotency_key": "key-1"},
    )
    assert result2.is_success()
    assert result2.data == {"echo": "hello"}
    assert tool.call_count == 1

    # A new registry instance pointing at the same Redis data must also hit cache.
    new_registry = ToolRegistry(redis_client=fake_redis)
    new_registry.register(tool)
    result3 = await new_registry.execute(
        "echo_tool",
        {"message": "new", "tenant_id": "tenant-1", "idempotency_key": "key-1"},
    )
    assert result3.is_success()
    assert result3.data == {"echo": "hello"}
    assert tool.call_count == 1


@pytest.mark.asyncio
async def test_redis_idempotency_is_tenant_scoped():
    fake_redis = _FakeStore()
    registry = ToolRegistry(redis_client=fake_redis)
    tool = _EchoTool()
    registry.register(tool)

    await registry.execute(
        "echo_tool",
        {"message": "tenant-a", "tenant_id": "tenant-a", "idempotency_key": "shared-key"},
    )

    result_b = await registry.execute(
        "echo_tool",
        {"message": "tenant-b", "tenant_id": "tenant-b", "idempotency_key": "shared-key"},
    )
    # Same idempotency key for a different tenant must not collide.
    assert result_b.is_success()
    assert result_b.data == {"echo": "tenant-b"}
    assert tool.call_count == 2
