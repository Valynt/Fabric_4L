from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.agents.base import BaseAgent


class _MemoryAgent(BaseAgent):
    agent_type = "MEMORY_AGENT"

    def get_capabilities(self):
        return []

    async def execute(self, task, ctx):
        mgw = ctx["memory_gateway"]
        await mgw.query(task["parameters"]["query"])
        return {"status": "ok"}


def _write_manifest(tmp_path):
    manifest = tmp_path / "memory_agent.abom.json"
    manifest.write_text(json.dumps({
        "schema_version": "1.0",
        "agent_type": "MEMORY_AGENT",
        "privilege_tier": "standard",
        "allowed_tools": ["tool_a"],
        "denied_tools": [],
        "invariants": {"max_tool_calls_per_run": 10},
    }))
    return manifest


@pytest.mark.asyncio
async def test_run_creates_memory_gateway_from_retrieval_engine(tmp_path):
    manifest = _write_manifest(tmp_path)
    engine = MagicMock()
    engine.query = AsyncMock(return_value={
        "query": "pain points",
        "entities": [{"id": "e1", "source_id": "src-1"}],
        "relationships": [],
        "context_graph": {},
        "traversal_path": [],
        "confidence_score": 0.9,
        "sources": ["src-1"],
    })

    agent = _MemoryAgent(config={"manifest_path": str(manifest)})
    result = await agent.run(
        {"capability": "analyze", "parameters": {"query": "pain points"}},
        context={
            "tenant_id": "t-1",
            "trace_id": "trace-1",
            "tool_registry": MagicMock(),
            "retrieval_engine": engine,
        },
    )

    assert result["status"] == "ok"
    assert "memory_gateway" in agent.state.context
    assert len(agent.state.context["memory_gateway"].access_log) == 1


@pytest.mark.asyncio
async def test_run_reuses_existing_memory_gateway(tmp_path):
    manifest = _write_manifest(tmp_path)
    existing = MagicMock()
    existing.access_log = [{"query": "cached"}]
    existing.query = AsyncMock()

    agent = _MemoryAgent(config={"manifest_path": str(manifest)})
    await agent.run(
        {"capability": "analyze", "parameters": {"query": "x"}},
        context={
            "tenant_id": "t-1",
            "trace_id": "trace-1",
            "tool_registry": MagicMock(),
            "memory_gateway": existing,
        },
    )

    assert agent.state.context["memory_gateway"] is existing


@pytest.mark.asyncio
async def test_memory_gateway_receives_tenant_and_agent_id(tmp_path):
    manifest = _write_manifest(tmp_path)
    engine = MagicMock()
    engine.query = AsyncMock(return_value={
        "query": "pain points",
        "entities": [{"id": "e1", "source_id": "src-1"}],
        "relationships": [],
        "context_graph": {},
        "traversal_path": [],
        "confidence_score": 0.9,
        "sources": ["src-1"],
    })

    agent = _MemoryAgent(config={"manifest_path": str(manifest)})
    await agent.run(
        {"capability": "analyze", "parameters": {"query": "pain points"}},
        context={
            "tenant_id": "t-1",
            "trace_id": "trace-1",
            "tool_registry": MagicMock(),
            "retrieval_engine": engine,
            "memory_source_blocklist": ["bad-source"],
        },
    )

    mgw = agent.state.context["memory_gateway"]
    assert mgw._tenant_id == "t-1"
    assert mgw._agent_id == agent.agent_id
    assert mgw._trace_id == "trace-1"
    assert mgw._source_blocklist == {"bad-source"}


class _NoMemoryAgent(BaseAgent):
    agent_type = "MEMORY_AGENT"

    def get_capabilities(self):
        return []

    async def execute(self, task, ctx):
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_run_without_memory_or_retrieval_engine_still_executes(tmp_path):
    manifest = _write_manifest(tmp_path)
    agent = _NoMemoryAgent(config={"manifest_path": str(manifest)})
    result = await agent.run(
        {"capability": "noop"},
        context={
            "tenant_id": "t-1",
            "trace_id": "trace-1",
            "tool_registry": MagicMock(),
        },
    )
    assert result["status"] == "ok"
    assert "memory_gateway" not in agent.state.context


@pytest.mark.asyncio
async def test_replay_mode_disabled_skips_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_REPLAY_MODE", "disabled")
    manifest = _write_manifest(tmp_path)

    class _NoOpAgent(BaseAgent):
        agent_type = "MEMORY_AGENT"

        def get_capabilities(self):
            return []

        async def execute(self, task, ctx):
            return {"status": "ok"}

    agent = _NoOpAgent(config={"manifest_path": str(manifest)})
    result = await agent.run(
        {"capability": "noop"},
        context={
            "tenant_id": "t-1",
            "trace_id": "trace-1",
            "tool_registry": MagicMock(),
        },
    )

    assert result["status"] == "ok"
    assert agent.state.metadata.get("replay_committed") is not True
