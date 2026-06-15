from __future__ import annotations

"""Route-level regression for stale checkpoint resume conflicts."""


from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import workflows
from layer4_agents.engine.executor import CheckpointConflictError


def test_resume_route_maps_checkpoint_conflict_to_stable_409_payload() -> None:
    class _Executor:
        checkpoint_saver = object()

        async def get_workflow_status(self, _workflow_id: str):
            return {"status": "paused", "tenant_id": "tenant-a", "current_node": "n1"}

        async def resume_workflow(self, *_args, **_kwargs):
            raise CheckpointConflictError(
                "Checkpoint hash mismatch",
                {
                    "workflow_id": "wf-123",
                    "run_id": "run-123",
                    "checkpoint_id": "chk-123",
                    "expected_hash": "expected",
                    "actual_hash": "actual",
                },
            )

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(workflows.router, prefix="/v1")
    app.dependency_overrides[workflows.get_executor] = lambda: _Executor()
    app.dependency_overrides[workflows.require_authenticated] = lambda: RequestContext(
        tenant_id="tenant-a",
        user_id="user-a",
    )
    client = TestClient(app)
    response = client.post("/v1/workflows/wf-123/resume", json={"user_id": "user-a"})

    assert response.status_code == 409
    payload = response.json()
    error = payload.get("detail") or payload.get("error")
    assert error["code"] in {"CHECKPOINT_CONFLICT", "CONFLICT"}
    assert error["message"] == "Checkpoint conflict"
