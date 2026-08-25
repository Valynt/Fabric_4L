"""Tests for Layer 4 OrchestrationController workflow lifecycle decomposition and facade integrity."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.engine.checkpoint_replay import (
    CheckpointReplayService,
    compute_state_hash,
    resolve_resume_policy,
)
from layer4_agents.engine.execution_dispatch import build_workflow_task
from layer4_agents.engine.execution_persistence import (
    WorkflowLifecyclePersistenceService,
    archive_workflow_state,
    recover_orphaned_workflow_states,
)
from layer4_agents.engine.execution_validation import (
    ensure_controller_accepts_execution,
)
from layer4_agents.engine.executor import (
    CheckpointConflictError,
    OrchestrationController,
    WorkflowExecutionError,
)
from layer4_agents.engine.ports import (
    CheckpointPolicyPort,
    WorkflowLifecyclePersistencePort,
    WorkflowRecoveryPort,
)
from layer4_agents.models.agent_state import (
    BaseAgentState,
    WorkflowStatus,
    WorkflowType,
)


@pytest.fixture
def mock_state_manager():
    sm = MagicMock()
    sm.load_state = AsyncMock()
    sm.save_state = AsyncMock()
    sm.list_active_workflows = AsyncMock(return_value=[])
    sm.get_workflow_checkpoints = AsyncMock(return_value=[])
    return sm


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


@pytest.fixture
def sample_state():
    return BaseAgentState(
        workflow_id="wf-test-123",
        workflow_type=WorkflowType.ORCHESTRATOR,
        status=WorkflowStatus.PENDING,
        tenant_id="tenant-alpha",
        input_data={"input": "test"},
        metadata={"created_at": datetime.now(UTC).isoformat()},
        errors=[],
    )


def test_protocol_implementations(mock_state_manager):
    """Verify that extracted services satisfy their structural lifecycle protocols."""
    persistence_svc = WorkflowLifecyclePersistenceService(mock_state_manager)
    replay_svc = CheckpointReplayService(mock_state_manager)

    assert isinstance(persistence_svc, WorkflowLifecyclePersistencePort)
    assert isinstance(persistence_svc, WorkflowRecoveryPort)
    assert isinstance(replay_svc, CheckpointPolicyPort)


@pytest.mark.asyncio
async def test_archive_workflow_state_success(mock_state_manager, sample_state):
    """Archiving a workflow sets archived flag and timestamp."""
    mock_state_manager.load_state.return_value = sample_state
    workflow_metadata = {"wf-test-123": {"tenant_id": "tenant-alpha"}}

    result = await archive_workflow_state(
        state_manager=mock_state_manager,
        workflow_id="wf-test-123",
        workflow_metadata=workflow_metadata,
        tenant_id="tenant-alpha",
    )

    assert result is not None
    assert "archived_at" in result
    assert sample_state.metadata.get("archived") is True
    mock_state_manager.save_state.assert_awaited_once_with("wf-test-123", sample_state)


@pytest.mark.asyncio
async def test_execute_workflow_deduplication_returns_existing_completed_state() -> (
    None
):
    from unittest.mock import AsyncMock, MagicMock

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


@pytest.mark.asyncio
async def test_archive_workflow_state_idempotent(mock_state_manager, sample_state):
    """Archiving an already archived workflow returns existing timestamp without saving."""
    sample_state.metadata["archived"] = True
    sample_state.metadata["archived_at"] = "2025-01-01T00:00:00Z"
    mock_state_manager.load_state.return_value = sample_state

    result = await archive_workflow_state(
        state_manager=mock_state_manager,
        workflow_id="wf-test-123",
        workflow_metadata={"wf-test-123": {"tenant_id": "tenant-alpha"}},
        tenant_id="tenant-alpha",
    )

    assert result == {"archived_at": "2025-01-01T00:00:00Z"}
    mock_state_manager.save_state.assert_not_called()


@pytest.mark.asyncio
async def test_archive_workflow_state_tenant_mismatch_raises(
    mock_state_manager, sample_state
):
    """Attempting to archive with mismatched tenant_id raises PermissionError."""
    mock_state_manager.load_state.return_value = sample_state
    workflow_metadata = {"wf-test-123": {"tenant_id": "tenant-alpha"}}

    with pytest.raises(
        PermissionError, match="belongs to tenant tenant-alpha, not tenant-bravo"
    ):
        await archive_workflow_state(
            state_manager=mock_state_manager,
            workflow_id="wf-test-123",
            workflow_metadata=workflow_metadata,
            tenant_id="tenant-bravo",
        )


@pytest.mark.asyncio
async def test_recover_orphaned_workflow_states(mock_state_manager, sample_state):
    """Orphaned workflows found in state manager are marked INTERRUPTED."""
    mock_state_manager.list_active_workflows.return_value = [
        "wf-orphan-1",
        "wf-active-2",
    ]
    sample_state.workflow_id = "wf-orphan-1"
    sample_state.status = WorkflowStatus.RUNNING
    sample_state.current_node = "analysis_step"
    mock_state_manager.load_state.return_value = sample_state

    recovered = await recover_orphaned_workflow_states(
        state_manager=mock_state_manager,
        active_workflow_ids={"wf-active-2"},
        format_enum=lambda e: getattr(e, "value", str(e)),
    )

    assert len(recovered) == 1
    assert recovered[0]["workflow_id"] == "wf-orphan-1"
    assert recovered[0]["status"] == WorkflowStatus.INTERRUPTED.value
    assert recovered[0]["recovery_available"] is True
    assert sample_state.status == WorkflowStatus.INTERRUPTED
    assert any("pod restart" in err for err in sample_state.errors)
    mock_state_manager.save_state.assert_awaited_once_with("wf-orphan-1", sample_state)


def test_compute_state_hash_deterministic(sample_state):
    """State hashing is deterministic across key ordering."""
    sample_state.metadata = {"b": 2, "a": 1}
    h1 = compute_state_hash(sample_state)
    sample_state.metadata = {"a": 1, "b": 2}
    h2 = compute_state_hash(sample_state)
    assert h1 == h2
    assert len(h1) == 64  # sha256


@pytest.mark.asyncio
async def test_resolve_resume_policy_conflict_raises(sample_state):
    """resolve_resume_policy raises CheckpointConflictError on hash mismatch."""
    controller = MagicMock()
    controller._compute_state_hash.return_value = "hash-actual-123"
    controller._get_latest_persisted_checkpoint_hash = AsyncMock(
        return_value="hash-persisted-456"
    )
    sample_state.metadata["checkpoint_hash"] = "hash-expected-789"

    with pytest.raises(CheckpointConflictError):
        await resolve_resume_policy(
            controller=controller,
            workflow_id="wf-test-123",
            state=sample_state,
            workflow_execution_error_type=WorkflowExecutionError,
            checkpoint_conflict_error_type=CheckpointConflictError,
        )
