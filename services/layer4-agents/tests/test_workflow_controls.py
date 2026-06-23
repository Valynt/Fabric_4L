from __future__ import annotations

"""Tests for workflow control endpoints: pause, resume, and edge cases.

API-level async tests via httpx.AsyncClient that validate public contract/status behavior.
"""


from datetime import UTC, datetime
from typing import Annotated, Any
from unittest.mock import MagicMock

import pytest
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel


class MockOrchestrationController_get_workflow_statusResult(TypedDictModel):
    current_node: Any
    progress_percentage: Any
    started_at: Any
    status: Any
    tenant_id: Any
    user_id: Any
    workflow_id: Any


class get_workflow_eventsResult(TypedDictModel):
    events: list[Any]
    workflow_id: Any


class WorkflowPauseRequest(BaseModel):
    user_id: str = Field(..., description="User pausing the workflow")
    reason: str | None = Field(None, description="Reason for pausing")
    tenant_id: str | None = None


class WorkflowPauseResponse(BaseModel):
    workflow_instance_id: str = Field(..., alias="workflow_instance_id")
    status: str = Field(..., description="paused")
    paused_at: str = Field(..., description="ISO timestamp when paused")
    current_node: str | None = Field(None, description="Current node when paused")
    message: str

    model_config = ConfigDict(populate_by_name=True)


class WorkflowResumeRequest(BaseModel):
    user_id: str = Field(..., description="User resuming the workflow")
    resume_data: dict | None = Field(default_factory=dict)
    tenant_id: str | None = None


class WorkflowResumeResponse(BaseModel):
    workflow_instance_id: str = Field(..., alias="workflow_instance_id")
    status: str = Field(..., description="resumed, completed, or failed")
    resumed_from_node: str | None = Field(None, description="Node from which execution resumed")
    message: str
    estimated_completion_seconds: int = Field(default=60)

    model_config = ConfigDict(populate_by_name=True)


# ============================================================================
# Local Helpers & Fixtures (no global shared test utility module)
# ============================================================================


class FakeStateStore:
    """Fake state store for testing workflow state management."""

    def __init__(self):
        self.workflows: dict[str, dict[str, Any]] = {}
        self.clock = 0  # Deterministic clock

    def tick(self, seconds: int = 1):
        self.clock += seconds

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        return self.workflows.get(workflow_id)

    def set_workflow(self, workflow_id: str, data: dict[str, Any]):
        self.workflows[workflow_id] = data

    def update_workflow(self, workflow_id: str, updates: dict[str, Any]):
        if workflow_id in self.workflows:
            self.workflows[workflow_id].update(updates)


class DeterministicClock:
    """Deterministic clock for predictable timestamps in tests."""

    def __init__(self, start: int = 1000000000):
        self.timestamp = start

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=UTC)

    def isoformat(self) -> str:
        return self.now().isoformat()

    def advance(self, seconds: int = 1):
        self.timestamp += seconds


class MockOrchestrationController:
    """Mock executor that simulates workflow orchestration for tests."""

    def __init__(self, state_store: FakeStateStore):
        self.state = state_store
        self.checkpoint_saver = None

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            return None
        return MockOrchestrationController_get_workflow_statusResult.model_validate(
            {
                "workflow_id": workflow_id,
                "status": workflow.get("status", "unknown"),
                "current_node": workflow.get("current_node"),
                "progress_percentage": workflow.get("progress", 0),
                "started_at": workflow.get("started_at"),
                "tenant_id": workflow.get("tenant_id"),
                "user_id": workflow.get("user_id"),
            }
        )

    async def pause_workflow(
        self, workflow_id: str, user_id: str, reason: str | None = None
    ) -> bool:
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.get("status") in ["completed", "failed", "cancelled"]:
            raise ValueError(f"Cannot pause workflow in state: {workflow['status']}")

        if workflow.get("status") == "paused":
            raise ValueError("Workflow already paused")

        self.state.update_workflow(
            workflow_id,
            {
                "status": "paused",
                "paused_at": datetime.now(UTC).isoformat(),
                "paused_by": user_id,
                "pause_reason": reason,
            },
        )
        return True

    async def resume_workflow(
        self, workflow_id: str, user_id: str, resume_data: dict | None = None
    ):
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.get("status") in ["completed", "failed", "cancelled"]:
            raise ValueError(f"Cannot resume workflow in state: {workflow['status']}")

        result = MagicMock()
        result.status = MagicMock()
        result.status.value = "running"
        result.workflow_id = workflow_id
        return result

    async def cancel_workflow(self, workflow_id: str) -> bool:
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            return False
        self.state.update_workflow(workflow_id, {"status": "cancelled"})
        return True

    async def list_active_workflows(self, tenant_id: str | None = None) -> list:
        active = []
        for wf_id, wf in self.state.workflows.items():
            if wf.get("status") in ["running", "paused"]:
                if tenant_id is None or wf.get("tenant_id") == tenant_id:
                    active.append(
                        {
                            "workflow_id": wf_id,
                            "status": wf["status"],
                            "workflow_type": wf.get("workflow_type", "unknown"),
                        }
                    )
        return active


@pytest.fixture
def fake_store():
    """Provide a fresh fake state store."""
    return FakeStateStore()


@pytest.fixture
def deterministic_clock():
    """Provide a deterministic clock."""
    return DeterministicClock()


@pytest.fixture
def mock_executor(fake_store):
    """Provide a mock orchestration controller."""
    return MockOrchestrationController(fake_store)


@pytest.fixture
def app(mock_executor):
    """Create FastAPI app with mocked executor for testing."""
    from datetime import datetime

    app = FastAPI()

    def get_executor():
        return mock_executor

    @app.post("/v1/workflows/{workflow_id}/pause", response_model=WorkflowPauseResponse)
    async def pause_workflow(
        workflow_id: str,
        pause_request: Annotated[WorkflowPauseRequest, Body()],
        executor=Depends(get_executor),
    ):
        """Pause a running workflow."""
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        current_status = status.get("status")
        if current_status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Workflow {workflow_id} is {current_status} and cannot be paused",
            )

        if current_status == "paused":
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is already paused")

        paused = await executor.pause_workflow(
            workflow_id=workflow_id,
            user_id=pause_request.user_id,
            reason=pause_request.reason,
        )

        if not paused:
            raise HTTPException(status_code=500, detail="Failed to pause workflow")

        return WorkflowPauseResponse(
            workflow_instance_id=workflow_id,
            status="paused",
            paused_at=datetime.now(UTC).isoformat(),
            current_node=status.get("current_node"),
            message=f"Workflow paused at node: {status.get('current_node', 'unknown')}",
        )

    @app.post("/v1/workflows/{workflow_id}/resume", response_model=WorkflowResumeResponse)
    async def resume_workflow(
        workflow_id: str,
        resume_request: Annotated[WorkflowResumeRequest, Body()],
        executor=Depends(get_executor),
    ):
        """Resume a paused workflow."""
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        current_status = status.get("status")
        if current_status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Workflow {workflow_id} is {current_status} and cannot be resumed",
            )

        await executor.resume_workflow(
            workflow_id=workflow_id,
            user_id=resume_request.user_id,
            resume_data=resume_request.resume_data,
        )

        return WorkflowResumeResponse(
            workflow_instance_id=workflow_id,
            status="resumed",
            resumed_from_node=status.get("current_node"),
            message=f"Workflow resumed from node: {status.get('current_node', 'unknown')}",
            estimated_completion_seconds=60,
        )

    @app.get("/v1/workflows/active")
    async def list_active_workflows(executor=Depends(get_executor)):
        """List active workflows."""
        return await executor.list_active_workflows()

    @app.get("/v1/workflows/{workflow_id}/events")
    async def get_workflow_events(workflow_id: str, executor=Depends(get_executor)):
        """Stream workflow events (simplified for testing)."""
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return get_workflow_eventsResult.model_validate({"workflow_id": workflow_id, "events": []})

    return app


@pytest.fixture
def client(app):
    """Provide a test client."""
    return TestClient(app)


# ============================================================================
# Tests
# ============================================================================


class TestWorkflowPause:
    """Test suite for workflow pause functionality."""

    def test_pause_running_workflow_returns_200(self, client, fake_store):
        """Pausing a running workflow returns 200 with paused status."""
        # Arrange: Create a running workflow
        fake_store.set_workflow(
            "wf-running",
            {
                "status": "running",
                "current_node": "extract_entities",
                "started_at": datetime.now(UTC).isoformat(),
            },
        )

        # Act: Pause the workflow
        response = client.post(
            "/v1/workflows/wf-running/pause",
            json={"user_id": "user-001", "reason": "Human review required"},
        )

        # Assert: Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_instance_id"] == "wf-running"
        assert data["status"] == "paused"
        assert data["current_node"] == "extract_entities"
        assert "paused_at" in data
        assert "message" in data

    def test_pause_completed_workflow_returns_400(self, client, fake_store):
        """Pausing a completed workflow returns 400 error."""
        # Arrange: Create a completed workflow
        fake_store.set_workflow(
            "wf-completed",
            {
                "status": "completed",
                "current_node": "final_output",
            },
        )

        # Act: Attempt to pause
        response = client.post("/v1/workflows/wf-completed/pause", json={"user_id": "user-001"})

        # Assert: Verify error
        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()

    def test_pause_failed_workflow_returns_400(self, client, fake_store):
        """Pausing a failed workflow returns 400 error."""
        fake_store.set_workflow(
            "wf-failed",
            {
                "status": "failed",
                "current_node": "error_handler",
            },
        )

        response = client.post("/v1/workflows/wf-failed/pause", json={"user_id": "user-001"})

        assert response.status_code == 400
        assert "failed" in response.json()["detail"].lower()

    def test_pause_already_paused_workflow_returns_400(self, client, fake_store):
        """Pausing an already paused workflow returns 400 error."""
        fake_store.set_workflow(
            "wf-paused",
            {
                "status": "paused",
                "current_node": "validate_entities",
            },
        )

        response = client.post("/v1/workflows/wf-paused/pause", json={"user_id": "user-001"})

        assert response.status_code == 400
        assert "already paused" in response.json()["detail"].lower()

    def test_pause_nonexistent_workflow_returns_404(self, client):
        """Pausing a non-existent workflow returns 404."""
        response = client.post("/v1/workflows/wf-nonexistent/pause", json={"user_id": "user-001"})

        assert response.status_code == 404


class TestWorkflowResume:
    """Test suite for workflow resume functionality."""

    def test_resume_paused_workflow_returns_200(self, client, fake_store):
        """Resuming a paused workflow returns 200 with resumed status."""
        fake_store.set_workflow(
            "wf-paused",
            {
                "status": "paused",
                "current_node": "validate_entities",
            },
        )

        response = client.post(
            "/v1/workflows/wf-paused/resume",
            json={"user_id": "user-001", "resume_data": {"approved": True}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_instance_id"] == "wf-paused"
        assert data["status"] == "resumed"
        assert data["resumed_from_node"] == "validate_entities"

    def test_resume_completed_workflow_returns_400(self, client, fake_store):
        """Resuming a completed workflow returns 400 error."""
        fake_store.set_workflow(
            "wf-completed",
            {
                "status": "completed",
                "current_node": "final_output",
            },
        )

        response = client.post("/v1/workflows/wf-completed/resume", json={"user_id": "user-001"})

        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()

    def test_resume_failed_workflow_returns_400(self, client, fake_store):
        """Resuming a failed workflow returns 400 error."""
        fake_store.set_workflow(
            "wf-failed",
            {
                "status": "failed",
                "current_node": "error_handler",
            },
        )

        response = client.post("/v1/workflows/wf-failed/resume", json={"user_id": "user-001"})

        assert response.status_code == 400
        assert "failed" in response.json()["detail"].lower()


class TestWorkflowActive:
    """Test suite for active workflows listing."""

    def test_list_active_workflows_returns_only_active(self, client, fake_store):
        """Active workflows endpoint returns only running/paused workflows."""
        # Arrange: Create workflows in various states
        fake_store.set_workflow("wf-running", {"status": "running", "workflow_type": "extraction"})
        fake_store.set_workflow("wf-paused", {"status": "paused", "workflow_type": "analysis"})
        fake_store.set_workflow(
            "wf-completed", {"status": "completed", "workflow_type": "extraction"}
        )
        fake_store.set_workflow("wf-failed", {"status": "failed", "workflow_type": "analysis"})

        # Act: List active workflows
        response = client.get("/v1/workflows/active")

        # Assert: Only running and paused returned
        assert response.status_code == 200
        workflows = response.json()
        assert len(workflows) == 2
        statuses = {w["status"] for w in workflows}
        assert statuses == {"running", "paused"}


class TestWorkflowEvents:
    """Test suite for workflow events endpoint."""

    def test_events_for_existing_workflow_returns_200(self, client, fake_store):
        """Events endpoint returns 200 for existing workflow."""
        fake_store.set_workflow("wf-test", {"status": "running"})

        response = client.get("/v1/workflows/wf-test/events")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "wf-test"

    def test_events_for_nonexistent_workflow_returns_404(self, client):
        """Events endpoint returns 404 for non-existent workflow."""
        response = client.get("/v1/workflows/wf-nonexistent/events")

        assert response.status_code == 404
