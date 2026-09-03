"""HTTP contract and tenant-isolation tests for the Agent Runtime routes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from layer4_agents.api.routes.runtime import router
from layer4_agents.runtime import (
    AgentRuntimeImpl,
    RunStatus,
    RuntimeContext,
    WorkflowResult,
)

pytestmark = pytest.mark.unit


def _app(ctx: RequestContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[require_authenticated] = lambda: ctx
    return app


def _runtime() -> AgentRuntimeImpl:
    runtime = AgentRuntimeImpl()

    async def factory(
        workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext
    ) -> WorkflowResult:
        return WorkflowResult(
            status=RunStatus.COMPLETED,
            output={"input": input_data, "tenant_id": ctx.tenant_id},
        )

    runtime.register_workflow_type("echo", factory)
    return runtime


async def test_runtime_routes_require_tenant_context() -> None:
    app = _app(RequestContext())
    app.state.agent_runtime = _runtime()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/runtime/health")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "TENANT_REQUIRED"


async def test_runtime_routes_return_explicit_shapes_and_scope_runs() -> None:
    app = _app(RequestContext(tenant_id="tenant-a"))
    app.state.agent_runtime = _runtime()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        types_response = await client.get("/v1/runtime/types")
        submit_response = await client.post(
            "/v1/runtime/runs",
            json={"workflow_type": "echo", "input_data": {"value": 7}},
        )
        run_id = submit_response.json()["run_id"]
        list_response = await client.get("/v1/runtime/runs")

    assert types_response.status_code == 200
    assert types_response.json()["workflow_types"] == ["echo"]
    assert {"workflow_types", "tools", "providers"} == set(types_response.json())
    assert submit_response.status_code == 202
    assert submit_response.json()["tenant_id"] == "tenant-a"
    assert list_response.status_code == 200
    assert [run["run_id"] for run in list_response.json()["runs"]] == [run_id]

    # A different tenant cannot observe the run, even when it knows its ID.
    other_app = _app(RequestContext(tenant_id="tenant-b"))
    other_app.state.agent_runtime = app.state.agent_runtime
    other_transport = httpx.ASGITransport(app=other_app)
    async with httpx.AsyncClient(transport=other_transport, base_url="http://test") as client:
        hidden = await client.get(f"/v1/runtime/runs/{run_id}")
    assert hidden.status_code == 404
    assert hidden.json()["detail"]["code"] == "RUN_NOT_FOUND"
