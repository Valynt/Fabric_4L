from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import checkpoints


class _FakeConn:
    async def fetch(self, _query: str, thread_id: str, tenant_id: str, _limit: int):
        if thread_id == "wf-b" and tenant_id == "tenant-b":
            return [{"thread_id": "wf-b", "checkpoint_id": "chk-1", "state_data": {"tenant_id": "tenant-b", "current_node": "node"}, "created_at": None}]
        return []

    async def fetchrow(self, _query: str, thread_id: str, checkpoint_id: str, tenant_id: str):
        if thread_id == "wf-b" and checkpoint_id == "chk-1" and tenant_id == "tenant-b":
            return {"thread_id": "wf-b", "checkpoint_id": "chk-1", "state_data": {"tenant_id": "tenant-b", "current_node": "node"}, "created_at": None}
        return None


class _FakeExecutor:
    checkpoint_saver = type("Saver", (), {"conn": _FakeConn()})()

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        if workflow_id == "wf-b":
            return {"workflow_id": workflow_id, "tenant_id": "tenant-b", "status": "paused"}
        return None

    async def resume_from_checkpoint(self, **_kwargs):
        return {"status": "resumed"}


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[checkpoints.get_executor] = lambda: _FakeExecutor()
    app.dependency_overrides[checkpoints.require_authenticated] = lambda: RequestContext(
        tenant_id="tenant-a", user_id="user-a", roles=[]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_tenant_a_cannot_list_tenant_b_checkpoints(client: AsyncClient):
    response = await client.get("/v1/workflows/wf-b/checkpoints")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_b_checkpoint_state(client: AsyncClient):
    response = await client.get("/v1/workflows/wf-b/checkpoints/chk-1/state")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_a_cannot_diff_tenant_b_checkpoints(client: AsyncClient):
    response = await client.post(
        "/v1/workflows/wf-b/checkpoints/diff",
        json={"checkpoint_a_id": "chk-1", "checkpoint_b_id": "chk-1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_a_cannot_resume_tenant_b_checkpoint(client: AsyncClient):
    response = await client.post(
        "/v1/workflows/wf-b/resume-from-checkpoint",
        json={"checkpoint_id": "chk-1", "resume_data": {}, "skip_nodes": []},
    )
    assert response.status_code == 403
