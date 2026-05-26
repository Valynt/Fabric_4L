from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from value_fabric.layer4.api.routes.workflows import WorkflowCreateRequest, WorkflowInputs, create_workflow
from value_fabric.layer4.engine.executor import WorkflowExecutionError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_workflow_returns_structured_error_when_durable_policy_blocks():
    request = WorkflowCreateRequest(
        workflow_type="roi_calculator",
        inputs=WorkflowInputs(prospect_id="p-1"),
        priority="NORMAL",
    )
    executor = SimpleNamespace(
        execute_workflow=AsyncMock(
            side_effect=WorkflowExecutionError("Durable workflow policy violation: checkpoint saver unavailable")
        )
    )
    ctx = SimpleNamespace(tenant_id="tenant-a", user_id="user-a")

    with pytest.raises(HTTPException) as exc:
        await create_workflow(request=request, executor=executor, _ctx=ctx)

    assert exc.value.status_code == 503
    assert exc.value.detail["error"] == "durable_workflow_required"
    assert "checkpoint saver unavailable" in exc.value.detail["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_workflow_best_effort_mode_returns_created_response():
    request = WorkflowCreateRequest(
        workflow_type="roi_calculator",
        inputs=WorkflowInputs(prospect_id="p-2"),
        priority="NORMAL",
    )
    executor = SimpleNamespace(
        execute_workflow=AsyncMock(
            return_value=SimpleNamespace(workflow_id="wf-1", status="pending")
        )
    )
    ctx = SimpleNamespace(tenant_id="tenant-a", user_id="user-a")

    response = await create_workflow(request=request, executor=executor, _ctx=ctx)

    assert response.workflow_instance_id == "wf-1"
    assert response.status == "pending"
