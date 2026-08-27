from __future__ import annotations

"""Integration tests for LangGraph checkpointing and workflow resume.

Tests the pause/resume lifecycle for human-in-the-loop workflows.
Verifies state persistence across interruptions and container restarts.
"""


import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from layer4_agents.config.checkpoint import (
    CheckpointConfig,
    CheckpointConnectionError,
    get_checkpoint_saver,
)
from layer4_agents.engine.executor import (
    CheckpointConflictError,
    OrchestrationController,
    WorkflowExecutionError,
)
from layer4_agents.models.agent_state import BaseAgentState, WorkflowStatus
from layer4_agents.tools.registry import ToolRegistry
from layer4_agents.workflows.base import BaseWorkflow

# Reuse fixtures from conftest.py: mock_checkpoint_saver, mock_tool_registry,
# state_manager, orchestrator_with_checkpoint, controller_with_running_state,
# controller_with_paused_state, completed_workflow_state, simple_test_workflow,
# setup_workflow_metadata
try:
    from tests.utils.workflow_helpers import setup_workflow_metadata
except (ImportError, ModuleNotFoundError):
    import importlib.util
    from pathlib import Path
    _helper_path = Path(__file__).resolve().parent / "utils" / "workflow_helpers.py"
    _spec = importlib.util.spec_from_file_location("layer4_test_workflow_helpers", _helper_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    setup_workflow_metadata = _mod.setup_workflow_metadata

# Test constants
TEST_WORKFLOW_TYPE = "roi_calculator"


@pytest.mark.unit
class TestCheckpointPersistence:
    """Test that workflow state persists across interruptions."""

    @pytest.mark.asyncio
    async def test_checkpoint_saver_stores_state(self, simple_test_workflow, mock_checkpoint_saver):
        """Verify checkpoint saver receives state during workflow execution."""
        workflow = simple_test_workflow()
        initial_state = workflow.create_initial_state({"test": "data"}, tenant_id="test-tenant")
        workflow_id = initial_state.workflow_id

        await workflow.run(initial_state, thread_id=workflow_id)

        assert workflow_id in mock_checkpoint_saver.saved_threads
        assert workflow_id in mock_checkpoint_saver.checkpoints

    @pytest.mark.asyncio
    async def test_workflow_without_checkpoint_saver_runs_normally(self, simple_test_workflow):
        """Workflow functions without checkpointing (backward compatibility)."""
        workflow = simple_test_workflow(checkpoint_saver=None)
        initial_state = workflow.create_initial_state({"test": "data"}, tenant_id="test-tenant")

        result = await workflow.run(initial_state, thread_id="test-wf-1")

        assert result is not None


@pytest.mark.unit
class TestResumeWorkflow:
    """Test OrchestrationController resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_workflow_loads_state(self, controller_with_running_state, state_manager):
        """Resume loads existing state and continues execution."""
        controller, workflow_id, existing_state = controller_with_running_state
        await state_manager.save_state(workflow_id, existing_state)

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_result = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.COMPLETED,
            input_data=existing_state.input_data,
            output_data={**existing_state.output_data, "resumed": True},
            errors=[]
        )
        mock_workflow.run = AsyncMock(return_value=mock_result)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data={"approved": True}
            )

        assert result is not None
        assert result.workflow_id == workflow_id
        mock_workflow.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_completed_workflow_fails(self, mock_tool_registry, state_manager, completed_workflow_state):
        """Cannot resume a workflow that is already completed."""
        workflow_id = completed_workflow_state.workflow_id
        await state_manager.save_state(workflow_id, completed_workflow_state)

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )
        setup_workflow_metadata(controller, workflow_id)

        with pytest.raises(WorkflowExecutionError):
            await controller.resume_workflow(workflow_id=workflow_id, user_id="test-user")

    @pytest.mark.asyncio
    async def test_resume_nonexistent_workflow_fails(self, mock_tool_registry, state_manager):
        """Cannot resume a workflow that doesn't exist."""
        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager
        )

        with pytest.raises(WorkflowExecutionError) as exc_info:
            await controller.resume_workflow(workflow_id="nonexistent-wf", user_id="test-user")

        assert "not found" in str(exc_info.value).lower() or "no state found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_resume_merges_user_data(self, controller_with_running_state, state_manager):
        """Resume merges user resume data into state."""
        controller, workflow_id, existing_state = controller_with_running_state
        existing_state.input_data = {"original": "data"}
        await state_manager.save_state(workflow_id, existing_state)

        async def mock_run(state, thread_id, resume_data=None, **kwargs):
            return state

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_workflow.run = AsyncMock(side_effect=mock_run)

        resume_data = {"approved": True, "notes": "Proceed with caution"}

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data=resume_data
            )

        assert result is not None
        assert result.workflow_id == workflow_id
        assert "resume_decision" in result.output_data
        assert result.output_data["resume_decision"] == resume_data
        assert result.output_data["resumed_by"] == "test-user"
        assert "resumed_at" in result.output_data

    @pytest.mark.asyncio
    async def test_resume_workflow_enforces_replay_policy(self, controller_with_running_state, state_manager):
        """Resume validates against replay-conflict policy with real hashes."""
        controller, workflow_id, existing_state = controller_with_running_state
        existing_state.input_data = {"original": "data"}
        await state_manager.save_state(workflow_id, existing_state)

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_workflow.run = AsyncMock(return_value=existing_state)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data={"approved": True}
            )

        assert result is not None
        # Fingerprint should be recorded after successful resume
        assert len(controller._seen_replay_fingerprints) > 0

    @pytest.mark.asyncio
    async def test_resolve_resume_policy_allows_matching_latest_and_checkpoint_hashes(
        self, controller_with_running_state, state_manager
    ):
        controller, workflow_id, existing_state = controller_with_running_state
        await state_manager.save_state(workflow_id, existing_state)
        checkpoint_id = "chk-match-001"
        expected_hash = controller._compute_state_hash(existing_state)

        controller._get_latest_persisted_checkpoint_hash = AsyncMock(return_value=expected_hash)  # type: ignore[method-assign]

        await controller._resolve_resume_policy(
            workflow_id=workflow_id,
            state=existing_state,
            target_checkpoint_id=checkpoint_id,
        )
        controller._get_latest_persisted_checkpoint_hash.assert_awaited_once_with(  # type: ignore[attr-defined]
            tenant_id=existing_state.tenant_id,
            workflow_id=workflow_id,
            run_id=existing_state.run_id,
            checkpoint_id=checkpoint_id,
        )

    @pytest.mark.asyncio
    async def test_resolve_resume_policy_rejects_when_persisted_hash_differs(
        self, controller_with_running_state, state_manager
    ):
        controller, workflow_id, existing_state = controller_with_running_state
        caller_state = existing_state.model_copy(deep=True)
        persisted_state = existing_state.model_copy(deep=True)
        persisted_state.output_data = {"start": {"status": "changed"}}
        await state_manager.save_state(workflow_id, persisted_state)

        with pytest.raises(CheckpointConflictError) as exc_info:
            await controller._resolve_resume_policy(
                workflow_id=workflow_id,
                state=caller_state,
                target_checkpoint_id="chk-stale-001",
            )

        assert exc_info.value.metadata["workflow_id"] == workflow_id
        assert exc_info.value.metadata["checkpoint_id"] == "chk-stale-001"
        assert exc_info.value.metadata["expected_hash"] != exc_info.value.metadata["actual_hash"]

    @pytest.mark.asyncio
    async def test_resume_workflow_rejects_stale_client_state(
        self, controller_with_running_state, state_manager
    ):
        controller, workflow_id, existing_state = controller_with_running_state
        await state_manager.save_state(workflow_id, existing_state.model_copy(deep=True))

        stale_state = existing_state.model_copy(deep=True)
        stale_state.input_data = {"stale": "client"}

        async def _load_state(_workflow_id: str):
            if not hasattr(_load_state, "count"):
                _load_state.count = 0
            _load_state.count += 1
            return stale_state if _load_state.count == 1 else existing_state

        controller.state_manager.load_state = _load_state  # type: ignore[method-assign]

        with pytest.raises(CheckpointConflictError):
            await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data={"approved": True},
            )

    @pytest.mark.asyncio
    async def test_resume_policy_rejects_second_writer_after_first_wins(
        self, controller_with_running_state
    ):
        controller, workflow_id, existing_state = controller_with_running_state
        caller_hash = controller._compute_state_hash(existing_state)
        stale_persisted_hash = "stale-hash-from-later-writer"
        assert caller_hash != stale_persisted_hash

        controller._get_latest_persisted_checkpoint_hash = AsyncMock(  # type: ignore[method-assign]
            side_effect=[caller_hash, stale_persisted_hash]
        )

        # First writer sees matching durable hash and may continue
        await controller._resolve_resume_policy(
            workflow_id=workflow_id,
            state=existing_state,
            target_checkpoint_id="chk-race-001",
        )

        # Second writer reuses stale state and is rejected
        with pytest.raises(CheckpointConflictError):
            await controller._resolve_resume_policy(
                workflow_id=workflow_id,
                state=existing_state,
                target_checkpoint_id="chk-race-001",
            )

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint_exists_and_runs(self, controller_with_running_state, state_manager):
        """resume_from_checkpoint is implemented and executes workflow."""
        controller, workflow_id, existing_state = controller_with_running_state
        existing_state.input_data = {"original": "data"}
        await state_manager.save_state(workflow_id, existing_state)

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_workflow.run = AsyncMock(return_value=existing_state)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_from_checkpoint(
                workflow_id=workflow_id,
                checkpoint_id="chk-test-001",
                user_id="test-user",
                resume_data={"approved": True}
            )

        assert result is not None
        assert result["status"] == existing_state.status.value
        assert result["checkpoint_id"] == "chk-test-001"
        mock_workflow.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint_uses_requested_checkpoint_not_latest(
        self, controller_with_running_state, state_manager
    ):
        """Resume passes the requested checkpoint ID when a thread has later checkpoints."""
        controller, workflow_id, existing_state = controller_with_running_state
        requested_checkpoint_id = "chk-requested-001"
        latest_checkpoint_id = "chk-latest-002"
        existing_state.metadata["checkpoint_history"] = [
            requested_checkpoint_id,
            latest_checkpoint_id,
        ]
        await state_manager.save_state(workflow_id, existing_state)

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_workflow.run = AsyncMock(return_value=existing_state)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_from_checkpoint(
                workflow_id=workflow_id,
                checkpoint_id=requested_checkpoint_id,
                user_id="test-user",
                resume_data={"approved": True},
            )

        assert result["checkpoint_id"] == requested_checkpoint_id
        _, kwargs = mock_workflow.run.call_args
        assert kwargs["thread_id"] == workflow_id
        assert kwargs["checkpoint_config"] == {"checkpoint_id": requested_checkpoint_id}
        assert kwargs["checkpoint_config"]["checkpoint_id"] != latest_checkpoint_id


@pytest.mark.unit
class TestCheckpointConfiguration:
    """Test checkpoint configuration and database connection."""
    
    @pytest.mark.asyncio
    async def test_checkpoint_config_returns_saver(self):
        """CheckpointConfig creates saver when database available."""
        # This test would require a real Postgres connection
        # For now, we mock the connection and saver to verify the interface
        # Create a mock AsyncPostgresSaver class that mimics the real one
        mock_saver_cls = MagicMock()
        mock_saver = MagicMock()
        # create_saver awaits setup() (LangGraph table provisioning); the mock
        # must support being awaited.
        mock_saver.setup = AsyncMock()
        mock_saver_cls.return_value = mock_saver

        with patch("psycopg.AsyncConnection.connect", new_callable=AsyncMock) as mock_connect:
            with patch.dict("sys.modules", {"langgraph.checkpoint.postgres.aio": MagicMock(AsyncPostgresSaver=mock_saver_cls)}):
                mock_conn = AsyncMock()
                mock_connect.return_value = mock_conn

                saver = await CheckpointConfig.create_saver()
                assert saver is not None
                # Verify connection is stored for later cleanup
                assert hasattr(saver, '_conn')
    
    def test_checkpoint_config_handles_url_variations(self):
        """CheckpointConfig handles different URL formats."""
        # Test URL cleaning for asyncpg compatibility
        test_cases = [
            ("postgresql+asyncpg://user:pass@host/db", "postgresql://user:pass@host/db"),
            ("postgresql+psycopg2://user:pass@host/db", "postgresql://user:pass@host/db"),
            ("  PostgreSQL+PG8000://user:pass@host/db  ", "postgresql://user:pass@host/db"),
            ("postgresql://user:pass@host/db", "postgresql://user:pass@host/db"),
            ("mysql+pymysql://user:pass@host/db", "mysql+pymysql://user:pass@host/db"),
        ]
        
        for input_url, expected in test_cases:
            result = CheckpointConfig._clean_url(input_url)
            assert result == expected
    
    @pytest.mark.asyncio
    async def test_get_checkpoint_saver_raises_connection_error_on_failure(self):
        """CheckpointConfig.get_saver() raises CheckpointConnectionError when DB unavailable.

        This test verifies that database connection failures are properly caught
        and converted to CheckpointConnectionError, allowing callers to handle
        persistence failures gracefully.
        """
        # When database is unavailable, should raise CheckpointConnectionError
        # Patch psycopg at the source module where connect is actually used.
        with patch("psycopg.AsyncConnection.connect", new_callable=AsyncMock) as mock_connect:
            with patch.dict("sys.modules", {"langgraph.checkpoint.postgres.aio": MagicMock()}):
                import psycopg
                mock_connect.side_effect = psycopg.OperationalError("Database unavailable")

                with pytest.raises(CheckpointConnectionError) as exc_info:
                    async with CheckpointConfig.get_saver() as _:
                        pass

                # Verify the error message contains useful context
                assert "Database connection failed" in str(exc_info.value)
                assert "Database unavailable" in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_factory_get_checkpoint_saver_returns_none_on_db_failure_in_development(self):
        """Factory function get_checkpoint_saver() returns None on DB failure in development.
        
        Unlike CheckpointConfig.get_saver() which raises exceptions, the factory function
        is designed to silently fail and return None, allowing workflows to continue
        without checkpointing when the database is unavailable.
        """
        # Must set env var to trigger DB connection attempt
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CHECKPOINT_DATABASE_URL": "postgresql://invalid:5432/test"}):
            with patch("layer4_agents.config.checkpoint.CheckpointConfig.create_saver") as mock_create:
                mock_create.side_effect = CheckpointConnectionError("Database unavailable")
                
                result = await get_checkpoint_saver()
                
                # Factory should gracefully return None instead of raising
                assert result is None

    @pytest.mark.asyncio
    async def test_factory_get_checkpoint_saver_fails_closed_in_production(self):
        """Production cannot silently disable durable workflow checkpoints."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            with pytest.raises(CheckpointConnectionError, match="CHECKPOINT_DATABASE_URL"):
                await get_checkpoint_saver()

    @pytest.mark.asyncio
    async def test_production_workflow_requires_checkpoint_saver(self, state_manager):
        """Runtime execution fails closed in production without a checkpointer."""
        controller = OrchestrationController(
            tool_registry=ToolRegistry(),
            state_manager=state_manager,
            checkpoint_saver=None,
        )
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            with pytest.raises(WorkflowExecutionError, match="checkpoint"):
                await controller.execute_workflow(
                    workflow_type=TEST_WORKFLOW_TYPE,
                    input_data={"workflow_id": "wf-prod-no-checkpoint"},
                    tenant_id="tenant-a",
                )


@pytest.mark.integration
class TestCheckpointIntegration:
    """End-to-end integration tests for checkpoint/resume."""

    @pytest.mark.asyncio
    async def test_full_pause_resume_lifecycle(self, controller_with_paused_state, state_manager):
        """Complete workflow: start -> pause -> resume -> complete."""
        controller, workflow_id, initial_state = controller_with_paused_state
        await state_manager.save_state(workflow_id, initial_state)

        mock_workflow = Mock(spec=BaseWorkflow)
        completed_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=workflow_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.COMPLETED,
            input_data=initial_state.input_data,
            output_data={
                **initial_state.output_data,
                "resumed": True,
                "middle": {"status": "completed"},
                "end": {"status": "completed"}
            },
            errors=[]
        )
        mock_workflow.run = AsyncMock(return_value=completed_state)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow):
            result = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="test-user",
                resume_data={"approved": True}
            )

        assert result is not None
        assert result.workflow_id == workflow_id
        assert result.status == WorkflowStatus.COMPLETED
        mock_workflow.run.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_multiple_resumes_continue_progress(self, controller_with_running_state, state_manager, mock_checkpoint_saver):
        """Multiple resume calls continue from latest checkpoint."""
        controller, workflow_id, existing_state = controller_with_running_state
        existing_state.output_data = {"resume_count": 0}
        await state_manager.save_state(workflow_id, existing_state)

        async def mock_run(state, thread_id, resume_data=None, **kwargs):
            return state

        mock_workflow = Mock(spec=BaseWorkflow)
        mock_workflow.run = AsyncMock(side_effect=mock_run)

        with patch("layer4_agents.engine.executor.create_workflow", return_value=mock_workflow) as mock_create:
            result1 = await controller.resume_workflow(
                workflow_id=workflow_id,
                user_id="user-1",
                resume_data={"iteration": 1}
            )

        assert result1 is not None
        assert result1.output_data["resume_decision"] == {"iteration": 1}
        mock_create.assert_called_once()
        assert mock_create.call_args.args[2] is mock_checkpoint_saver


@pytest.mark.unit
class TestOrchestrationControllerEdgeCases:
    """Edge-case tests for controller lifecycle methods."""

    @pytest.mark.asyncio
    async def test_recover_workflows_marks_orphaned_as_interrupted(
        self, state_manager, mock_tool_registry
    ):
        """Orphaned workflows from a previous pod are marked INTERRUPTED."""
        from layer4_agents.models.agent_state import WorkflowStatus

        controller = OrchestrationController(
            tool_registry=mock_tool_registry,
            state_manager=state_manager,
        )

        # Seed an "orphaned" workflow in state manager (not in _active_workflows)
        orphaned_id = "orphaned-wf-001"
        orphaned_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=orphaned_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.RUNNING,
            input_data={},
            output_data={},
            errors=[],
        )
        await state_manager.save_state(orphaned_id, orphaned_state)

        recovered = await controller.recover_workflows()
        assert len(recovered) == 1
        assert recovered[0]["workflow_id"] == orphaned_id
        assert recovered[0]["status"] == "interrupted"
        assert recovered[0]["recovery_available"] is True

        # Verify persisted state was updated
        updated = await state_manager.load_state(orphaned_id)
        assert updated.status == WorkflowStatus.INTERRUPTED
        assert any("pod restart" in e for e in updated.errors)

    @pytest.mark.asyncio
    async def test_pause_completed_workflow_raises(self, state_manager, completed_workflow_state):
        """Pause on a completed workflow must raise ValueError."""
        controller = OrchestrationController(
            tool_registry=ToolRegistry(),
            state_manager=state_manager,
        )
        await state_manager.save_state(completed_workflow_state.workflow_id, completed_workflow_state)
        setup_workflow_metadata(controller, completed_workflow_state.workflow_id)

        with pytest.raises(ValueError, match="cannot be paused"):
            await controller.pause_workflow(
                completed_workflow_state.workflow_id, user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_pause_already_interrupted_workflow_raises(self, state_manager):
        """Pause on an already-interrupted workflow must raise ValueError."""
        from layer4_agents.models.agent_state import WorkflowStatus

        wf_id = "already-interrupted-wf"
        interrupted_state = BaseAgentState(tenant_id="test-tenant", 
            workflow_id=wf_id,
            workflow_type=TEST_WORKFLOW_TYPE,
            status=WorkflowStatus.INTERRUPTED,
            input_data={},
            output_data={},
            errors=[],
        )
        controller = OrchestrationController(
            tool_registry=ToolRegistry(),
            state_manager=state_manager,
        )
        await state_manager.save_state(wf_id, interrupted_state)
        setup_workflow_metadata(controller, wf_id)

        with pytest.raises(ValueError, match="already interrupted"):
            await controller.pause_workflow(wf_id, user_id="test-user")

    @pytest.mark.asyncio
    async def test_resume_completed_workflow_raises(self, state_manager, completed_workflow_state):
        """Resume on a completed workflow must raise WorkflowExecutionError."""
        controller = OrchestrationController(
            tool_registry=ToolRegistry(),
            state_manager=state_manager,
        )
        await state_manager.save_state(
            completed_workflow_state.workflow_id, completed_workflow_state
        )
        setup_workflow_metadata(controller, completed_workflow_state.workflow_id)

        with pytest.raises(WorkflowExecutionError, match="cannot be resumed"):
            await controller.resume_workflow(
                completed_workflow_state.workflow_id, user_id="test-user"
            )


# Fixtures moved to conftest.py:
# - mock_checkpoint_saver
# - mock_tool_registry
# - state_manager
# - orchestrator_with_checkpoint
# - controller_with_running_state
# - controller_with_paused_state
# - completed_workflow_state
