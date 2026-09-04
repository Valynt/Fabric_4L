"""HTTP contract and tenant-isolation tests for the Agent Runtime routes."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    get_request_context,
    set_request_context,
)
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.permissions import Permission, Role
from value_fabric.shared.identity.policy_registry import authorize_action

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
from layer4_agents.runtime.adapters.workflow_langgraph import LangGraphWorkflowEngineAdapter

pytestmark = pytest.mark.unit


def _app(ctx: RequestContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[require_authenticated] = lambda: ctx
    # Production wires the canonical exception handlers via configure_middleware;
    # register them here so route tests assert the real error envelope.
    register_exception_handlers(app)
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
    assert response.json()["error"]["code"] == "TENANT_REQUIRED"


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
    assert hidden.json()["error"]["code"] == "RUN_NOT_FOUND"


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


class _CapturingRuntime(AgentRuntimeImpl):
    """Runtime double that records the RuntimeContext of each submission."""

    def __init__(self) -> None:
        super().__init__()
        self.captured: list[RuntimeContext] = []

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


async def test_run_metadata_cannot_self_grant_authorization() -> None:
    # Forged body grants are stripped; the runtime context carries only the
    # authenticated caller's (empty) grants, so a submission cannot widen its
    # own authorization.
    app = _app(RequestContext(tenant_id="tenant-a"))
    runtime = _CapturingRuntime()
    app.state.agent_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/runtime/runs",
            json={
                "workflow_type": "echo",
                "metadata": {"permissions": ["admin"], "service_account_scopes": ["*"]},
            },
        )
    assert response.status_code == 202
    assert runtime.captured
    assert runtime.captured[0].metadata["permissions"] == []
    assert runtime.captured[0].metadata["service_account_scopes"] == []


async def test_submit_propagates_authenticated_grants_into_runtime_metadata() -> None:
    # Real grants from the authenticated request context survive into runtime
    # metadata while forged body values are discarded.
    ctx = RequestContext(
        tenant_id="tenant-a",
        permissions=frozenset({Permission.READ_SEARCH}),
        service_account_scopes=["read:search"],
    )
    app = _app(ctx)
    runtime = _CapturingRuntime()
    app.state.agent_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/runtime/runs",
            json={
                "workflow_type": "echo",
                "metadata": {
                    "permissions": ["admin:system"],
                    "service_account_scopes": ["admin:tenants"],
                    "kept": "value",
                },
            },
        )
    assert response.status_code == 202
    metadata = runtime.captured[0].metadata
    assert metadata["permissions"] == ["read:search"]
    assert metadata["service_account_scopes"] == ["read:search"]
    assert metadata["kept"] == "value"


def test_background_execution_context_uses_non_bypass_service_role() -> None:
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
        assert ambient.roles == ["service"]
        assert not ambient.has_any_role(Role.SYSTEM, Role.SUPER_ADMIN)
    finally:
        if token is not None:
            clear_current_context()


def test_background_execution_context_gated_action_denied_without_grants() -> None:
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
        with pytest.raises(HTTPException) as exc_info:
            authorize_action("layer4.tool.knowledge.read_entity")
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "INSUFFICIENT_SCOPE"
    finally:
        if token is not None:
            clear_current_context()


def test_background_execution_context_gated_action_allowed_with_metadata_grants() -> None:
    ctx = RuntimeContext(
        tenant_id="tenant-a",
        trace_id="trace",
        run_id="run",
        workflow_id="workflow",
        workflow_type="echo",
        metadata={"permissions": ["read:agents"], "service_account_scopes": ["read:search"]},
    )
    assert get_request_context() is None
    token = LangGraphWorkflowEngineAdapter._enter_execution_context(ctx)
    try:
        ambient = get_request_context()
        assert ambient is not None
        assert ambient.has_permission(Permission.READ_AGENTS)
        assert ambient.service_account_scopes == ["read:search"]
        # Must not raise: the ambient service-role context evaluates the
        # propagated scope grant instead of bypassing the policy check.
        authorize_action("layer4.tool.knowledge.read_entity")
    finally:
        if token is not None:
            clear_current_context()
