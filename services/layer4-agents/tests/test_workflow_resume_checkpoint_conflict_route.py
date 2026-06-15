from __future__ import annotations

"""Route-level regression for stale checkpoint resume conflicts."""


from types import SimpleNamespace

from fastapi.testclient import TestClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.main import app
from layer4_agents.api.routes.workflows import get_executor
from value_fabric.shared.identity.dependencies import require_authenticated
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

    app.dependency_overrides[get_executor] = lambda: _Executor()
    app.dependency_overrides[require_authenticated] = lambda: SimpleNamespace(
        tenant_id="tenant-a",
        user_id="user-a",
    )
    try:
        client = TestClient(app)
        response = client.post("/v1/workflows/wf-123/resume", json={"user_id": "user-a"})
    finally:
        app.dependency_overrides.pop(get_executor, None)
        app.dependency_overrides.pop(require_authenticated, None)

    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"]["code"] == "CHECKPOINT_CONFLICT"
    assert payload["detail"]["message"] == "Checkpoint conflict"
