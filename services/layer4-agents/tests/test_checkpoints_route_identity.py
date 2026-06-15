from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import checkpoints

TENANT_ID = "11111111-1111-4111-8111-111111111111"


class _FakeExecutor:
    def __init__(self) -> None:
        self.checkpoint_saver = object()
        self.resume_calls: list[dict] = []

    async def resume_from_checkpoint(self, **kwargs):
        self.resume_calls.append(kwargs)
        return {"status": "resumed"}

    async def get_workflow_status(self, workflow_id: str):
        return {"workflow_id": workflow_id, "tenant_id": TENANT_ID}


@pytest.mark.asyncio
async def test_resume_from_checkpoint_uses_authenticated_identity(monkeypatch):
    app = FastAPI()
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")

    fake_executor = _FakeExecutor()

    async def _mock_context() -> RequestContext:
        return RequestContext(user_id="auth-user-42", tenant_id=TENANT_ID)

    async def _mock_get_checkpoint_data(
        _saver, _workflow_id: str, _checkpoint_id: str, _tenant_id: str
    ):
        return {"node_name": "validation_node"}

    monkeypatch.setattr(checkpoints, "_get_checkpoint_data", _mock_get_checkpoint_data)
    app.dependency_overrides[checkpoints.get_executor] = lambda: fake_executor
    app.dependency_overrides[checkpoints.require_authenticated] = _mock_context

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/workflows/wf-123/resume-from-checkpoint",
            json={
                "checkpoint_id": "chk-002",
                "resume_data": {"approved": True},
                "skip_nodes": ["validation_node"],
            },
        )

    assert response.status_code == 200
    assert fake_executor.resume_calls[0]["user_id"] == "auth-user-42"


@pytest.mark.asyncio
async def test_resume_from_checkpoint_rejects_body_identity_fields():
    app = FastAPI()
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")

    async def _mock_context() -> RequestContext:
        return RequestContext(user_id="auth-user-42", tenant_id=TENANT_ID)

    app.dependency_overrides[checkpoints.get_executor] = lambda: _FakeExecutor()
    app.dependency_overrides[checkpoints.require_authenticated] = _mock_context

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/workflows/wf-123/resume-from-checkpoint",
            json={"checkpoint_id": "chk-002", "user_id": "spoofed-user"},
        )

    assert response.status_code == 422
