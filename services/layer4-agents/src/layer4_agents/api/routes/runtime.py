"""Authenticated HTTP surface for the provider-agnostic Agent Runtime.

The runtime routes deliberately depend on the shared identity middleware rather
than accepting a tenant identifier from request bodies.  Runtime operations use
the tenant from :class:`RequestContext`, so forged body/query tenant values
cannot widen visibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...runtime import (
    AgentRuntimeError,
    CheckpointConflictError,
    ResumeRequest,
    RunEnvelope,
    RunNotFoundError,
    RunRequest,
    RunResult,
    RunSummary,
    RuntimeContext,
    RuntimeMetrics,
    TenantRequiredError,
    ToolForbiddenError,
    ToolSchema,
    WorkflowTypeNotFoundError,
)
from ...runtime.ports import AgentRuntime
from ..runtime_state import runtime_state

router = APIRouter(prefix="/runtime", tags=["runtime"])


class RuntimeMetricsResponse(BaseModel):
    """Vendor-neutral aggregate runtime counters."""

    model_config = ConfigDict(extra="forbid")

    runs_started_total: int = Field(ge=0)
    runs_terminal_total: int = Field(ge=0)
    runs_paused_total: int = Field(ge=0)
    runs_resumed_total: int = Field(ge=0)
    tool_calls_total: int = Field(ge=0)
    tool_calls_allowed_total: int = Field(ge=0)
    tool_calls_denied_total: int = Field(ge=0)
    checkpoints_saved_total: int = Field(ge=0)


class RuntimeHealthResponse(BaseModel):
    """Safe health state for an authenticated runtime consumer."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded", "unavailable"]
    service: str
    runtime_ready: bool
    timestamp: str
    metrics: RuntimeMetricsResponse


class RuntimeTypesResponse(BaseModel):
    """Tenant-safe runtime discovery payload."""

    model_config = ConfigDict(extra="forbid")

    workflow_types: list[str]
    tools: list[ToolSchema]
    providers: list[str]


class RuntimeRunListResponse(BaseModel):
    """Explicit list envelope for stable SDK and OpenAPI generation."""

    model_config = ConfigDict(extra="forbid")

    runs: list[RunSummary]


def _runtime(request: Request) -> AgentRuntime:
    runtime: AgentRuntime | None = (
        getattr(request.app.state, "agent_runtime", None) or runtime_state.agent_runtime
    )
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "RUNTIME_UNAVAILABLE", "message": "Agent Runtime is not initialized"},
        )
    return runtime


def _tenant(ctx: RequestContext, *, operation: str) -> str:
    tenant_id = str(ctx.tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TENANT_REQUIRED",
                "message": "Tenant context is required",
                "details": {"operation": operation},
            },
        )
    return tenant_id


def _metrics_snapshot(metrics: RuntimeMetrics | None) -> RuntimeMetricsResponse:
    snapshot = metrics.snapshot() if metrics is not None else {}
    return RuntimeMetricsResponse(
        runs_started_total=int(snapshot.get("runs_started_total", 0)),
        runs_terminal_total=int(snapshot.get("runs_terminal_total", 0)),
        runs_paused_total=int(snapshot.get("runs_paused_total", 0)),
        runs_resumed_total=int(snapshot.get("runs_resumed_total", 0)),
        tool_calls_total=int(snapshot.get("tool_calls_total", 0)),
        tool_calls_allowed_total=int(snapshot.get("tool_calls_allowed_total", 0)),
        tool_calls_denied_total=int(snapshot.get("tool_calls_denied_total", 0)),
        checkpoints_saved_total=int(snapshot.get("checkpoints_saved_total", 0)),
    )


def _runtime_error(exc: AgentRuntimeError) -> HTTPException:
    if isinstance(exc, TenantRequiredError):
        code, http_status = "TENANT_REQUIRED", status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, RunNotFoundError):
        code, http_status = "RUN_NOT_FOUND", status.HTTP_404_NOT_FOUND
    elif isinstance(exc, WorkflowTypeNotFoundError):
        code, http_status = "WORKFLOW_TYPE_NOT_FOUND", status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ToolForbiddenError):
        code, http_status = "TOOL_FORBIDDEN", status.HTTP_403_FORBIDDEN
    elif isinstance(exc, CheckpointConflictError):
        code, http_status = "CHECKPOINT_CONFLICT", status.HTTP_409_CONFLICT
    else:
        code, http_status = exc.code, status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail={"code": code, "message": str(exc), "details": exc.details},
    )


@router.get("/health", response_model=RuntimeHealthResponse)
async def runtime_health(
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RuntimeHealthResponse:
    """Report runtime readiness without exposing cross-tenant labels."""
    _tenant(ctx, operation="runtime_health")
    runtime = getattr(request.app.state, "agent_runtime", None) or runtime_state.agent_runtime
    metrics = getattr(request.app.state, "runtime_metrics", None) or runtime_state.runtime_metrics
    ready = runtime is not None
    return RuntimeHealthResponse(
        status="healthy" if ready else "unavailable",
        service="layer4-agents",
        runtime_ready=ready,
        timestamp=datetime.now(UTC).isoformat(),
        metrics=_metrics_snapshot(metrics),
    )


@router.get("/metrics", response_model=RuntimeMetricsResponse)
async def runtime_metrics(
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RuntimeMetricsResponse:
    """Return aggregate runtime counters to an authenticated tenant principal."""
    _tenant(ctx, operation="runtime_metrics")
    metrics = getattr(request.app.state, "runtime_metrics", None) or runtime_state.runtime_metrics
    return _metrics_snapshot(metrics)


@router.get("/types", response_model=RuntimeTypesResponse)
async def runtime_types(
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RuntimeTypesResponse:
    """Discover workflows, tenant-visible tools, and registered providers."""
    tenant = _tenant(ctx, operation="runtime_types")
    runtime = _runtime(request)
    try:
        return RuntimeTypesResponse(
            workflow_types=runtime.list_workflow_types(),
            tools=runtime.list_tools(tenant),
            providers=runtime.list_model_providers(),
        )
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc


@router.post("/runs", response_model=RunEnvelope, status_code=status.HTTP_202_ACCEPTED)
async def submit_runtime_run(
    request: Request,
    body: RunRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> RunEnvelope:
    """Submit a tenant-scoped runtime run."""
    tenant = _tenant(ctx, operation="submit_run")
    run_id = str(uuid4())
    runtime_context = RuntimeContext(
        tenant_id=tenant,
        user_id=str(ctx.user_id) if ctx.user_id is not None else None,
        trace_id=ctx.trace_id or ctx.request_id or str(uuid4()),
        run_id=run_id,
        workflow_id=body.workflow_id or run_id,
        workflow_type=body.workflow_type,
        priority=body.priority,
        metadata=dict(body.metadata),
    )
    try:
        return await _runtime(request).submit_run(body, runtime_context)
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc


@router.get("/runs", response_model=RuntimeRunListResponse)
async def list_runtime_runs(
    request: Request,
    workflow_type: str | None = Query(default=None),
    run_status: str | None = Query(default=None, alias="status"),
    ctx: RequestContext = Depends(require_authenticated),
) -> RuntimeRunListResponse:
    """List only runs owned by the authenticated tenant."""
    tenant = _tenant(ctx, operation="list_runs")
    try:
        runs = await _runtime(request).list_runs(
            tenant, workflow_type=workflow_type, status=run_status
        )
        return RuntimeRunListResponse(runs=runs)
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc


@router.get("/runs/{run_id}", response_model=RunResult)
async def get_runtime_run(
    run_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RunResult:
    """Get a run or return a tenant-safe not-found response."""
    tenant = _tenant(ctx, operation="get_run")
    try:
        result = await _runtime(request).get_run(run_id, tenant)
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc
    if result is None:
        raise _runtime_error(RunNotFoundError(run_id))
    return result


@router.post("/runs/{run_id}/cancel", response_model=RunResult)
async def cancel_runtime_run(
    run_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RunResult:
    """Cancel a run only when it belongs to the authenticated tenant."""
    tenant = _tenant(ctx, operation="cancel_run")
    try:
        return await _runtime(request).cancel_run(run_id, tenant)
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc


@router.post("/runs/{run_id}/resume", response_model=RunResult)
async def resume_runtime_run(
    run_id: str,
    body: ResumeRequest,
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
) -> RunResult:
    """Resume a tenant-owned run with an explicit checkpoint contract."""
    tenant = _tenant(ctx, operation="resume_run")
    try:
        return await _runtime(request).resume_run(
            run_id,
            tenant,
            body,
        )
    except AgentRuntimeError as exc:
        raise _runtime_error(exc) from exc
