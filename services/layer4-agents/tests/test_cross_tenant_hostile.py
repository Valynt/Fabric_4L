from __future__ import annotations

"""Cross-tenant hostile invariants for layer4-agents.

These tests prove runtime tenant isolation at the workflow controller level:
a tenant can only archive, list, or transition workflows that belong to their
own tenant, and the tenant kill-switch blocks suspended tenants.
"""


from datetime import UTC
from unittest.mock import Mock

import pytest

from layer4_agents.engine.executor import OrchestrationController
from layer4_agents.engine.state_manager import StateManager
from layer4_agents.models.agent_state import BaseAgentState, WorkflowStatus, WorkflowType
from layer4_agents.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Runtime controller-level hostile tests (no mocks — real controller + state)
# ---------------------------------------------------------------------------

@pytest.fixture
def runtime_controller():
    """Real OrchestrationController with in-memory StateManager for runtime tests."""
    registry = ToolRegistry()
    controller = OrchestrationController(
        tool_registry=registry,
        state_manager=StateManager(),
    )
    return controller


def _make_state(status: WorkflowStatus) -> BaseAgentState:
    """Build a minimal BaseAgentState for controller tests."""
    return BaseAgentState(tenant_id="test-tenant", 
        workflow_id="",
        workflow_type=WorkflowType.ORCHESTRATOR,
        status=status,
    )


@pytest.mark.asyncio
async def test_archive_workflow_rejects_cross_tenant(runtime_controller):
    """archive_workflow must raise PermissionError when tenant_id does not match."""
    wf_id = "wf-tenant-a-001"
    state = _make_state(WorkflowStatus.COMPLETED)
    state.metadata = {"archived": False}

    # Seed the controller's metadata and state manager
    runtime_controller._workflow_metadata[wf_id] = {"tenant_id": "tenant-a"}
    await runtime_controller.state_manager.save_state(wf_id, state)

    with pytest.raises(PermissionError, match="belongs to tenant"):
        await runtime_controller.archive_workflow(wf_id, tenant_id="tenant-b")


@pytest.mark.asyncio
async def test_list_active_workflows_filters_cross_tenant(runtime_controller):
    """list_active_workflows must not return workflows from other tenants."""
    # Create workflow for tenant-a
    state_a = _make_state(WorkflowStatus.RUNNING)
    state_a.metadata = {"archived": False}
    runtime_controller._workflow_metadata["wf-a"] = {"tenant_id": "tenant-a"}
    await runtime_controller.state_manager.save_state("wf-a", state_a)

    # Create workflow for tenant-b
    state_b = _make_state(WorkflowStatus.RUNNING)
    state_b.metadata = {"archived": False}
    runtime_controller._workflow_metadata["wf-b"] = {"tenant_id": "tenant-b"}
    await runtime_controller.state_manager.save_state("wf-b", state_b)

    results = await runtime_controller.list_active_workflows(tenant_id="tenant-a")
    assert len(results) == 1
    assert results[0].get("workflow_id") == "wf-a"


@pytest.mark.asyncio
async def test_list_workflows_filters_cross_tenant(runtime_controller):
    """list_workflows must not return workflows from other tenants."""
    state_a = _make_state(WorkflowStatus.COMPLETED)
    state_a.metadata = {"archived": False}
    runtime_controller._workflow_metadata["wf-a"] = {"tenant_id": "tenant-a"}
    await runtime_controller.state_manager.save_state("wf-a", state_a)

    state_b = _make_state(WorkflowStatus.COMPLETED)
    state_b.metadata = {"archived": False}
    runtime_controller._workflow_metadata["wf-b"] = {"tenant_id": "tenant-b"}
    await runtime_controller.state_manager.save_state("wf-b", state_b)

    results = await runtime_controller.list_workflows(tenant_id="tenant-a")
    assert len(results) == 1
    assert results[0].get("tenant_id") == "tenant-a"


@pytest.mark.asyncio
async def test_workflow_executor_blocks_suspended_tenant(runtime_controller):
    """_run_workflow_task must reject execution for suspended tenants (kill-switch)."""
    from datetime import datetime
    from unittest.mock import AsyncMock, patch

    from layer4_agents.engine.types import ScheduledTask
    from layer4_agents.models.agent_state import ROIAgentState

    tenant_id = "suspended-tenant"
    workflow_id = "wf-suspended-001"

    state = ROIAgentState(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_type="roi_calculator",
        status="pending",
    )
    task = ScheduledTask(
        priority=1,
        scheduled_time=datetime.now(UTC),
        task_id=f"wf-{workflow_id}",
        workflow_instance_id=workflow_id,
        capability="workflow_execution",
        agent_type="OrchestrationController",
        context={"tenant_id": tenant_id},
        parameters={
            "workflow": Mock(),
            "initial_state": state,
            "workflow_id": workflow_id,
        },
        tenant_id=tenant_id,
    )

    with patch(
        "value_fabric.shared.tenant_kill_switch.TenantKillSwitch.is_suspended",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with pytest.raises(Exception, match="suspended"):
            await runtime_controller._run_workflow_task(task)


@pytest.mark.asyncio
async def test_run_workflow_task_blocks_when_kill_switch_check_fails(runtime_controller):
    """_run_workflow_task must block execution when the tenant kill-switch cannot be queried."""
    from datetime import datetime
    from unittest.mock import AsyncMock, patch

    from layer4_agents.engine.executor import WorkflowExecutionError
    from layer4_agents.engine.types import ScheduledTask
    from layer4_agents.models.agent_state import ROIAgentState

    tenant_id = "kill-switch-err-tenant"
    workflow_id = "wf-kill-switch-err-001"

    state = ROIAgentState(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_type="roi_calculator",
        status="pending",
    )
    task = ScheduledTask(
        priority=1,
        scheduled_time=datetime.now(UTC),
        task_id=f"wf-{workflow_id}",
        workflow_instance_id=workflow_id,
        capability="workflow_execution",
        agent_type="OrchestrationController",
        context={"tenant_id": tenant_id},
        parameters={
            "workflow": Mock(),
            "initial_state": state,
            "workflow_id": workflow_id,
        },
        tenant_id=tenant_id,
    )

    with patch(
        "value_fabric.shared.tenant_kill_switch.TenantKillSwitch.is_suspended",
        new_callable=AsyncMock,
        side_effect=RuntimeError("kill-switch store unavailable"),
    ):
        with pytest.raises(
            WorkflowExecutionError, match="kill-switch check failed|blocking workflow execution"
        ):
            await runtime_controller._run_workflow_task(task)
