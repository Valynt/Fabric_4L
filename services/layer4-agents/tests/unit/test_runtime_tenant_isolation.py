"""Phase 6 hostile tenant-isolation tests for ``AgentRuntimeImpl``.

Proves the runtime fails closed on every tenant boundary: cross-tenant reads
and mutations are denied without leaking run identity, and a missing tenant
context raises ``TenantRequiredError`` rather than silently succeeding,
returning an empty list, or executing a tool. These are the "hostile" half of
the behavior-first tenancy contract (see docs/governance/behavior-first-testing.md).

Request-body tenant forging is an HTTP-layer concern (the ``/v1/runtime/*``
routes are deferred); at the runtime core the equivalent guarantee is that a
caller-supplied ``RuntimeContext.tenant_id`` is never trusted over the tenant
recorded at submit time, so a forged context simply cannot see or mutate
another tenant's runs.
"""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    AgentRuntimeImpl,
    AuthzDecision,
    ResumeRequest,
    RunNotFoundError,
    RunRequest,
    RunStatus,
    RuntimeContext,
    TenantRequiredError,
    ToolDef,
    ToolResult,
    ToolSchema,
    WorkflowResult,
)

pytestmark = pytest.mark.unit


def _ctx(tenant_id: str = "tenant-a", **overrides: Any) -> RuntimeContext:
    base = {
        "tenant_id": tenant_id,
        "trace_id": "trace-1",
        "run_id": "run-1",
        "workflow_id": "wf-1",
        "workflow_type": "demo",
    }
    base.update(overrides)
    return RuntimeContext(**base)


async def _completed_factory(
    workflow_type: str, input_data: dict[str, Any], ctx: RuntimeContext
) -> WorkflowResult:
    return WorkflowResult(status=RunStatus.COMPLETED, output={"ok": True})


async def _submit(runtime: AgentRuntimeImpl, tenant_id: str) -> str:
    runtime.register_workflow_type("demo", _completed_factory)
    envelope = await runtime.submit_run(
        RunRequest(workflow_type="demo"), _ctx(tenant_id=tenant_id)
    )
    # Standalone test-file mypy resolves the runtime import as Any (no src on
    # path); the envelope's run_id is str at runtime.
    return envelope.run_id  # type: ignore[no-any-return]


class _NeverReachedEngine:
    """WorkflowEnginePort double that pauses on execute and must never resume."""

    def get_supported_types(self) -> set[str]:
        return {"demo"}

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Any | None = None,
    ) -> WorkflowResult:
        return WorkflowResult(status=RunStatus.PAUSED)

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        raise AssertionError("engine.resume must never see a cross-tenant attempt")


class _EchoToolRegistry:
    """Minimal ToolRegistryPort stub whose execution would succeed if reached."""

    def register(self, tool: ToolDef) -> None:
        pass

    def get_schema(self, name: str, tenant_id: str) -> ToolSchema | None:
        return None

    def list_tools(self, tenant_id: str) -> list[ToolSchema]:
        return []

    async def execute(
        self, name: str, arguments: dict[str, Any], ctx: RuntimeContext
    ) -> ToolResult:
        return ToolResult(status="success", data={"echo": arguments})


class _AllowAuthz:
    def __init__(self) -> None:
        self.seen: list[tuple[str, str]] = []

    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        self.seen.append((tool_name, ctx.tenant_id))
        return AuthzDecision(allowed=True)


# ---------------------------------------------------------------------------
# Cross-tenant reads / mutations fail closed without leaking run identity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_run_denies_cross_tenant_mutation() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    with pytest.raises(RunNotFoundError) as exc_info:
        await runtime.cancel_run(run_id, "tenant-b")

    assert exc_info.value.code == "RUN_NOT_FOUND"
    # The owner still sees the run unchanged — the hostile cancel had no effect.
    owned = await runtime.get_run(run_id, "tenant-a")
    assert owned is not None and owned.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_cancel_run_unknown_run_raises_not_found() -> None:
    runtime = AgentRuntimeImpl()
    await _submit(runtime, "tenant-a")

    with pytest.raises(RunNotFoundError) as exc_info:
        await runtime.cancel_run("no-such-run", "tenant-a")

    assert exc_info.value.code == "RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_cancel_run_cancels_owned_run_only() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    cancelled = await runtime.cancel_run(run_id, "tenant-a")

    assert cancelled.status == RunStatus.CANCELLED
    assert cancelled.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_resume_run_denies_cross_tenant_attempt() -> None:
    engine = _NeverReachedEngine()
    runtime = AgentRuntimeImpl(workflow_engine=engine)
    envelope = await runtime.submit_run(
        RunRequest(workflow_type="demo"), _ctx(tenant_id="tenant-a")
    )

    with pytest.raises(RunNotFoundError) as exc_info:
        await runtime.resume_run(envelope.run_id, "tenant-b", ResumeRequest())

    assert exc_info.value.code == "RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_run_returns_none_for_forged_tenant_context() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    # A caller who forges a different tenant in their context cannot read the run.
    assert await runtime.get_run(run_id, "tenant-b") is None


@pytest.mark.asyncio
async def test_list_runs_is_bidirectionally_tenant_scoped() -> None:
    runtime = AgentRuntimeImpl()
    run_a = await _submit(runtime, "tenant-a")
    run_b = await _submit(runtime, "tenant-b")

    tenant_a_runs = await runtime.list_runs("tenant-a")
    tenant_b_runs = await runtime.list_runs("tenant-b")

    assert [r.run_id for r in tenant_a_runs] == [run_a]
    assert [r.run_id for r in tenant_b_runs] == [run_b]


# ---------------------------------------------------------------------------
# Missing tenant context fails closed (TenantRequiredError), never silent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_run_requires_tenant_and_fails_closed() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    with pytest.raises(TenantRequiredError) as exc_info:
        await runtime.get_run(run_id, "")

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_cancel_run_requires_tenant_and_fails_closed() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    with pytest.raises(TenantRequiredError) as exc_info:
        await runtime.cancel_run(run_id, "")

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_list_runs_requires_tenant_and_fails_closed() -> None:
    runtime = AgentRuntimeImpl()
    await _submit(runtime, "tenant-a")

    with pytest.raises(TenantRequiredError) as exc_info:
        await runtime.list_runs("")

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_call_tool_requires_tenant_and_fails_closed() -> None:
    registry = _EchoToolRegistry()
    runtime = AgentRuntimeImpl(tool_registry=registry, authz=_AllowAuthz())

    # Without the tenant guard this would silently execute the tool; the guard
    # must fire before either the authz gate or the registry execute path.
    with pytest.raises(TenantRequiredError) as exc_info:
        await runtime.call_tool("echo", {"x": 1}, _ctx(tenant_id=""))

    assert exc_info.value.code == "TENANT_REQUIRED"


# ---------------------------------------------------------------------------
# Audit metadata: tenant ownership is preserved across mutations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_preserves_tenant_ownership_metadata() -> None:
    runtime = AgentRuntimeImpl()
    run_id = await _submit(runtime, "tenant-a")

    cancelled = await runtime.cancel_run(run_id, "tenant-a")
    stored = await runtime.get_run(run_id, "tenant-a")

    assert cancelled.tenant_id == "tenant-a"
    assert stored is not None and stored.tenant_id == "tenant-a"
    assert stored.status == RunStatus.CANCELLED
