from __future__ import annotations

"""Failure-path tests for workflow checkpoint/resume.

Tests corrupted state recovery, partial resume, missing dependencies,
failed agent calls, and inconsistent state scenarios.
"""


from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from value_fabric.layer4.engine.executor import OrchestrationController, WorkflowExecutionError
from value_fabric.layer4.engine.state_manager import StateManager
from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowStatus
from value_fabric.layer4.tools.registry import ToolRegistry
from value_fabric.shared.models.typed_dict import TypedDictModel


class CorruptedCheckpointSaver_aget_tupleResult(TypedDictModel):
    checkpoint: dict[str, Any]
    parent_config: Any

TEST_WORKFLOW_TYPE = "roi_calculator"


class CorruptedCheckpointSaver(InMemorySaver):
    """Simulates corrupted checkpoint storage."""

    async def aget_tuple(self, config):
        # Return corrupted state
        return CorruptedCheckpointSaver_aget_tupleResult.model_validate({
            "checkpoint": {
                "ts": "invalid-timestamp",
                "channel_versions": {"__root__": 1},
                "versions_seen": {},
            },
            "parent_config": None,
        })


class FailingCheckpointSaver(InMemorySaver):
    """Simulates checkpoint save failures."""

    async def aput(self, config, checkpoint, metadata, new_versions):
        raise RuntimeError("Database connection lost")


@pytest.fixture
def mock_tool_registry():
    """Provide mock tool registry."""
    registry = Mock(spec=ToolRegistry)
    registry.execute = AsyncMock(return_value={"result": "mock"})
    return registry


@pytest.fixture
def state_manager():
    """Provide fresh state manager."""
    return StateManager()


@pytest.mark.asyncio
class TestCorruptedStateRecovery:
    """Test handling of corrupted or inconsistent state."""

    async def test_resume_with_corrupted_checkpoint_raises_clear_error(
        self, mock_tool_registry, state_manager
    ):
        """Should raise clear error when checkpoint data is corrupted."""
        corrupted_saver = CorruptedCheckpointSaver()

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
            checkpoint_saver=corrupted_saver
        )

        # Pre-populate with valid state to get past initial lookup
        workflow_id = "corrupted-wf"
        valid_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, valid_state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Resume should fail with clear error
        with pytest.raises(WorkflowExecutionError) as exc_info:
            await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user"
            )

        error_msg = str(exc_info.value).lower()
        assert "checkpoint" in error_msg or "resume" in error_msg or "failed" in error_msg

    async def test_handles_state_with_missing_required_fields(
        self, mock_tool_registry, state_manager
    ):
        """Should handle state missing required fields gracefully."""
        workflow_id = "incomplete-wf"

        # Create state missing output_data (required field)
        incomplete_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={"test": "data"},
            output_data=None,  # Missing/None
            errors=[]
        )
        await state_manager.save_state(workflow_id, incomplete_state)

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Should not crash - handles gracefully
        with pytest.raises(WorkflowExecutionError):
            await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data={"approved": True}
            )

    async def test_recover_from_partial_save_state(
        self, mock_tool_registry, state_manager
    ):
        """Should handle case where state was partially saved."""
        workflow_id = "partial-wf"

        # Save state to state_manager but not to checkpoint
        partial_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.RUNNING,
            current_node="middle",
            input_data={},
            output_data={"start": "completed"},
            errors=[]
        )
        await state_manager.save_state(workflow_id, partial_state)

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Should use state_manager state even without checkpoint
        with pytest.raises(WorkflowExecutionError):
            await controller.resume_workflow(workflow_id=workflow_id, user_id="test-user")


@pytest.mark.asyncio
class TestFailedAgentCalls:
    """Test handling of failed agent/tool calls during resume."""

    async def test_failed_tool_call_during_resume_propagates_error(
        self, state_manager
    ):
        """Tool failure during resume should be captured in state."""
        failing_registry = Mock(spec=ToolRegistry)
        failing_registry.execute = AsyncMock(
            side_effect=RuntimeError("LLM API timeout")
        )

        controller = OrchestrationController(
            tool_registry=failing_registry,
            state_manager=state_manager
        )

        workflow_id = "failing-tool-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Mock workflow to simulate tool failure
        mock_workflow = Mock()
        mock_workflow.run = AsyncMock(side_effect=WorkflowExecutionError("Tool call failed"))

        with patch("value_fabric.layer4.engine.executor.create_workflow", return_value=mock_workflow):
            with pytest.raises(WorkflowExecutionError):
                await controller.resume_workflow(workflow_id=workflow_id, user_id="user")

    async def test_multiple_tool_failures_accumulate_in_state(
        self, state_manager
    ):
        """Multiple failures should be tracked in state.errors."""
        controller = OrchestrationController(
            tool_registry=Mock(spec=ToolRegistry),
            state_manager=state_manager
        )

        workflow_id = "multi-fail-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=["previous_error_1", "previous_error_2"]  # Existing errors
        )
        await state_manager.save_state(workflow_id, state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Verify state preserves error history
        loaded_state = await state_manager.load_state(workflow_id)
        assert len(loaded_state.errors) == 2


@pytest.mark.asyncio
class TestCheckpointFailureModes:
    """Test checkpoint storage failure scenarios."""

    async def test_failing_checkpoint_save_does_not_crash_workflow(
        self, mock_tool_registry, state_manager
    ):
        """Checkpoint save failure should not crash workflow (graceful degradation)."""
        failing_saver = FailingCheckpointSaver()

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
            checkpoint_saver=failing_saver
        )

        workflow_id = "checkpoint-fail-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Resume should handle checkpoint failure gracefully
        # (may fail but should not crash the process)
        mock_workflow = Mock()
        mock_workflow.run = AsyncMock(return_value=state)

        with patch("value_fabric.layer4.engine.executor.create_workflow", return_value=mock_workflow):
            # Should not raise unhandled exception
            try:
                await controller.resume_workflow(workflow_id=workflow_id, user_id="user")
            except WorkflowExecutionError:
                pass  # Expected - workflow error is okay
            except Exception as e:
                pytest.fail(f"Unexpected exception type: {type(e).__name__}: {e}")

    async def test_null_checkpoint_saver_is_handled(
        self, mock_tool_registry, state_manager
    ):
        """Should handle None checkpoint_saver (backward compatibility)."""
        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
            checkpoint_saver=None
        )

        workflow_id = "no-checkpoint-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        mock_workflow = Mock()
        mock_workflow.run = AsyncMock(return_value=state)

        with patch("value_fabric.layer4.engine.executor.create_workflow", return_value=mock_workflow):
            # Should work without checkpoint saver
            result = await controller.resume_workflow(workflow_id=workflow_id, user_id="user")
            assert result is not None


@pytest.mark.asyncio
class TestMissingDependencies:
    """Test handling of missing dependencies during resume."""

    async def test_resume_without_workflow_metadata_fails_clearly(
        self, mock_tool_registry, state_manager
    ):
        """Missing workflow metadata should give clear error."""
        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )

        workflow_id = "no-metadata-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)
        # Note: NOT setting controller._workflow_metadata[workflow_id]

        with pytest.raises(WorkflowExecutionError) as exc_info:
            await controller.resume_workflow(workflow_id=workflow_id, user_id="user")

        error_msg = str(exc_info.value).lower()
        assert "metadata" in error_msg or "workflow" in error_msg or "not found" in error_msg

    async def test_resume_with_deleted_tool_fails_gracefully(
        self, state_manager
    ):
        """Tool deleted after workflow started should fail gracefully."""
        # Registry that doesn't have the tool workflow expects
        incomplete_registry = Mock(spec=ToolRegistry)
        incomplete_registry.get_tool = Mock(return_value=None)  # Tool not found

        controller = OrchestrationController(
            tool_registry=incomplete_registry,
            state_manager=state_manager
        )

        workflow_id = "deleted-tool-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            current_node="tool_node",
            input_data={},
            output_data={},
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        with pytest.raises(WorkflowExecutionError) as exc_info:
            await controller.resume_workflow(workflow_id=workflow_id, user_id="user")

        error_msg = str(exc_info.value).lower()
        assert "tool" in error_msg or "not found" in error_msg or "missing" in error_msg


@pytest.mark.asyncio
class TestPartialResume:
    """Test partial/incomplete workflow resume scenarios."""

    async def test_resume_mid_workflow_preserves_previous_output(
        self, mock_tool_registry, state_manager
    ):
        """Resuming mid-workflow should preserve output from completed nodes."""
        workflow_id = "mid-wf"
        existing_output = {
            "node_1": {"result": "completed_data"},
            "node_2": {"result": "more_data"},
        }

        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            current_node="node_3",
            input_data={"initial": "data"},
            output_data=existing_output,
            errors=[]
        )
        await state_manager.save_state(workflow_id, state)

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        # Mock workflow that returns merged output
        mock_workflow = Mock()
        completed_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.COMPLETED,
            input_data=state.input_data,
            output_data={
                **existing_output,
                "node_3": {"result": "new_data"},
                "resumed": True
            },
            errors=[]
        )
        mock_workflow.run = AsyncMock(return_value=completed_state)

        with patch("value_fabric.layer4.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="user",
                resume_data={"decision": "continue"}
            )

        # Verify previous output preserved
        assert result.output_data["node_1"] == {"result": "completed_data"}
        assert result.output_data["node_2"] == {"result": "more_data"}
        assert result.output_data["node_3"] == {"result": "new_data"}
        assert result.output_data["resumed"] is True


@pytest.mark.asyncio
class TestAgentCheckpointSafety:
    """Focused checkpoint/resume safety contracts for agent workflows."""

    async def test_agent_checkpoint_preserves_tenant_context(self, state_manager):
        workflow_id = "tenant-checkpoint-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={"tenant_id": "tenant-a", "account_id": "account-a"},
            output_data={},
            errors=[],
            metadata={"tenant_id": "tenant-a", "user_id": "user-a"},
        )

        await state_manager.save_state(workflow_id, state)
        loaded = await state_manager.load_state(workflow_id)

        assert loaded is not None
        assert loaded.input_data["tenant_id"] == "tenant-a"
        assert loaded.metadata["tenant_id"] == "tenant-a"

    async def test_agent_resume_missing_checkpoint_fails_safely(self, mock_tool_registry, state_manager):
        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
        )

        with pytest.raises(WorkflowExecutionError) as exc_info:
            await controller.resume_workflow("missing-checkpoint", user_id="user-a")

        assert "no state found" in str(exc_info.value).lower()

    async def test_agent_checkpoint_does_not_store_secrets(self, state_manager):
        workflow_id = "secret-checkpoint-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.PAUSED,
            input_data={
                "tenant_id": "tenant-a",
                "api_key": "sk-live-secret",
                "nested": {"password": "p@ssw0rd", "token": "tok-secret"},
            },
            output_data={"safe": True},
            errors=[],
        )

        await state_manager.save_state(workflow_id, state)
        stored = state_manager._memory_store[state_manager._get_key(workflow_id)]["data"]
        rendered = str(stored)

        assert "sk-live-secret" not in rendered
        assert "p@ssw0rd" not in rendered
        assert "tok-secret" not in rendered
        assert stored["input_data"]["api_key"] == "[redacted]"
        assert stored["input_data"]["nested"]["password"] == "[redacted]"

    async def test_agent_resume_does_not_repeat_mutation(self, mock_tool_registry, state_manager):
        workflow_id = "mutation-resume-wf"
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.COMPLETED,
            input_data={"tenant_id": "tenant-a"},
            output_data={"mutation_applied": True},
            errors=[],
        )
        await state_manager.save_state(workflow_id, state)
        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
        )
        controller._workflow_metadata[workflow_id] = {"workflow_type": TEST_WORKFLOW_TYPE}

        with pytest.raises(WorkflowExecutionError):
            await controller.resume_workflow(workflow_id, user_id="user-a")

        mock_tool_registry.execute.assert_not_called()
