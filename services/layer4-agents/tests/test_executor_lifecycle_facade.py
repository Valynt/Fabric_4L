from __future__ import annotations

import pytest

from layer4_agents.engine.execution_dispatch import build_workflow_task
from layer4_agents.engine.execution_validation import (
    ensure_controller_accepts_execution,
)
from layer4_agents.engine.executor import WorkflowExecutionError


def test_validation_phase_raises_when_shutdown() -> None:
    with pytest.raises(WorkflowExecutionError):
        ensure_controller_accepts_execution(
            is_shutdown=True, error_cls=WorkflowExecutionError
        )


def test_dispatch_phase_builds_scheduler_task_shape() -> None:
    task = build_workflow_task(
        priority=3,
        workflow_id="wf-123",
        tenant_id="tenant-a",
        user_id="user-a",
        workflow_type="roi_calculator",
        workflow=object(),
        initial_state=object(),
        checkpoint_interval=5,
        handler=lambda *_args, **_kwargs: None,
    )
    assert task.task_id == "wf-wf-123"
    assert task.workflow_instance_id == "wf-123"
    assert task.tenant_id == "tenant-a"
    assert task.context["workflow_type"] == "roi_calculator"
    assert task.tenant_context["auth_source"] == "workflow_execution"


@pytest.mark.asyncio
async def test_execute_workflow_deduplication_returns_existing_completed_state() -> (
    None
):
    from unittest.mock import AsyncMock, MagicMock

    from layer4_agents.engine.executor import OrchestrationController
    from layer4_agents.models.agent_state import (
        BaseAgentState,
        WorkflowStatus,
        WorkflowType,
    )

    mock_state_mgr = MagicMock()
    existing = BaseAgentState(
        workflow_id="wf-existing-1",
        tenant_id="tenant-123",
        workflow_type=WorkflowType.ROI_CALCULATOR,
        status=WorkflowStatus.COMPLETED,
    )
    mock_state_mgr.load_state = AsyncMock(return_value=existing)

    controller = OrchestrationController(
        tool_registry=MagicMock(), state_manager=mock_state_mgr
    )
    controller.checkpoint_saver = MagicMock()

    result = await controller.execute_workflow(
        workflow_type="roi_calculator",
        input_data={},
        workflow_id="wf-existing-1",
        tenant_id="tenant-123",
    )

    assert result == existing
    mock_state_mgr.load_state.assert_called_once_with("wf-existing-1")
