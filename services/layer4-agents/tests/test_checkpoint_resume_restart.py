"""Recovery test: workflow resumes from Postgres checkpoint after pod restart.

Simulates a pod restart by creating a new BaseWorkflow instance with the same
thread_id and checkpoint saver, then asserts that state resumes correctly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from langgraph.types import interrupt

from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowStatus
from value_fabric.layer4.models.workflow_config import EdgeConfig, NodeConfig, NodeType, WorkflowConfig
from value_fabric.layer4.tools.registry import ToolRegistry
from value_fabric.layer4.workflows.base import BaseWorkflow


TEST_WORKFLOW_TYPE = "roi_calculator"


class RestartTestWorkflow(BaseWorkflow):
    """Minimal workflow that interrupts at the middle node for HITL testing."""

    def __init__(self, tool_registry, checkpoint_saver=None):
        config = WorkflowConfig(
            workflow_type=TEST_WORKFLOW_TYPE,
            name="Restart Test Workflow",
            description="Tests checkpoint resume across instances",
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

    async def _execute_tool(self, tool_name: str, state, config: dict) -> dict[str, Any]:
        current_node = state.current_node
        self.executed_nodes.append(current_node)
        # Interrupt on the second node execution (middle)
        if len(self.executed_nodes) == 2:
            interrupt("Approval required")
        return {"status": "ok", "node": current_node, "tool": tool_name}

    def create_initial_state(self, input_data: dict[str, Any], *, tenant_id: str | None = None) -> BaseAgentState:
        return BaseAgentState(tenant_id=tenant_id or "test-tenant",
            workflow_id=input_data.get("workflow_id", "restart-test-wf"),
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PENDING,
            input_data=input_data,
            output_data={},
            errors=[],
        )


@pytest.mark.unit
class TestCheckpointResumeRestart:
    """Test that workflow state survives a simulated pod restart."""

    @pytest.mark.asyncio
    async def test_workflow_resumes_after_new_instance(self):
        """Create a workflow, interrupt it, then resume from a brand-new instance."""
        registry = AsyncMock(spec=ToolRegistry)
        registry.execute = AsyncMock(return_value={"result": "mock"})

        saver = InMemorySaver()

        # --- First instance: start workflow, it should interrupt before "middle" ---
        workflow1 = RestartTestWorkflow(registry, checkpoint_saver=saver)
        initial_state = workflow1.create_initial_state({"test": "data"}, tenant_id="test-tenant")
        thread_id = initial_state.workflow_id

        result1 = await workflow1.run(initial_state, thread_id=thread_id)

        assert result1.status == WorkflowStatus.INTERRUPTED

        # --- Simulate pod restart: new instance, same thread_id, same saver ---
        workflow2 = RestartTestWorkflow(registry, checkpoint_saver=saver)

        # Resume on the new instance using Command(resume=...)
        result2 = await workflow2.run(
            workflow2.create_initial_state({"test": "data"}, tenant_id="test-tenant"),
            thread_id=thread_id,
            resume_data={"approved": True},
        )

        assert result2.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_checkpoint_persists_across_instances(self):
        """The InMemorySaver (stand-in for Postgres) must retain state across workflow objects."""
        registry = AsyncMock(spec=ToolRegistry)
        registry.execute = AsyncMock(return_value={"result": "mock"})

        saver = InMemorySaver()
        thread_id = "persist-test"

        workflow1 = RestartTestWorkflow(registry, checkpoint_saver=saver)
        state1 = workflow1.create_initial_state({"workflow_id": thread_id}, tenant_id="test-tenant")
        await workflow1.run(state1, thread_id=thread_id)

        # Verify checkpoint exists in saver
        assert thread_id in saver.storage

        workflow2 = RestartTestWorkflow(registry, checkpoint_saver=saver)
        state2 = workflow2.create_initial_state({"workflow_id": thread_id}, tenant_id="test-tenant")
        result2 = await workflow2.run(state2, thread_id=thread_id, resume_data=True)

        assert result2.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_new_instance_without_shared_saver_does_not_resume(self):
        """A new instance with a fresh saver should behave like a new workflow."""
        registry = AsyncMock(spec=ToolRegistry)
        registry.execute = AsyncMock(return_value={"result": "mock"})

        saver1 = InMemorySaver()
        thread_id = "no-share-test"

        workflow1 = RestartTestWorkflow(registry, checkpoint_saver=saver1)
        state1 = workflow1.create_initial_state({"workflow_id": thread_id}, tenant_id="test-tenant")
        await workflow1.run(state1, thread_id=thread_id)

        # Fresh saver = no checkpoint knowledge
        saver2 = InMemorySaver()
        workflow2 = RestartTestWorkflow(registry, checkpoint_saver=saver2)
        state2 = workflow2.create_initial_state({"workflow_id": thread_id}, tenant_id="test-tenant")

        # With a fresh saver, resume should fail because there's no checkpoint
        with pytest.raises(Exception):
            await workflow2.run(state2, thread_id=thread_id, resume_data=True)
