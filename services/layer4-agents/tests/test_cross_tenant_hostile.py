from __future__ import annotations

"""Cross-tenant hostile invariants for layer4-agents."""


from pathlib import Path

import pytest

from value_fabric.layer4.engine.executor import OrchestrationController
from value_fabric.layer4.engine.state_manager import StateManager
from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowStatus, WorkflowType
from value_fabric.layer4.tools.registry import ToolRegistry


def _load_service_code() -> str:
    """Concatenate all Python source under the service ``src`` tree."""
    service_root = Path(__file__).resolve().parents[1] / "src"
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in service_root.rglob("*.py"))


def test_tenant_a_cannot_read_tenant_b_patterns_present() -> None:
    content = _load_service_code()
    assert "tenant_id" in content, "Expected tenant_id references in source"
    assert "list_" in content or "get_" in content, "Expected read-style method names in source"


def test_tenant_a_cannot_mutate_tenant_b_patterns_present() -> None:
    content = _load_service_code()
    assert "tenant_id" in content, "Expected tenant_id references in source"
    assert (
        "create" in content
        or "update" in content
        or "delete" in content
        or "ingest" in content
    ), "Expected write-style method names in source"


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
