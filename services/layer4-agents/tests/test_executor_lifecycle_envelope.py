"""Characterization tests for OrchestrationController lifecycle transitions and output envelopes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from layer4_agents.engine.executor import CheckpointConflictError, OrchestrationController
from layer4_agents.models.agent_state import ROIAgentState, WorkflowStatus, WorkflowType
from layer4_agents.tools.registry import ToolRegistry


@pytest.mark.unit
class TestOrchestrationControllerLifecycleAndEnvelope:
    """Tests lifecycle states and output envelope contract for OrchestrationController."""

    @pytest.mark.asyncio
    async def test_get_result_envelope_contract(self):
        """Assert the structural contract of get_result output envelope."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        state = ROIAgentState(
            tenant_id="tenant-123",
            workflow_id="wf-test-01",
            workflow_type=WorkflowType.ROI_CALCULATOR,
        )
        now = datetime.now(UTC)
        state.status = WorkflowStatus.COMPLETED
        state.started_at = now
        state.completed_at = now
        state.output_data = {"roi_percentage": 145.5, "payback_months": 8}
        await controller.state_manager.save_state("wf-test-01", state)

        result = await controller.get_result("wf-test-01")
        assert result is not None
        assert result["workflow_id"] == "wf-test-01"
        assert result["status"] == "completed"
        assert result["output"] == {"roi_percentage": 145.5, "payback_months": 8}
        assert result["started_at"] is not None
        assert result["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_get_result_for_tenant_returns_result_only_for_owner(self):
        """Tenant-scoped results should be returned only for the authoritative owner."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        state = ROIAgentState(
            tenant_id="tenant-123",
            workflow_id="wf-tenant-owned",
            workflow_type=WorkflowType.ROI_CALCULATOR,
        )
        state.status = WorkflowStatus.COMPLETED
        state.output_data = {"roi_percentage": 145.5}
        await controller.state_manager.save_state("wf-tenant-owned", state)

        owner_result = await controller.get_result_for_tenant("wf-tenant-owned", "tenant-123")
        foreign_result = await controller.get_result_for_tenant("wf-tenant-owned", "tenant-999")

        assert owner_result is not None
        assert owner_result["workflow_id"] == "wf-tenant-owned"
        assert foreign_result is None

    @pytest.mark.asyncio
    async def test_get_result_for_tenant_fails_closed_when_persisted_tenant_is_missing(self):
        """Malformed persisted state without tenant ownership must be denied."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        workflow_id = "wf-missing-tenant"
        key = controller.state_manager._get_key(workflow_id)
        controller.state_manager._memory_store[key] = {
            "data": {
                "workflow_id": workflow_id,
                "workflow_type": "roi_calculator",
                "status": "completed",
                "output_data": {"roi_percentage": 145.5},
                "metadata": {"workflow_id": workflow_id},
            },
            "expires": datetime.now(UTC).timestamp() + 60,
        }

        result = await controller.get_result_for_tenant(workflow_id, "tenant-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_workflow_status_envelope_contract(self):
        """Assert the structural contract of get_workflow_status output envelope."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        state = ROIAgentState(
            tenant_id="tenant-xyz",
            workflow_id="wf-test-02",
            workflow_type=WorkflowType.BUSINESS_CASE,
        )
        state.status = WorkflowStatus.RUNNING
        state.current_node = "financial_modeling"
        await controller.state_manager.save_state("wf-test-02", state)

        status_res = await controller.get_workflow_status("wf-test-02")
        assert status_res is not None
        assert status_res["workflow_id"] == "wf-test-02"
        assert status_res["workflow_type"] == "business_case"
        assert status_res["status"] == "running"
        assert status_res["current_node"] == "financial_modeling"

    def test_get_cluster_health_envelope_contract(self):
        """Assert cluster health envelope structure."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        health = controller.get_cluster_health()
        assert "status" in health
        assert "active_workflows" in health
        assert "pending_tasks" in health
        assert "running_tasks" in health
        assert "registered_agents" in health
        assert "utilization" in health

    @pytest.mark.asyncio
    async def test_workflow_lifecycle_cancel_transition(self):
        """Verify lifecycle cancellation transitions status to CANCELLED."""
        controller = OrchestrationController(tool_registry=ToolRegistry())
        state = ROIAgentState(
            tenant_id="tenant-abc",
            workflow_id="wf-cancel-01",
            workflow_type=WorkflowType.ROI_CALCULATOR,
        )
        state.status = WorkflowStatus.RUNNING
        state.started_at = datetime.now(UTC)
        await controller.state_manager.save_state("wf-cancel-01", state)

        await controller.cancel_workflow("wf-cancel-01", reason="User requested abort")
        # scheduler.cancel_task may return False if not queued in scheduler, but state is marked CANCELLED
        updated_state = await controller.state_manager.load_state("wf-cancel-01")
        assert updated_state is not None
        assert updated_state.status == WorkflowStatus.CANCELLED

    def test_checkpoint_conflict_error_metadata(self):
        """Assert CheckpointConflictError retains error metadata envelope."""
        err = CheckpointConflictError(
            message="State hash conflict detected",
            metadata={"expected_hash": "hash_a", "actual_hash": "hash_b", "workflow_id": "wf-1"},
        )
        assert str(err) == "State hash conflict detected"
        assert err.metadata["expected_hash"] == "hash_a"
        assert err.metadata["actual_hash"] == "hash_b"
        assert err.metadata["workflow_id"] == "wf-1"
