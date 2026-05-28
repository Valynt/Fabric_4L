from __future__ import annotations

"""Integration tests for workflow archive and list endpoints.

Tests the following routes added for frontend-backend contract alignment:
- GET /v1/workflows (with type filter)
- POST /v1/workflows/{id}/archive (with tenant isolation)

Uses inline FastAPI app (same pattern as test_workflow_controls.py) to avoid
heavy app-level imports.
"""


import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated


# ---------------------------------------------------------------------------
# Fake executor that simulates the real OrchestrationController
# ---------------------------------------------------------------------------

class FakeStateStore:
    def __init__(self):
        self.states: dict[str, dict[str, Any]] = {}

    def load(self, workflow_id: str) -> dict[str, Any] | None:
        return self.states.get(workflow_id)

    def save(self, workflow_id: str, state: dict[str, Any]):
        self.states[workflow_id] = state


class FakeOrchestrationController:
    """Minimal fake executor for archive/list tests."""

    def __init__(self):
        self.workflows: dict[str, dict[str, Any]] = {}
        self.state_store = FakeStateStore()

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return None
        return {
            "workflow_id": workflow_id,
            "workflow_type": wf.get("workflow_type", "unknown"),
            "status": wf.get("status", "unknown"),
            "current_node": wf.get("current_node"),
            "progress_percentage": 0.0,
            "started_at": None,
            "completed_at": None,
            "error_count": 0,
            "has_output": False,
            "tenant_id": wf.get("tenant_id"),
            "user_id": wf.get("user_id"),
            "priority": None,
            "scheduler_status": None,
        }

    async def list_active_workflows(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        result = []
        for wid, wf in self.workflows.items():
            if tenant_id and str(wf.get("tenant_id")) != str(tenant_id):
                continue
            if wf.get("metadata", {}).get("archived"):
                continue
            if wf.get("status") in ("pending", "running", "retrying"):
                result.append(await self.get_workflow_status(wid))
        return result

    async def archive_workflow(self, workflow_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return None
        if tenant_id and str(wf.get("tenant_id")) != str(tenant_id):
            raise PermissionError("Tenant mismatch")
        if wf.get("metadata", {}).get("archived"):
            return {"archived_at": wf["metadata"]["archived_at"]}
        ts = datetime.now(UTC).isoformat()
        wf.setdefault("metadata", {})["archived"] = True
        wf["metadata"]["archived_at"] = ts
        return {"archived_at": ts}


# ---------------------------------------------------------------------------
# Inline route definitions (mirroring src/api/routes/workflows.py)
# ---------------------------------------------------------------------------

def build_app(fake_executor: FakeOrchestrationController) -> FastAPI:
    app = FastAPI()

    def get_executor():
        return fake_executor

    def override_auth():
        return RequestContext(
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            roles=[],
        )

    @app.get("/v1/workflows")
    async def list_workflows(
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        type: str | None = None,
        _ctx: RequestContext = Depends(override_auth),
        executor: FakeOrchestrationController = Depends(get_executor),
    ) -> dict[str, Any]:
        all_active = await executor.list_active_workflows(tenant_id=_ctx.tenant_id)
        if status:
            status_lower = status.lower()
            all_active = [w for w in all_active if w.get("status", "").lower() == status_lower]
        if type:
            type_lower = type.lower()
            all_active = [w for w in all_active if w.get("workflow_type", "").lower() == type_lower]
        total = len(all_active)
        paginated = all_active[offset:offset + limit]
        has_more = (offset + limit) < total
        return {
            "items": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }

    @app.post("/v1/workflows/{workflow_id}/archive")
    async def archive_workflow(
        workflow_id: str,
        executor: FakeOrchestrationController = Depends(get_executor),
        _ctx: RequestContext = Depends(override_auth),
    ) -> dict[str, Any]:
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        workflow_tenant = status.get("tenant_id")
        if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
            raise HTTPException(
                status_code=403,
                detail=f"Workflow {workflow_id} does not belong to the current tenant",
            )
        try:
            result = await executor.archive_workflow(workflow_id, tenant_id=_ctx.tenant_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        if result is None:
            raise HTTPException(status_code=500, detail=f"Failed to archive workflow {workflow_id}")
        archived_at = result.get("archived_at", datetime.now(UTC).isoformat())
        return {
            "workflow_id": workflow_id,
            "status": "archived",
            "archived_at": archived_at,
        }

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_TENANT_ID = uuid4()
TEST_USER_ID = uuid4()
OTHER_TENANT_ID = uuid4()


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
# GET /v1/workflows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_workflows_defaults(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """GET /v1/workflows returns paginated list with defaults."""
    fake_executor.workflows["wf-1"] = {
        "workflow_type": "business_case",
        "status": "running",
        "tenant_id": str(TEST_TENANT_ID),
        "current_node": "node-a",
    }

    response = await client.get("/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert data["has_more"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["workflow_id"] == "wf-1"


@pytest.mark.asyncio
async def test_list_workflows_with_type_filter(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """GET /v1/workflows?type=business_case filters by workflow type."""
    fake_executor.workflows["wf-1"] = {
        "workflow_type": "business_case",
        "status": "running",
        "tenant_id": str(TEST_TENANT_ID),
    }
    fake_executor.workflows["wf-2"] = {
        "workflow_type": "roi_calculator",
        "status": "running",
        "tenant_id": str(TEST_TENANT_ID),
    }

    response = await client.get("/v1/workflows?type=business_case")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["workflow_type"] == "business_case"


@pytest.mark.asyncio
async def test_list_workflows_excludes_archived(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Archived workflows must not appear in GET /v1/workflows."""
    fake_executor.workflows["wf-1"] = {
        "workflow_type": "business_case",
        "status": "running",
        "tenant_id": str(TEST_TENANT_ID),
        "metadata": {"archived": True, "archived_at": "2026-01-01T00:00:00Z"},
    }

    response = await client.get("/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_workflows_pagination(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Pagination limit and offset are respected."""
    for i in range(5):
        fake_executor.workflows[f"wf-{i}"] = {
            "workflow_type": "business_case",
            "status": "running",
            "tenant_id": str(TEST_TENANT_ID),
        }

    response = await client.get("/v1/workflows?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2
    assert data["has_more"] is True


@pytest.mark.asyncio
async def test_list_workflows_tenant_isolation(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Workflows from other tenants are excluded."""
    fake_executor.workflows["wf-other"] = {
        "workflow_type": "business_case",
        "status": "running",
        "tenant_id": str(OTHER_TENANT_ID),
    }

    response = await client.get("/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# POST /v1/workflows/{id}/archive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archive_workflow_success(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Archiving a workflow returns 200 with archived timestamp."""
    fake_executor.workflows["wf-1"] = {
        "workflow_type": "business_case",
        "status": "completed",
        "tenant_id": str(TEST_TENANT_ID),
    }

    response = await client.post("/v1/workflows/wf-1/archive")
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "wf-1"
    assert data["status"] == "archived"
    assert "archived_at" in data


@pytest.mark.asyncio
async def test_archive_workflow_idempotent(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Repeated archive calls succeed and preserve the same archived_at."""
    fake_executor.workflows["wf-1"] = {
        "workflow_type": "business_case",
        "status": "completed",
        "tenant_id": str(TEST_TENANT_ID),
    }

    r1 = await client.post("/v1/workflows/wf-1/archive")
    assert r1.status_code == 200
    archived_at = r1.json()["archived_at"]

    r2 = await client.post("/v1/workflows/wf-1/archive")
    assert r2.status_code == 200
    assert r2.json()["archived_at"] == archived_at


@pytest.mark.asyncio
async def test_archive_workflow_not_found(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Archiving a non-existent workflow returns 404."""
    response = await client.post("/v1/workflows/nonexistent/archive")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_archive_workflow_cross_tenant_forbidden(client: AsyncClient, fake_executor: FakeOrchestrationController):
    """Archiving a workflow belonging to another tenant returns 403."""
    fake_executor.workflows["wf-other"] = {
        "workflow_type": "business_case",
        "status": "completed",
        "tenant_id": str(OTHER_TENANT_ID),
    }

    response = await client.post("/v1/workflows/wf-other/archive")
    assert response.status_code == 403
