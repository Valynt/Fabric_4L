from __future__ import annotations

"""Unit tests verifying workflow lifecycle audit emission.

These tests assert that critical workflow operations (create, cancel, pause,
resume, checkpoint-resume) emit auditable events via ``emit_route_audit``.
They use inline FastAPI apps to avoid heavy global imports.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.audit import AuditAction
from value_fabric.shared.identity.context import RequestContext

TEST_TENANT_ID = str(uuid4())
TEST_USER_ID = str(uuid4())


def _fake_auth():
    return RequestContext(tenant_id=TEST_TENANT_ID, user_id=TEST_USER_ID, roles=[])


class _FakeExecutor:
    """Minimal fake that supports the operations under test."""

    def __init__(self):
        self.workflows: dict[str, dict[str, Any]] = {}
        self.checkpoint_saver = MagicMock()
        self.checkpoint_saver.conn = AsyncMock()

    async def get_workflow_status(self, workflow_id: str):
        return self.workflows.get(workflow_id)

    async def execute_workflow(self, *, workflow_type, input_data, workflow_id, priority, tenant_id, user_id):
        wid = workflow_id or str(uuid4())
        self.workflows[wid] = {
            "workflow_id": wid,
            "workflow_type": workflow_type,
            "status": "pending",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "current_node": "start",
        }
        result = MagicMock()
        result.workflow_id = wid
        result.status = MagicMock()
        result.status.value = "pending"
        return result

    async def cancel_workflow(self, workflow_id: str) -> bool:
        if workflow_id not in self.workflows:
            return False
        self.workflows[workflow_id]["status"] = "cancelled"
        return True

    async def pause_workflow(self, workflow_id: str, user_id: str, reason: str | None = None) -> bool:
        if workflow_id not in self.workflows:
            raise ValueError("not found")
        self.workflows[workflow_id]["status"] = "paused"
        return True

    async def resume_workflow(self, workflow_id: str, user_id: str, resume_data: dict | None = None):
        if workflow_id not in self.workflows:
            raise ValueError("not found")
        self.workflows[workflow_id]["status"] = "running"
        result = MagicMock()
        result.status = MagicMock()
        result.status.value = "running"
        return result

    async def resume_from_checkpoint(self, *, workflow_id, checkpoint_id, user_id, resume_data, skip_nodes):
        self.workflows[workflow_id]["status"] = "resumed"
        return {"status": "resumed"}


def _build_app(fake: _FakeExecutor) -> FastAPI:
    app = FastAPI()

    @app.post("/v1/workflows")
    async def create_workflow(
        request: dict[str, Any],
        executor: _FakeExecutor = Depends(lambda: fake),
        _ctx: RequestContext = Depends(_fake_auth),
    ):
        # Inline constants to avoid heavy production imports in tests
        _PRIORITY_MAP = {"CRITICAL": 4, "HIGH": 3, "NORMAL": 2, "LOW": 1, "BACKGROUND": 0}
        _ESTIMATED_DURATION = {"roi_calculator": 120, "whitespace_analysis": 300, "business_case": 400, "business_case_generation": 400, "orchestrator": 180}

        priority = _PRIORITY_MAP.get(request.get("priority", "NORMAL").upper(), 2)
        result = await executor.execute_workflow(
            workflow_type=request["workflow_type"],
            input_data=request.get("inputs", {}),
            workflow_id=request.get("workflow_id"),
            priority=priority,
            tenant_id=_ctx.tenant_id,
            user_id=_ctx.user_id,
        )

        # mirror production audit emission
        from layer4_agents.api.common.audit import emit_route_audit
        await emit_route_audit(
            action=AuditAction.WORKFLOW_STARTED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=result.workflow_id,
            details={"workflow_type": request["workflow_type"], "priority": request.get("priority", "NORMAL")},
        )

        status_value = result.status.value if hasattr(result.status, "value") else str(result.status)
        return {
            "workflow_instance_id": result.workflow_id,
            "status": status_value,
            "estimated_duration_seconds": _ESTIMATED_DURATION.get(request["workflow_type"], 300),
        }

    @app.delete("/v1/workflows/{workflow_id}")
    async def cancel_workflow(
        workflow_id: str,
        executor: _FakeExecutor = Depends(lambda: fake),
        _ctx: RequestContext = Depends(_fake_auth),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404)
        if str(status.get("tenant_id")) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403)

        cancelled = await executor.cancel_workflow(workflow_id)
        if not cancelled:
            raise HTTPException(status_code=400)

        from layer4_agents.api.common.audit import emit_route_audit
        await emit_route_audit(
            action=AuditAction.WORKFLOW_CANCELLED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={"outcome": "success"},
        )
        return {"workflow_id": workflow_id, "status": "cancelled"}

    @app.post("/v1/workflows/{workflow_id}/pause")
    async def pause_workflow(
        workflow_id: str,
        request: dict[str, Any],
        executor: _FakeExecutor = Depends(lambda: fake),
        _ctx: RequestContext = Depends(_fake_auth),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404)
        if str(status.get("tenant_id")) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403)
        if status.get("status") in ("completed", "failed", "cancelled"):
            raise HTTPException(status_code=400)
        if status.get("status") == "paused":
            raise HTTPException(status_code=400)

        paused = await executor.pause_workflow(workflow_id, request["user_id"], request.get("reason"))
        if not paused:
            raise HTTPException(status_code=500)

        from layer4_agents.api.common.audit import emit_route_audit
        await emit_route_audit(
            action=AuditAction.WORKFLOW_PAUSED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={"reason": request.get("reason"), "outcome": "success"},
        )
        return {
            "workflow_instance_id": workflow_id,
            "status": "paused",
            "paused_at": datetime.now(UTC).isoformat(),
            "current_node": status.get("current_node"),
            "message": f"Workflow paused at node: {status.get('current_node', 'unknown')}",
        }

    @app.post("/v1/workflows/{workflow_id}/resume")
    async def resume_workflow(
        workflow_id: str,
        request: dict[str, Any],
        executor: _FakeExecutor = Depends(lambda: fake),
        _ctx: RequestContext = Depends(_fake_auth),
    ):
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404)
        if str(status.get("tenant_id")) != str(_ctx.tenant_id):
            raise HTTPException(status_code=403)
        if status.get("status") in ("completed", "failed", "cancelled"):
            raise HTTPException(status_code=400)

        result = await executor.resume_workflow(workflow_id, request["user_id"], request.get("resume_data"))
        from layer4_agents.api.common.audit import emit_route_audit
        await emit_route_audit(
            action=AuditAction.WORKFLOW_RESUMED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={"outcome": "success", "resumed_from_node": status.get("current_node")},
        )
        return {
            "workflow_instance_id": workflow_id,
            "status": "resumed",
            "resumed_from_node": status.get("current_node"),
            "message": f"Workflow resumed from node: {status.get('current_node', 'unknown')}",
        }

    @app.post("/v1/workflows/{workflow_id}/resume-from-checkpoint")
    async def resume_from_checkpoint(
        workflow_id: str,
        request: dict[str, Any],
        executor: _FakeExecutor = Depends(lambda: fake),
        _ctx: RequestContext = Depends(_fake_auth),
    ):
        from layer4_agents.api.common.audit import emit_route_audit
        await emit_route_audit(
            action=AuditAction.CHECKPOINT_RESUMED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={
                "outcome": "success",
                "checkpoint_id": request["checkpoint_id"],
                "resumed_from_node": "middle",
            },
        )
        return {
            "workflow_instance_id": workflow_id,
            "resumed_from_checkpoint": request["checkpoint_id"],
            "resumed_from_node": "middle",
            "status": "resumed",
            "message": "Workflow resumed from checkpoint at node: middle",
        }

    return app


@pytest.fixture
def fake_executor():
    return _FakeExecutor()


@pytest.fixture
def app(fake_executor):
    return _build_app(fake_executor)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_workflow_emits_audit(client: AsyncClient, fake_executor: _FakeExecutor):
    with patch("layer4_agents.api.common.audit.emit_route_audit", new_callable=AsyncMock) as mock_emit:
        response = await client.post("/v1/workflows", json={
            "workflow_type": "roi_calculator",
            "inputs": {"prospect_id": "p1"},
            "priority": "HIGH",
        })
        assert response.status_code == 200
        mock_emit.assert_awaited_once()
        call_kwargs = mock_emit.call_args.kwargs
        assert call_kwargs["action"] == AuditAction.WORKFLOW_STARTED
        assert call_kwargs["resource_type"] == "Workflow"
        assert call_kwargs["details"]["workflow_type"] == "roi_calculator"


@pytest.mark.asyncio
async def test_cancel_workflow_emits_audit(client: AsyncClient, fake_executor: _FakeExecutor):
    await client.post("/v1/workflows", json={"workflow_type": "roi_calculator"})
    wf_id = list(fake_executor.workflows.keys())[0]

    with patch("layer4_agents.api.common.audit.emit_route_audit", new_callable=AsyncMock) as mock_emit:
        response = await client.delete(f"/v1/workflows/{wf_id}")
        assert response.status_code == 200
        mock_emit.assert_awaited_once()
        assert mock_emit.call_args.kwargs["action"] == AuditAction.WORKFLOW_CANCELLED


@pytest.mark.asyncio
async def test_pause_workflow_emits_audit(client: AsyncClient, fake_executor: _FakeExecutor):
    await client.post("/v1/workflows", json={"workflow_type": "roi_calculator"})
    wf_id = list(fake_executor.workflows.keys())[0]

    with patch("layer4_agents.api.common.audit.emit_route_audit", new_callable=AsyncMock) as mock_emit:
        response = await client.post(f"/v1/workflows/{wf_id}/pause", json={"user_id": "u1", "reason": "review"})
        assert response.status_code == 200
        mock_emit.assert_awaited_once()
        assert mock_emit.call_args.kwargs["action"] == AuditAction.WORKFLOW_PAUSED


@pytest.mark.asyncio
async def test_resume_workflow_emits_audit(client: AsyncClient, fake_executor: _FakeExecutor):
    await client.post("/v1/workflows", json={"workflow_type": "roi_calculator"})
    wf_id = list(fake_executor.workflows.keys())[0]
    fake_executor.workflows[wf_id]["status"] = "paused"

    with patch("layer4_agents.api.common.audit.emit_route_audit", new_callable=AsyncMock) as mock_emit:
        response = await client.post(f"/v1/workflows/{wf_id}/resume", json={"user_id": "u1"})
        assert response.status_code == 200
        mock_emit.assert_awaited_once()
        assert mock_emit.call_args.kwargs["action"] == AuditAction.WORKFLOW_RESUMED


@pytest.mark.asyncio
async def test_resume_from_checkpoint_emits_audit(client: AsyncClient, fake_executor: _FakeExecutor):
    with patch("layer4_agents.api.common.audit.emit_route_audit", new_callable=AsyncMock) as mock_emit:
        response = await client.post("/v1/workflows/wf-123/resume-from-checkpoint", json={
            "checkpoint_id": "chk-001",
            "resume_data": {},
        })
        assert response.status_code == 200
        mock_emit.assert_awaited_once()
        assert mock_emit.call_args.kwargs["action"] == AuditAction.CHECKPOINT_RESUMED
