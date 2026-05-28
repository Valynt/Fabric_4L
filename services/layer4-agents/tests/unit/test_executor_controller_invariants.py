"""Production-invariant tests for OrchestrationController.

Covers deterministic hashing, timeout resolution, lifecycle state transitions,
status guards, and early validation gates — all without a real scheduler
or message bus.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from value_fabric.layer4.engine.executor import (
    CheckpointConflictError,
    OrchestrationController,
    WorkflowExecutionError,
)
from value_fabric.layer4.models.agent_state import (
    ROIAgentState,
    WorkflowStatus,
    WorkflowType,
)
from value_fabric.layer4.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_controller() -> OrchestrationController:
    """Return an unstarted controller with an in-memory state manager."""
    return OrchestrationController(tool_registry=ToolRegistry())


def _running_state(workflow_id: str = "wf-1") -> ROIAgentState:
    state = ROIAgentState(
        tenant_id="tenant-a",
        workflow_id=workflow_id,
        workflow_type=WorkflowType.ROI_CALCULATOR,
    )
    state.status = WorkflowStatus.RUNNING
    state.started_at = datetime.now(UTC)
    return state


# ============================================================================
# OrchestrationController – state hash determinism
# ============================================================================

class TestStateHashDeterminism:
    """Tests for _compute_state_hash — checkpoint conflict detection."""

    @pytest.mark.unit
    def test_same_state_produces_same_hash(self):
        controller = _minimal_controller()
        state = _running_state()
        h1 = controller._compute_state_hash(state)
        h2 = controller._compute_state_hash(state)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    @pytest.mark.unit
    def test_different_workflow_ids_produce_different_hashes(self):
        controller = _minimal_controller()
        a = _running_state("wf-a")
        b = _running_state("wf-b")
        assert controller._compute_state_hash(a) != controller._compute_state_hash(b)

    @pytest.mark.unit
    def test_mutation_changes_hash(self):
        controller = _minimal_controller()
        state = _running_state()
        h1 = controller._compute_state_hash(state)
        state.status = WorkflowStatus.COMPLETED
        h2 = controller._compute_state_hash(state)
        assert h1 != h2


# ============================================================================
# OrchestrationController – tenant timeout resolution
# ============================================================================

class TestTenantTimeoutResolution:
    """Tests for _extract_tenant_timeout and _resolve_workflow_timeout_seconds."""

    @pytest.mark.unit
    def test_extract_tenant_timeout_none_settings(self):
        controller = _minimal_controller()
        assert controller._extract_tenant_timeout(None) is None

    @pytest.mark.unit
    def test_extract_tenant_timeout_nested_path(self):
        controller = _minimal_controller()
        settings = {"layer4": {"workflow": {"timeout_seconds": 900}}}
        assert controller._extract_tenant_timeout(settings) == 900

    @pytest.mark.unit
    def test_extract_tenant_timeout_flat_path(self):
        controller = _minimal_controller()
        settings = {"workflow_timeout_seconds": 600}
        assert controller._extract_tenant_timeout(settings) == 600

    @pytest.mark.unit
    def test_extract_tenant_timeout_missing_key(self):
        controller = _minimal_controller()
        settings = {"layer4": {"workflow": {}}}
        assert controller._extract_tenant_timeout(settings) is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resolve_timeout_uses_service_default_when_no_tenant(self):
        controller = _minimal_controller()
        seconds, source = await controller._resolve_workflow_timeout_seconds(None)
        assert source == "service_default"
        assert isinstance(seconds, int)
        assert seconds > 0


# ============================================================================
# OrchestrationController – progress calculation
# ============================================================================

class TestProgressCalculation:
    """Tests for _calculate_progress."""

    @pytest.mark.unit
    def test_progress_by_status(self):
        controller = _minimal_controller()
        expectations = {
            WorkflowStatus.PENDING: 0,
            WorkflowStatus.RUNNING: 50,
            WorkflowStatus.PAUSED: 50,
            WorkflowStatus.INTERRUPTED: 25,
            WorkflowStatus.COMPLETED: 100,
            WorkflowStatus.FAILED: 100,
            WorkflowStatus.CANCELLED: 100,
        }
        for status, expected in expectations.items():
            state = _running_state()
            state.status = status
            assert controller._calculate_progress(state) == expected


# ============================================================================
# OrchestrationController – lifecycle (start / stop)
# ============================================================================

class TestLifecycle:
    """Tests for start, stop, and interruption semantics."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        controller = _minimal_controller()
        await controller.start()
        assert controller._started is True
        # Second call should not raise
        await controller.start()
        assert controller._started is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_is_noop_when_not_started(self):
        controller = _minimal_controller()
        # Should not raise
        await controller.stop()
        assert controller._started is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_marks_active_workflows_interrupted(self):
        controller = _minimal_controller()
        await controller.start()

        # Seed a RUNNING workflow in state manager
        state = _running_state("wf-active")
        await controller.state_manager.save_state("wf-active", state)

        # Simulate an active asyncio.Task reference
        fake_task = asyncio.create_task(asyncio.sleep(10))
        controller._active_workflows["wf-active"] = fake_task

        await controller.stop()

        # State should be INTERRUPTED with metadata
        updated = await controller.state_manager.load_state("wf-active")
        assert updated is not None
        assert updated.status == WorkflowStatus.INTERRUPTED
        assert "interrupted_at" in updated.metadata
        assert updated.metadata["interruption_reason"] == "controller shutdown"
        fake_task.cancel()
        try:
            await fake_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# OrchestrationController – cancel_workflow
# ============================================================================

class TestCancelWorkflow:
    """Tests for cancel_workflow state transitions."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_updates_state_to_cancelled(self):
        controller = _minimal_controller()
        await controller.start()
        state = _running_state("wf-cancel")
        await controller.state_manager.save_state("wf-cancel", state)

        # Mock scheduler cancel to return True (as a coroutine)
        async def _mock_cancel(*_a, **_k):
            return True

        controller.scheduler.cancel_task = _mock_cancel  # type: ignore[method-assign]

        result = await controller.cancel_workflow("wf-cancel", reason="user request")
        assert result is True

        updated = await controller.state_manager.load_state("wf-cancel")
        assert updated is not None
        assert updated.status == WorkflowStatus.CANCELLED
        assert updated.completed_at is not None


# ============================================================================
# OrchestrationController – pause_workflow
# ============================================================================

class TestPauseWorkflow:
    """Tests for pause_workflow status guards and state mutation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pause_running_workflow(self):
        controller = _minimal_controller()
        await controller.start()
        state = _running_state("wf-pause")
        await controller.state_manager.save_state("wf-pause", state)

        async def _mock_cancel(*_a, **_k):
            return True

        controller.scheduler.cancel_task = _mock_cancel  # type: ignore[method-assign]

        result = await controller.pause_workflow("wf-pause", user_id="alice", reason="review")
        assert result is True

        updated = await controller.state_manager.load_state("wf-pause")
        assert updated is not None
        assert updated.status == WorkflowStatus.INTERRUPTED
        assert updated.paused_by == "alice"
        assert updated.pause_count == 1
        assert updated.metadata["pause_reason"] == "review"
        assert "checkpoint_hash" in updated.metadata

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pause_completed_workflow_raises(self):
        controller = _minimal_controller()
        state = _running_state("wf-done")
        state.status = WorkflowStatus.COMPLETED
        await controller.state_manager.save_state("wf-done", state)

        with pytest.raises(ValueError, match="cannot be paused"):
            await controller.pause_workflow("wf-done", user_id="alice")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pause_already_interrupted_raises(self):
        controller = _minimal_controller()
        state = _running_state("wf-int")
        state.status = WorkflowStatus.INTERRUPTED
        await controller.state_manager.save_state("wf-int", state)

        with pytest.raises(ValueError, match="already interrupted"):
            await controller.pause_workflow("wf-int", user_id="alice")


# ============================================================================
# OrchestrationController – archive_workflow
# ============================================================================

class TestArchiveWorkflow:
    """Tests for archive_workflow tenant ownership and idempotency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_sets_metadata(self):
        controller = _minimal_controller()
        state = _running_state("wf-archive")
        await controller.state_manager.save_state("wf-archive", state)
        controller._workflow_metadata["wf-archive"] = {"tenant_id": "tenant-a"}

        result = await controller.archive_workflow("wf-archive")
        assert result is not None
        assert "archived_at" in result

        updated = await controller.state_manager.load_state("wf-archive")
        assert updated is not None
        assert updated.metadata.get("archived") is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_is_idempotent(self):
        controller = _minimal_controller()
        state = _running_state("wf-archive")
        await controller.state_manager.save_state("wf-archive", state)
        controller._workflow_metadata["wf-archive"] = {"tenant_id": "tenant-a"}

        first = await controller.archive_workflow("wf-archive")
        second = await controller.archive_workflow("wf-archive")
        assert first == second

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_enforces_tenant_ownership(self):
        controller = _minimal_controller()
        state = _running_state("wf-archive")
        await controller.state_manager.save_state("wf-archive", state)
        controller._workflow_metadata["wf-archive"] = {"tenant_id": "tenant-a"}

        with pytest.raises(PermissionError, match="belongs to tenant"):
            await controller.archive_workflow("wf-archive", tenant_id="tenant-b")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_missing_workflow_returns_none(self):
        controller = _minimal_controller()
        result = await controller.archive_workflow("missing")
        assert result is None


# ============================================================================
# OrchestrationController – execute_workflow early validation
# ============================================================================

class TestExecuteWorkflowValidation:
    """Tests for execute_workflow input validation gates."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejects_missing_tenant_id(self):
        controller = _minimal_controller()
        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.execute_workflow(
                workflow_type="roi_calculator",
                input_data={},
                tenant_id=None,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejects_blank_tenant_id(self):
        controller = _minimal_controller()
        with pytest.raises(WorkflowExecutionError, match="tenant_id is required"):
            await controller.execute_workflow(
                workflow_type="roi_calculator",
                input_data={},
                tenant_id="   ",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejects_unknown_workflow_type(self):
        controller = _minimal_controller()
        with pytest.raises(WorkflowExecutionError, match="Unknown workflow type"):
            await controller.execute_workflow(
                workflow_type="evil_type",
                input_data={},
                tenant_id="tenant-a",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejects_when_shutdown(self):
        controller = _minimal_controller()
        controller._shutdown = True
        with pytest.raises(WorkflowExecutionError, match="shutting down"):
            await controller.execute_workflow(
                workflow_type="roi_calculator",
                input_data={},
                tenant_id="tenant-a",
            )
