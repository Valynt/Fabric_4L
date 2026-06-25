from __future__ import annotations

"""Tests for mandatory tenant scope as a workflow-start invariant."""



import pytest

from layer4_agents.engine.executor import OrchestrationController, WorkflowExecutionError
from layer4_agents.tools.registry import ToolRegistry
from layer4_agents.workflows.roi_calculator import ROICalculatorWorkflow


class TestWorkflowStartTenantInvariant:
    def test_base_agent_state_rejects_empty_tenant(self) -> None:
        from layer4_agents.models.agent_state import BaseAgentState, WorkflowType

        with pytest.raises(ValueError, match="tenant_id is required"):
            BaseAgentState(
                workflow_type=WorkflowType.ROI_CALCULATOR,
                tenant_id="",
            )

    def test_base_agent_state_accepts_valid_tenant(self) -> None:
        from layer4_agents.models.agent_state import BaseAgentState, WorkflowType

        state = BaseAgentState(
            workflow_type=WorkflowType.ROI_CALCULATOR,
            tenant_id="tenant-123",
        )
        assert state.tenant_id == "tenant-123"

    def test_create_initial_state_requires_tenant_id(self) -> None:
        registry = ToolRegistry()
        workflow = ROICalculatorWorkflow(registry)

        with pytest.raises(TypeError):
            workflow.create_initial_state({"prospect_id": "p1", "value_driver_ids": ["vd1"]})

    def test_create_initial_state_generates_envelope(self) -> None:
        registry = ToolRegistry()
        workflow = ROICalculatorWorkflow(registry)

        state = workflow.create_initial_state(
            {"prospect_id": "p1", "value_driver_ids": ["vd1"]},
            tenant_id="tenant-123",
        )
        assert state.tenant_id == "tenant-123"
        assert state.run_envelope is not None
        assert state.run_envelope.tenant_id == "tenant-123"
        assert state.run_id == state.run_envelope.run_id
        assert state.workflow_id == state.run_envelope.workflow_id

    @pytest.mark.asyncio
    async def test_execute_workflow_rejects_missing_tenant(self) -> None:
        registry = ToolRegistry()
        controller = OrchestrationController(tool_registry=registry)

        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.execute_workflow(
                workflow_type="roi_calculator",
                input_data={"prospect_id": "p1", "value_driver_ids": ["vd1"]},
                tenant_id=None,
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_rejects_empty_tenant(self) -> None:
        registry = ToolRegistry()
        controller = OrchestrationController(tool_registry=registry)

        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.execute_workflow(
                workflow_type="roi_calculator",
                input_data={"prospect_id": "p1", "value_driver_ids": ["vd1"]},
                tenant_id="",
            )

    @pytest.mark.asyncio
    async def test_schedule_workflow_rejects_missing_tenant(self) -> None:
        registry = ToolRegistry()
        controller = OrchestrationController(tool_registry=registry)

        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.schedule_workflow(
                workflow_type="roi_calculator",
                input_data={"prospect_id": "p1", "value_driver_ids": ["vd1"]},
                tenant_id=None,
            )

    @pytest.mark.asyncio
    async def test_schedule_workflow_rejects_empty_tenant(self) -> None:
        registry = ToolRegistry()
        controller = OrchestrationController(tool_registry=registry)

        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.schedule_workflow(
                workflow_type="roi_calculator",
                input_data={"prospect_id": "p1", "value_driver_ids": ["vd1"]},
                tenant_id="",
            )
