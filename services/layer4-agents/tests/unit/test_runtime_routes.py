"""HTTP contract and tenant-isolation tests for the Agent Runtime routes."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    get_request_context,
    set_request_context,
)
from value_fabric.shared.identity.dependencies import require_authenticated

from layer4_agents.api.routes.runtime import (
    _require_runtime_metrics_privileged,
    router,
)
from layer4_agents.runtime import (
    AgentRuntimeImpl,
    RunEnvelope,
    RunRequest,
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


async def test_runtime_routes_deny_unauthenticated_requests() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/runtime/health")
    assert response.status_code == 401


def _runtime() -> AgentRuntimeImpl:
    runtime = AgentRuntimeImpl()

    async def factory(
        workflow_type: str, input_data: dict[str, object], ctx: RuntimeContext
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


async def test_runtime_health_and_metrics_have_stable_shapes() -> None:
    app = _app(RequestContext(tenant_id="tenant-a", roles=["super_admin"]))
    app.dependency_overrides[_require_runtime_metrics_privileged] = lambda: RequestContext(tenant_id="tenant-a", roles=["super_admin"])
    app.state.agent_runtime = _runtime()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/runtime/health")
        metrics = await client.get("/v1/runtime/metrics")
    assert set(health.json()) == {"status", "service", "runtime_ready", "timestamp"}
    assert set(metrics.json()) == {
        "runs_started_total", "runs_terminal_total", "runs_paused_total",
        "runs_resumed_total", "tool_calls_total", "tool_calls_allowed_total",
        "tool_calls_denied_total", "checkpoints_saved_total",
    }


async def test_regular_tenant_cannot_read_global_metrics_via_health() -> None:
    app = _app(RequestContext(tenant_id="tenant-a"))
    app.state.agent_runtime = _runtime()
    app.state.runtime_metrics = object()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/runtime/health")
    assert response.status_code == 200
    assert "metrics" not in response.json()


async def test_regular_tenant_cannot_read_global_metrics() -> None:
    app = _app(RequestContext(tenant_id="tenant-a"))
    app.state.agent_runtime = _runtime()
    transport = httpx.ASGITransport(app=app)
    # The privileged gate resolves the ambient request context, not the
    # overridden require_authenticated dependency: set a valid regular-tenant
    # context so the denial is the deterministic 403 (not an auth-less 401).
    set_request_context(RequestContext(tenant_id="tenant-a"))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/runtime/metrics")
    finally:
        clear_current_context()
    assert response.status_code == 403


async def test_run_metadata_cannot_self_grant_authorization() -> None:
    app = _app(RequestContext(tenant_id="tenant-a"))
    class CapturingRuntime(AgentRuntimeImpl):
        captured: list[RuntimeContext]

        def __init__(self) -> None:
            super().__init__()
            self.captured = []
            async def echo(
                workflow_type: str, input_data: dict[str, object], ctx: RuntimeContext
            ) -> WorkflowResult:
                return WorkflowResult(
                    status=RunStatus.COMPLETED,
                    output={"input": input_data, "tenant_id": ctx.tenant_id},
                )
            self.register_workflow_type("echo", echo)

        async def submit_run(self, body: RunRequest, ctx: RuntimeContext) -> RunEnvelope:
            self.captured.append(ctx)
            return await super().submit_run(body, ctx)

    runtime = CapturingRuntime()
    app.state.agent_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/runtime/runs",
            json={"workflow_type": "echo", "metadata": {"permissions": ["admin"], "service_account_scopes": ["*"]}},
        )
    assert response.status_code == 202
    assert runtime.captured
    assert "permissions" not in runtime.captured[0].metadata
    assert "service_account_scopes" not in runtime.captured[0].metadata


def test_background_execution_context_uses_system_role_without_ambient_context() -> None:
    from layer4_agents.runtime.adapters.workflow_langgraph import LangGraphWorkflowEngineAdapter

    ctx = RuntimeContext(
        tenant_id="tenant-a",
        trace_id="trace",
        run_id="run",
        workflow_id="workflow",
        workflow_type="echo",
    )
    assert get_request_context() is None
    token = LangGraphWorkflowEngineAdapter._enter_execution_context(ctx)
    try:
        ambient = get_request_context()
        assert ambient is not None
        assert ambient.roles == ["system"]
        assert "tenant_admin" not in ambient.roles
    finally:
        if token is not None:
            clear_current_context()
