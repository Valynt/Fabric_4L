from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.agents.base import AgentCapability, BaseAgent
from value_fabric.shared.governance.abom import AgentBillOfMaterials
from value_fabric.shared.governance.tool_gateway import ToolGateway


class DummyAgent(BaseAgent):
    agent_type = "ConversationAgent"

    def get_capabilities(self) -> list[AgentCapability]:
        return [AgentCapability(name="echo", description="echo")]

    async def execute(self, task: dict, context: dict) -> dict:
        gateway = context.get("tool_gateway")
        if gateway is None:
            return {"tool_gateway_present": False}
        result = await gateway.execute("query_graph", {"value": "hello"})
        return {"tool_gateway_present": True, "result": result}


def _make_registry() -> MagicMock:
    registry = MagicMock()
    registry.execute = AsyncMock(return_value={"echo": "hello"})
    return registry


class TestBaseAgentABOM:
    MANIFEST_DIR = Path(__file__).resolve().parents[1] / "manifests"

    @pytest.mark.asyncio
    async def test_initialize_loads_abom_from_default_dir(self) -> None:
        agent = DummyAgent(config={})
        await agent.initialize()
        assert agent.abom is not None
        assert agent.abom.agent_type == "ConversationAgent"
        assert "abom_hash" in agent.state.metadata

    @pytest.mark.asyncio
    async def test_initialize_loads_abom_from_config_path(self) -> None:
        path = self.MANIFEST_DIR / "orchestration_controller.abom.json"
        agent = DummyAgent(config={"manifest_path": str(path)})
        await agent.initialize()
        assert agent.abom.agent_type == "OrchestrationController"

    @pytest.mark.asyncio
    async def test_run_injects_tool_gateway(self) -> None:
        agent = DummyAgent(config={})
        registry = _make_registry()
        result = await agent.run(
            {"capability": "echo", "parameters": {}},
            context={
                "tool_registry": registry,
                "tenant_id": "tenant-123",
                "trace_id": "trace-abc",
            },
        )
        assert result["tool_gateway_present"] is True
        assert result["result"] == {"echo": "hello"}
        registry.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_without_registry_degrades_to_no_gateway(self) -> None:
        agent = DummyAgent(config={})
        result = await agent.run(
            {"capability": "echo", "parameters": {}},
            context={},
        )
        assert result["tool_gateway_present"] is False
