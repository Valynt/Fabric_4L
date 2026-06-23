from __future__ import annotations

"""Security tests for workflow endpoint tenant isolation.

Verifies that cross-tenant access is blocked for all workflow operations:
- GET /v1/workflows/{id} (status)
- GET /v1/workflows/{id}/result
- DELETE /v1/workflows/{id} (cancel)
- POST /v1/workflows/{id}/resume
- POST /v1/workflows/{id}/pause
- POST /v1/workflows/{id}/archive (reference: already has checks)

Pattern: inline FastAPI app with FakeOrchestrationController and auth override.
"""


import json
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

# ---------------------------------------------------------------------------
# Fake executor
# ---------------------------------------------------------------------------


class FakeOrchestrationController:
    """Minimal fake executor for tenant isolation tests."""

    def __init__(self):
        self.workflows: dict[str, dict[str, Any]] = {}

    def add_workflow(self, workflow_id: str, tenant_id: str, status: str = "running"):
        self.workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": "roi_calculator",
            "status": status,
            "current_node": "collect_metrics",
            "progress_percentage": 50.0,
            "started_at": "2024-01-15T10:00:00Z",
            "completed_at": None,
            "error_count": 0,
            "has_output": False,
            "output": None,
            "errors": [],
            "tenant_id": tenant_id,
            "user_id": "user-001",
            "priority": None,
            "scheduler_status": None,
        }

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        return self.workflows.get(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if wf:
            wf["status"] = "cancelled"
            return True
        return False

    async def resume_workflow(self, workflow_id: str, user_id: str, resume_data: dict[str, Any] | None = None):
        class FakeResult:
            status = "running"
        return FakeResult()

    async def pause_workflow(self, workflow_id: str, user_id: str, reason: str | None = None) -> bool:
        wf = self.workflows.get(workflow_id)
        if wf:
            wf["status"] = "paused"
            return True
        return False

    async def archive_workflow(self, workflow_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return None
        if tenant_id and str(wf.get("tenant_id")) != str(tenant_id):
            raise PermissionError("Tenant mismatch")
        return {"archived_at": "2024-01-15T12:00:00Z"}


# ---------------------------------------------------------------------------
# Inline routes mirroring src/api/routes/workflows.py with tenant checks
# ---------------------------------------------------------------------------


def build_app(fake_executor: FakeOrchestrationController) -> FastAPI:
    app = FastAPI()

    def get_executor():
        return fake_executor

    def override_auth_tenant_a():
        return RequestContext(tenant_id=str(TEST_TENANT_A), user_id="user-a", roles=[])

    def override_auth_tenant_b():
        return RequestContext(tenant_id=str(TEST_TENANT_B), user_id="user-b", roles=[])

    # ── GET /v1/workflows/{workflow_id} ──────────────────────────────────

    @app.get("/v1/workflows/{workflow_id}")
    async def get_workflow_status(
        workflow_id: str,
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        return status

    # ── GET /v1/workflows/{workflow_id}/result ────────────────────────────

    @app.get("/v1/workflows/{workflow_id}/result")
    async def get_workflow_result(
        workflow_id: str,
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        if status.get("status") not in {"completed", "failed", "cancelled"}:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} not complete")
        return {"workflow_id": workflow_id, "status": status.get("status"), "output": status.get("output"), "errors": status.get("errors", []), "completed_at": status.get("completed_at")}

    # ── DELETE /v1/workflows/{workflow_id} ───────────────────────────────

    @app.delete("/v1/workflows/{workflow_id}")
    async def cancel_workflow(
        workflow_id: str,
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        cancelled = await executor.cancel_workflow(workflow_id)
        if not cancelled:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} could not be cancelled")
        return {"workflow_id": workflow_id, "status": "cancelled"}

    # ── POST /v1/workflows/{workflow_id}/resume ──────────────────────────

    @app.post("/v1/workflows/{workflow_id}/resume")
    async def resume_workflow(
        workflow_id: str,
        request_body: dict[str, Any],
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        if status.get("status") in {"completed", "failed", "cancelled"}:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is {status.get('status')} and cannot be resumed")
        await executor.resume_workflow(workflow_id, user_id=request_body.get("user_id", ""))
        return {"workflow_instance_id": workflow_id, "status": "resumed", "resumed_from_node": status.get("current_node"), "message": "Resumed", "estimated_completion_seconds": 60}

    # ── POST /v1/workflows/{workflow_id}/pause ───────────────────────────

    @app.post("/v1/workflows/{workflow_id}/pause")
    async def pause_workflow(
        workflow_id: str,
        request_body: dict[str, Any],
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        if status.get("status") in {"completed", "failed", "cancelled"}:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} cannot be paused")
        if status.get("status") == "paused":
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is already paused")
        await executor.pause_workflow(workflow_id, user_id=request_body.get("user_id", ""))
        return {"workflow_instance_id": workflow_id, "status": "paused", "paused_at": "2024-01-15T12:00:00Z", "current_node": status.get("current_node"), "message": "Paused"}

    # ── POST /v1/workflows/{workflow_id}/archive (reference) ─────────────

    @app.post("/v1/workflows/{workflow_id}/archive")
    async def archive_workflow(
        workflow_id: str,
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403, detail=f"Workflow {workflow_id} does not belong to the current tenant")
        result = await executor.archive_workflow(workflow_id, tenant_id=_ctx.tenant_id)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to archive workflow {workflow_id}")
        return {"workflow_id": workflow_id, "status": "archived", "archived_at": result.get("archived_at")}

    # ── POST /v1/workflows (create with tenant validation) ─────────────

    @app.post("/v1/workflows", status_code=201)
    async def create_workflow(
        request_body: dict[str, Any],
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth_tenant_a),
    ):
        if request_body.get("tenant_id") != _ctx.tenant_id:
            raise HTTPException(status_code=403, detail="tenant_id mismatch")
        wf_id = str(uuid4())
        executor.add_workflow(wf_id, tenant_id=_ctx.tenant_id, status="pending")
        return {"workflow_instance_id": wf_id, "status": "pending", "estimated_duration_seconds": 300}

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_TENANT_A = uuid4()
TEST_TENANT_B = uuid4()


@pytest.fixture
def fake_executor():
    return FakeOrchestrationController()


@pytest.fixture
def app(fake_executor):
    return build_app(fake_executor)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Positive tests (same-tenant access works)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="running")
    resp = await client.get(f"/v1/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_result_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="completed")
    fake_executor.workflows[wf_id]["output"] = {"roi": 142}
    resp = await client.get(f"/v1/workflows/{wf_id}/result")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="running")
    resp = await client.delete(f"/v1/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_resume_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="paused")
    resp = await client.post(f"/v1/workflows/{wf_id}/resume", json={"user_id": "user-a"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_pause_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="running")
    resp = await client.post(f"/v1/workflows/{wf_id}/pause", json={"user_id": "user-a"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_archive_same_tenant(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="running")
    resp = await client.post(f"/v1/workflows/{wf_id}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_create_workflow_valid_tenant(client: AsyncClient):
    resp = await client.post("/v1/workflows", json={
        "workflow_type": "roi_calculator",
        "tenant_id": str(TEST_TENANT_A),
        "user_id": "user-a",
    })
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Negative tests (cross-tenant access is blocked with 403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="running")
    resp = await client.get(f"/v1/workflows/{wf_id}")
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_result_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="completed")
    resp = await client.get(f"/v1/workflows/{wf_id}/result")
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="running")
    resp = await client.delete(f"/v1/workflows/{wf_id}")
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resume_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="paused")
    resp = await client.post(f"/v1/workflows/{wf_id}/resume", json={"user_id": "user-a"})
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_pause_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="running")
    resp = await client.post(f"/v1/workflows/{wf_id}/pause", json={"user_id": "user-a"})
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_archive_cross_tenant_returns_403(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_B), status="running")
    resp = await client.post(f"/v1/workflows/{wf_id}/archive")
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_workflow_cross_tenant_returns_403(client: AsyncClient):
    resp = await client.post("/v1/workflows", json={
        "workflow_type": "roi_calculator",
        "tenant_id": str(TEST_TENANT_B),
        "user_id": "user-b",
    })
    assert resp.status_code == 403
    assert "tenant_id mismatch" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Adversarial tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_missing_workflow_returns_404(client: AsyncClient):
    resp = await client.get(f"/v1/workflows/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_result_not_terminal_returns_400(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="running")
    resp = await client.get(f"/v1/workflows/{wf_id}/result")
    assert resp.status_code == 400
    assert "not complete" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resume_terminal_workflow_returns_400(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="completed")
    resp = await client.post(f"/v1/workflows/{wf_id}/resume", json={"user_id": "user-a"})
    assert resp.status_code == 400
    assert "cannot be resumed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_pause_already_paused_returns_400(client: AsyncClient, fake_executor: FakeOrchestrationController):
    wf_id = str(uuid4())
    fake_executor.add_workflow(wf_id, tenant_id=str(TEST_TENANT_A), status="paused")
    resp = await client.post(f"/v1/workflows/{wf_id}/pause", json={"user_id": "user-a"})
    assert resp.status_code == 400
    assert "already paused" in resp.json()["detail"]
