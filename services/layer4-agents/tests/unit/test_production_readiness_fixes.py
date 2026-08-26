from __future__ import annotations

"""Regression tests for Layer 4 production readiness fixes.

Covers critical bugs fixed during the production readiness pass:
- Settings import-time side effects
- StateManager in-memory fallback
- Pydantic v2 API compatibility
- Scheduler agent type resolution
- BaseWorkflow conditional routing
- OrchestrationController validation and timeout
- Checkpoint connection lifecycle
"""


import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from layer4_agents.api.routes.workflows import WorkflowEvent, WorkflowEventPayload
from layer4_agents.config.checkpoint import CheckpointConfig
from layer4_agents.engine.executor import OrchestrationController
from layer4_agents.engine.state_manager import StateManager
from layer4_agents.engine.types import ScheduledTask
from layer4_agents.models.agent_state import (
    BaseAgentState,
    WorkflowStatus,
    WorkflowType,
)
from layer4_agents.workflows.base import BaseWorkflow, WorkflowBuilder


class TestSettingsImportSafety:
    """Ensure settings can be imported without triggering side effects."""

    def test_settings_imports_without_infisical_crash(self):
        """Importing settings must not raise when Infisical is unconfigured."""
        # The fix moved load_infisical_secrets() into configure_settings() which
        # is only called during app lifespan.  Importing the module directly
        # must be safe.
        import importlib

        from layer4_agents.config import settings as settings_mod

        # Re-importing should not raise
        reloaded = importlib.reload(settings_mod)
        assert hasattr(reloaded, "Settings")
        assert hasattr(reloaded, "configure_settings")

    def test_configure_settings_is_idempotent(self):
        from layer4_agents.config.settings import configure_settings

        # Calling twice should not raise
        configure_settings()
        configure_settings()


class TestStateManagerInMemoryFallback:
    """StateManager must work without Redis (in-memory fallback)."""

    @pytest.fixture
    def manager(self):
        return StateManager(redis_client=None, max_memory_entries=5)

    @pytest.mark.asyncio
    async def test_lru_eviction_when_capacity_exceeded(self, manager):
        """Oldest entries must be evicted when in-memory capacity is exceeded."""
        from layer4_agents.models.agent_state import ROIAgentState

        for i in range(7):
            state = ROIAgentState(tenant_id="test-tenant", 
                workflow_id=f"wf-{i}",
                workflow_type=WorkflowType.ROI_CALCULATOR,
                status=WorkflowStatus.PENDING,
            )
            await manager.save_state(f"wf-{i}", state)

        # With max_memory_entries=5, wf-0 and wf-1 should have been evicted
        assert await manager.load_state("wf-0") is None
        assert await manager.load_state("wf-1") is None
        assert await manager.load_state("wf-2") is not None

    @pytest.mark.asyncio
    async def test_secret_redaction(self, manager):
        from layer4_agents.models.agent_state import ROIAgentState

        state = ROIAgentState(tenant_id="test-tenant", 
            workflow_id="wf-secret",
            workflow_type=WorkflowType.ROI_CALCULATOR,
            status=WorkflowStatus.PENDING,
            metadata={"api_key": "should-be-redacted", "normal": "value"},
        )
        await manager.save_state("wf-secret", state)

        raw = manager._memory_store["layer4:workflow:wf-secret"]["data"]
        assert raw["metadata"]["api_key"] == "[redacted]"
        assert raw["metadata"]["normal"] == "value"


class TestPydanticV2Compatibility:
    """Ensure all Pydantic models use v2 API."""

    def test_workflow_event_uses_model_dump(self):
        """WorkflowEvent must serialize with model_dump (not dict)."""
        event = WorkflowEvent(
            event_id="evt-1",
            event_type="status_update",
            timestamp="2024-01-15T10:00:00Z",
            message="test",
        )
        # model_dump() is the Pydantic v2 method
        data = event.model_dump()
        assert data["event_id"] == "evt-1"
        # Verify it can be JSON serialized
        json.dumps(data)

    def test_workflow_event_payload_uses_model_dump(self):
        payload = WorkflowEventPayload(
            id="wf-1",
            status="running",
            progress=50.0,
        )
        data = payload.model_dump()
        assert data["progress"] == 50.0


class TestSchedulerAgentTypeResolution:
    """distribute_task must resolve agent_type from BaseAgent, not dict."""

    @pytest.mark.asyncio
    async def test_distribute_task_gets_agent_type_from_baseagent(self):
        controller = OrchestrationController(tool_registry=Mock())
        agent = Mock()
        agent.agent_id = "agent-1"
        agent.agent_type = "TestAgent"
        controller._registered_agents["agent-1"] = agent
        controller.message_router.route_task = Mock(return_value="agent-1")
        controller.message_bus.publish = AsyncMock()

        # Patch scheduler.schedule_task to capture the task
        captured = []
        async def capture(task):
            captured.append(task)
        controller.scheduler.schedule_task = capture

        await controller.distribute_task(
            capability="test_cap",
            parameters={},
            tenant_id="tenant-1",
        )

        assert len(captured) == 1
        assert captured[0].agent_type == "TestAgent"

    @pytest.mark.asyncio
    async def test_distribute_task_unknown_agent_defaults_to_unknown(self):
        controller = OrchestrationController(tool_registry=Mock())
        controller.message_router.route_task = Mock(return_value="agent-1")
        controller.message_bus.publish = AsyncMock()

        captured = []
        async def capture(task):
            captured.append(task)
        controller.scheduler.schedule_task = capture

        await controller.distribute_task(
            capability="test_cap",
            parameters={},
            tenant_id="tenant-1",
        )

        assert captured[0].agent_type == "Unknown"


class TestBaseWorkflowConditionalRouting:
    """Conditional edges must return string keys, not booleans."""

    def test_router_returns_string_keys(self):
        from layer4_agents.models.workflow_config import EdgeConfig, EdgeType

        class FakeWorkflow(BaseWorkflow):
            def create_initial_state(self, input_data):
                return BaseAgentState(tenant_id="test-tenant", 
                    workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR
                )

        config = WorkflowBuilder("test", "Test").set_entry_point("start").build()
        workflow = FakeWorkflow(config, Mock())

        edge = EdgeConfig(
            source="start", target="end", edge_type=EdgeType.CONDITIONAL, condition="results_valid"
        )
        router = workflow._create_router(edge)

        # No errors → "continue"
        state_no_errors = BaseAgentState(tenant_id="test-tenant", 
            workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR, errors=[]
        )
        assert router(state_no_errors) == "continue"

        # Errors → "retry"
        state_with_errors = BaseAgentState(tenant_id="test-tenant", 
            workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR, errors=["boom"]
        )
        assert router(state_with_errors) == "retry"


class TestOrchestrationControllerValidation:
    """OrchestrationController must validate inputs and enforce timeouts."""

    @pytest.mark.asyncio
    async def test_execute_workflow_rejects_unknown_type(self):
        controller = OrchestrationController(tool_registry=Mock())
        with pytest.raises(Exception) as exc_info:
            await controller.execute_workflow(
                workflow_type="nonexistent_type",
                input_data={},
            )
        assert "nonexistent_type" in str(exc_info.value)
        assert "Unknown workflow type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_workflow_task_times_out(self):
        controller = OrchestrationController(tool_registry=Mock())
        controller.state_manager = StateManager()

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(10)

        workflow = AsyncMock()
        workflow.run = AsyncMock(side_effect=slow_run)

        task = ScheduledTask(
            priority=1,
            scheduled_time=datetime.now(UTC),
            task_id="task-1",
            workflow_instance_id="wf-1",
            capability="workflow_execution",
            agent_type="test",
            parameters={
                "workflow": workflow,
                "initial_state": BaseAgentState(tenant_id="test-tenant", 
                    workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR
                ),
                "workflow_id": "wf-1",
                "timeout_seconds": 0.01,
            },
        )

        with pytest.raises(Exception) as exc_info:
            await controller._run_workflow_task(task)

        assert "timeout" in str(exc_info.value).lower() or "exceeded" in str(
            exc_info.value
        ).lower()

    @pytest.mark.asyncio
    async def test_resolve_model_catches_connection_errors(self):
        controller = OrchestrationController(tool_registry=Mock())

        with patch(
            "layer4_agents.engine.executor.resolve_llm_model",
            side_effect=ConnectionError("DB down"),
        ):
            model = await controller.resolve_model(
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            )

        # Must fallback to env default
        assert model == "gpt-4o"


class TestCheckpointConnectionLifecycle:
    """CheckpointConfig must manage connections safely."""

    @pytest.mark.asyncio
    async def test_close_saver_handles_none(self):
        # Should not raise
        await CheckpointConfig.close_saver(None)

    @pytest.mark.asyncio
    async def test_close_saver_handles_already_closed(self):
        saver = Mock()
        saver.conn = AsyncMock()
        saver.conn.close = AsyncMock(side_effect=RuntimeError("already closed"))
        # Should not raise despite the underlying error
        await CheckpointConfig.close_saver(saver)

    @pytest.mark.asyncio
    async def test_close_saver_prefers_public_conn(self):
        saver = Mock()
        saver.conn = AsyncMock()
        saver._conn = AsyncMock()
        await CheckpointConfig.close_saver(saver)
        saver.conn.close.assert_awaited_once()
        saver._conn.close.assert_not_awaited()
