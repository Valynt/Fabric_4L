from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Workflow API routes - OpenAPI spec compliant.

Implements the workflow API as specified in value_fabric_backend_logic_specifications.md:
- POST /api/v1/workflows - Submit workflow
- GET /api/v1/workflows/{instance_id} - Get status
- GET /api/v1/workflows/{instance_id}/events - Event streaming
- DELETE /api/v1/workflows/{instance_id} - Cancel workflow
"""


import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from value_fabric.shared.audit import AuditAction
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...engine.executor import (
    CheckpointConflictError,
    OrchestrationController,
    WorkflowExecutionError,
)
from ...engine.types import TaskPriority
from ...workflows import list_workflow_types
from ..common.audit import emit_route_audit
from ..common.errors import raise_normalized_with_log
from ..schemas.workflow_progress import WorkflowProgressSchema, normalize_workflow_progress

JsonObject = dict[str, Any]


WorkflowStatusValue = Literal["pending", "running", "paused", "interrupted", "completed", "failed", "cancelled"]

WorkflowErrorValue = str | JsonObject


class WorkflowOutput(BaseModel):
    """Structured workflow output envelope for completed workflow results."""

    data: Any = Field(default_factory=dict)
    summary: str | None = None
    artifacts: list[JsonObject] = Field(default_factory=list)
    metrics: JsonObject = Field(default_factory=dict)
    reasoning_trace: JsonObject | None = Field(
        default=None, description="Structured reasoning trace for agent outputs"
    )
    model_config = ConfigDict(extra="allow")


class WorkflowResultResponse(BaseModel):
    workflow_id: str
    run_id: str | None = Field(default=None, description="Distinct execution identifier")
    trace_id: str | None = Field(default=None, description="Cross-layer audit trace identifier")
    status: WorkflowStatusValue
    output: WorkflowOutput | None = None
    errors: list[WorkflowErrorValue] = Field(default_factory=list)
    completed_at: str | None = None


class WorkflowCancelResponse(BaseModel):
    workflow_id: str
    status: Literal["cancelled"]


class AvailableWorkflow(BaseModel):
    type: str
    name: str
    description: str


class AvailableWorkflowsResponse(BaseModel):
    workflows: list[AvailableWorkflow]


router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

PRIORITY_MAP: dict[str, TaskPriority] = {
    "CRITICAL": TaskPriority.CRITICAL,
    "HIGH": TaskPriority.HIGH,
    "NORMAL": TaskPriority.NORMAL,
    "LOW": TaskPriority.LOW,
    "BACKGROUND": TaskPriority.BACKGROUND,
}

ESTIMATED_DURATION_SECONDS: dict[str, int] = {
    "roi_calculator": 120,
    "whitespace_analysis": 300,
    "business_case": 400,
    "business_case_generation": 400,
    "orchestrator": 180,
}

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
PAUSABLE_STATUSES = {"pending", "running", "scheduled"}


def extract_status_value(status_obj) -> str:
    """Extract string value from WorkflowStatus enum or string."""
    if hasattr(status_obj, 'value'):
        return str(status_obj.value)
    return str(status_obj)


# ============================================================================
# Request/Response Models (OpenAPI Spec Compliant)
# ============================================================================


class WorkflowInputs(BaseModel):
    """Workflow inputs wrapper per spec."""

    prospect_id: str | None = None
    prospect_company: str | None = None
    use_case_ids: list[str] | None = None
    prospect_metrics: JsonObject | None = None
    custom_data: JsonObject | None = Field(default_factory=dict)


VALID_WORKFLOW_TYPES = (
    "business_case_generation",
    "business_case",
    "roi_calculator",
    "whitespace_analysis",
    "orchestrator",
)


class WorkflowCreateRequest(BaseModel):
    """Request to submit a new workflow - OpenAPI spec compliant.

    Spec requires:
    - workflow_type: enum [whitespace_analysis, business_case_generation]
    - inputs: object
    """

    workflow_type: str = Field(
        ...,
        description="Type of workflow to run",
        json_schema_extra={"enum": list(VALID_WORKFLOW_TYPES)},
    )
    inputs: WorkflowInputs = Field(default_factory=WorkflowInputs, description="Workflow inputs")
    priority: str = Field(default="NORMAL", description="Execution priority")
    workflow_id: str | None = Field(None, description="Optional workflow ID")

    @field_validator("workflow_type")
    @classmethod
    def _validate_workflow_type(cls, v: str) -> str:
        if v not in VALID_WORKFLOW_TYPES:
            raise ValueError(f"Invalid workflow_type: {v!r}. Must be one of: {', '.join(VALID_WORKFLOW_TYPES)}")
        return v


class WorkflowCreateResponse(BaseModel):
    """Response from workflow creation - OpenAPI spec compliant.

    Spec requires:
    - workflow_instance_id: string
    - status: string
    - estimated_duration_seconds: integer
    """

    workflow_instance_id: str = Field(..., alias="workflow_instance_id")
    status: str = Field(..., description="Workflow status")
    estimated_duration_seconds: int = Field(default=300, description="Estimated execution time")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowStatusResponse(BaseModel):
    """Workflow status response - OpenAPI spec compliant.

    Spec requires:
    - workflow_instance_id: string
    - workflow_type: string
    - status: string
    - current_state: string
    - progress_percentage: number
    - started_at: datetime
    - completed_at: datetime
    - results: object
    """

    id: str
    workflow_type: str
    status: WorkflowStatusValue
    current_state: str | None = Field(None, alias="current_state")
    current_node: str | None = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    started_at: str | None = None
    completed_at: str | None = None
    error_count: int = 0
    has_output: bool = False
    results: JsonObject | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    priority: int | None = None
    scheduler_status: str | None = None
    progress_meta: WorkflowProgressSchema | None = None
    run_id: str | None = Field(default=None, description="Distinct execution identifier")
    trace_id: str | None = Field(default=None, description="Cross-layer audit trace identifier")

class WorkflowListItem(BaseModel):
    id: str
    name: str
    workflow_type: str
    status: WorkflowStatusValue
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowListItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class WorkflowEvent(BaseModel):
    """Workflow event for streaming.

    Spec requires:
    - event_id: string
    - event_type: string
    - timestamp: datetime
    - message: string
    """

    event_id: str
    event_type: str
    timestamp: str
    message: str
    payload: JsonObject | None = None
    trace_id: str | None = Field(default=None, description="Canonical lineage key for cross-layer audit correlation")
    correlation_id: str | None = Field(default=None, description="Deprecated alias of trace_id; when present must match trace_id")


class WorkflowEventPayload(BaseModel):
    id: str
    status: WorkflowStatusValue
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    current_node: str | None = None
    normalized_progress: JsonObject | None = None
    trace_id: str | None = Field(default=None, description="Canonical lineage key for the workflow lifecycle")
    correlation_id: str | None = Field(default=None, description="Deprecated alias of trace_id")


class WorkflowResumeRequest(BaseModel):
    """Request to resume a paused or interrupted workflow.

    Supports human-in-the-loop workflows where execution pauses
    for user input or approval, then resumes with decision data.
    """

    user_id: str = Field(..., description="User resuming the workflow")
    resume_data: JsonObject | None = Field(
        default_factory=dict, description="Optional user decision/input data"
    )
    tenant_id: str | None = None


class WorkflowResumeResponse(BaseModel):
    """Response from workflow resume."""

    workflow_instance_id: str = Field(..., alias="workflow_instance_id")
    status: str = Field(..., description="resumed, completed, or failed")
    resumed_from_node: str | None = Field(None, description="Node from which execution resumed")
    message: str
    estimated_completion_seconds: int = Field(default=60)

    model_config = ConfigDict(populate_by_name=True)


class WorkflowPauseRequest(BaseModel):
    """Request to pause a running workflow."""

    user_id: str = Field(..., description="User pausing the workflow")
    reason: str | None = Field(None, description="Reason for pausing")
    tenant_id: str | None = None


class WorkflowPauseResponse(BaseModel):
    """Response from workflow pause."""

    workflow_instance_id: str = Field(..., alias="workflow_instance_id")
    status: str = Field(..., description="paused")
    paused_at: str = Field(..., description="ISO timestamp when paused")
    current_node: str | None = Field(None, description="Current node when paused")
    message: str

    model_config = ConfigDict(populate_by_name=True)


def get_executor() -> OrchestrationController:
    """Get workflow executor instance."""
    from ..startup import runtime_state

    if runtime_state.workflow_executor is None:
        raise ServiceUnavailableError(message = "Workflow executor not initialized")
    return runtime_state.workflow_executor


@router.post("/workflows", response_model=WorkflowCreateResponse, status_code=201)
async def create_workflow(
    request: WorkflowCreateRequest,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowCreateResponse:
    """Create and execute a new workflow - OpenAPI spec compliant.

    Example:
        POST /v1/workflows
        {
            "workflow_type": "roi_calculator",
            "inputs": {
                "prospect_id": "prospect-001",
                "use_case_ids": ["uc-001", "uc-002"]
            },
            "priority": "HIGH"
        }

    Returns:
        201 Created with workflow_instance_id and estimated duration
    """
    # Tenant/user identity is sourced from authenticated context only.
    tenant_id = _ctx.tenant_id
    user_id = _ctx.user_id

    # Validate tenant_id is required
    if not tenant_id:
        raise ValidationError(message = "tenant_id is required")

    try:
        # Map priority string to enum
        priority = PRIORITY_MAP.get(request.priority.upper(), TaskPriority.NORMAL)
        # Convert inputs to dict for execution
        input_data = request.inputs.model_dump(exclude_none=True) if request.inputs else {}

        # Execute workflow (async - returns immediately with scheduled task)
        result = await executor.execute_workflow(
            workflow_type=request.workflow_type,
            input_data=input_data,
            workflow_id=request.workflow_id,
            priority=priority,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Estimate duration based on workflow type
        estimated_duration = ESTIMATED_DURATION_SECONDS.get(request.workflow_type, 300)

        # Audit: workflow started
        try:
            await emit_route_audit(
                action=AuditAction.WORKFLOW_STARTED,
                context=_ctx,
                resource_type="Workflow",
                resource_id=result.workflow_id,
                details={"workflow_type": request.workflow_type, "priority": request.priority},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Audit logging failed for workflow start {result.workflow_id}")

        return WorkflowCreateResponse(
            workflow_instance_id=result.workflow_id,
            status=extract_status_value(result.status),
            estimated_duration_seconds=estimated_duration,
        )

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if isinstance(exc, WorkflowExecutionError):
            raise_normalized_with_log(
                exc,
                status_code=403,
                message="Workflow blocked by approval policy",
                error_code="APPROVAL_POLICY_BLOCKED",
                logger=logger,
                log_message="Workflow policy enforcement blocked execution",
            )
        raise_normalized_with_log(
            exc,
            status_code=500,
            message="Workflow execution failed",
            error_code="WORKFLOW_EXECUTION_FAILED",
            logger=logger,
            log_message="Workflow execution failed",
        )



async def _filter_and_paginate_workflows(
    executor: OrchestrationController,
    tenant_id: str,
    limit: int,
    offset: int,
    status: str | None,
    workflow_type: str | None,
    include_completed: bool = False,
) -> WorkflowListResponse:
    """Shared helper: filter and paginate workflows for a tenant."""
    workflows = await executor.list_workflows(tenant_id=tenant_id)

    if not include_completed:
        workflows = [
            w for w in workflows
            if str(w.get("status", "")).lower() not in TERMINAL_STATUSES
        ]

    if status:
        status_lower = status.lower()
        workflows = [w for w in workflows if w.get("status", "").lower() == status_lower]

    if workflow_type:
        type_lower = workflow_type.lower()
        workflows = [w for w in workflows if w.get("workflow_type", "").lower() == type_lower]

    total = len(workflows)
    paginated_raw = workflows[offset:offset + limit]
    paginated = [
        WorkflowListItem(
            id=str(w.get("workflow_id") or w.get("id") or ""),
            name=str(w.get("name") or w.get("workflow_type") or "workflow"),
            workflow_type=str(w.get("workflow_type") or "unknown"),
            status=str(w.get("status") or "pending"),  # type: ignore[arg-type]
            progress=float(w.get("progress") if w.get("progress") is not None else (w.get("progress_percentage") or 0)),  # type: ignore[arg-type]
            created_at=w.get("created_at") or w.get("started_at"),
            updated_at=w.get("updated_at") or w.get("completed_at"),
        )
        for w in paginated_raw
        if str(w.get("workflow_id") or w.get("id") or "").strip()
    ]
    has_more = (offset + limit) < total

    return WorkflowListResponse(
        items=paginated,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of workflows to return"),
    offset: int = Query(default=0, ge=0, description="Number of workflows to skip"),
    status: str | None = Query(default=None, description="Filter by status (pending, running, completed, failed, cancelled)"),
    type: str | None = Query(default=None, description="Filter by workflow type (e.g. business_case)"),
    include_completed: bool = Query(default=False, description="Include terminal workflows in the list response"),
    _ctx: RequestContext = Depends(require_authenticated),
    executor: OrchestrationController = Depends(get_executor),
) -> WorkflowListResponse:
    """List workflows for the authenticated tenant (frontend compatibility alias).

    Supports ?type=business_case filter used by the business-cases hook.
    """
    result = await _filter_and_paginate_workflows(
        executor, _ctx.tenant_id, limit, offset, status, type, include_completed
    )
    return result


@router.get("/workflows/active", response_model=WorkflowListResponse)
async def list_active_workflows(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of workflows to return"),
    offset: int = Query(default=0, ge=0, description="Number of workflows to skip"),
    status: str | None = Query(default=None, description="Filter by status (pending, running, completed, failed, cancelled)"),
    workflow_type: str | None = Query(default=None, description="Filter by workflow type (e.g. business_case)"),
    _ctx: RequestContext = Depends(require_authenticated),
    executor: OrchestrationController = Depends(get_executor),
) -> WorkflowListResponse:
    """List currently active workflows for the authenticated tenant with pagination.

    Returns a paginated list of workflows with metadata for efficient client-side rendering.
    """
    result = await _filter_and_paginate_workflows(
        executor, _ctx.tenant_id, limit, offset, status, workflow_type, include_completed=False
    )
    return result


@router.get("/workflows/types", response_model=AvailableWorkflowsResponse)
async def list_available_workflows() -> AvailableWorkflowsResponse:
    """List available workflow types."""
    types = list_workflow_types()

    return AvailableWorkflowsResponse.model_validate({
        "workflows": [
            {"type": key, "name": info["name"], "description": info["description"]}
            for key, info in types.items()
        ]
    })

@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowStatusResponse:
    """Get status of a workflow - OpenAPI spec compliant.

    Returns detailed status including:
    - progress_percentage (0-100)
    - current_state
    - tenant_id, user_id
    """
    status = await executor.get_workflow_status(workflow_id)

    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    return WorkflowStatusResponse(
        id=status.get("workflow_id", workflow_id),
        workflow_type=status.get("workflow_type", "unknown"),
        status=status.get("status", "pending"),
        current_state=status.get("current_node"),
        current_node=status.get("current_node"),
        progress=status.get("progress_percentage", 0.0),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
        error_count=status.get("error_count", 0),
        has_output=status.get("has_output", False),
        results=status.get("output"),
        tenant_id=status.get("tenant_id"),
        user_id=status.get("user_id"),
        priority=status.get("priority"),
        scheduler_status=status.get("scheduler_status"),
        progress_meta=normalize_workflow_progress(status=status),
        run_id=status.get("run_id"),
        trace_id=status.get("trace_id"),
    )


@router.get("/workflows/{workflow_id}/result", response_model=WorkflowResultResponse)
async def get_workflow_result(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowResultResponse:
    """Get result of a completed workflow."""
    status = await executor.get_workflow_status(workflow_id)

    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    if status.get("status") not in TERMINAL_STATUSES:
        raise ValidationError(message = str(f"Workflow {workflow_id} not complete (status: {status.get('status')})"))

    result = await executor.get_result(workflow_id)
    if not result:
        raise NotFoundError(message = str(f"Workflow {workflow_id} result not found"))

    output_data = result.get("output") or {}
    response = WorkflowResultResponse.model_validate({
        "workflow_id": workflow_id,
        "run_id": result.get("run_id"),
        "trace_id": result.get("trace_id"),
        "status": status.get("status"),
        "output": {
            "data": output_data,
            "reasoning_trace": output_data.get("reasoning_trace"),
        },
        "errors": status.get("errors", []),
        "completed_at": status.get("completed_at"),
    })
    return response


@router.delete("/workflows/{workflow_id}", response_model=WorkflowCancelResponse)
async def cancel_workflow(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowCancelResponse:
    """Cancel a running workflow - OpenAPI spec compliant (DELETE method)."""
    status = await executor.get_workflow_status(workflow_id)

    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    cancelled = await executor.cancel_workflow(workflow_id)

    if not cancelled:
        raise ValidationError(message = str(f"Workflow {workflow_id} could not be cancelled"))

    # Audit: workflow cancelled
    try:
        await emit_route_audit(
            action=AuditAction.WORKFLOW_CANCELLED,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={"outcome": "success"},
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(f"Audit logging failed for workflow cancel {workflow_id}")

    return WorkflowCancelResponse(workflow_id=workflow_id, status="cancelled")


@router.post("/workflows/{workflow_id}/resume", response_model=WorkflowResumeResponse)
async def resume_workflow(
    workflow_id: str,
    request: WorkflowResumeRequest,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowResumeResponse:
    """Resume a paused or interrupted workflow from its last checkpoint.

    This endpoint enables human-in-the-loop workflows by allowing execution
    to pause for user input/decisions, then resume from the exact point
    where it stopped.

    The workflow state is loaded from Postgres checkpoint storage, and
    execution continues from the last completed node.

    Example:
        POST /v1/workflows/wf-123/resume
        {
            "user_id": "user-001",
            "resume_data": {"approved": true, "notes": "Proceed with ROI calc"}
        }

    Returns:
        200 OK - Workflow resumed and running (or completed if fast)
        404 Not Found - Workflow not found or no checkpoint exists
        400 Bad Request - Workflow not in resumable state (completed/failed/cancelled)
        503 Service Unavailable - Checkpointing not configured
    """
    # Verify checkpointing is available
    if executor.checkpoint_saver is None:
        raise ServiceUnavailableError(message = "Checkpointing not configured - cannot resume workflows")

    # Check current status
    status = await executor.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    if status.get("status") in TERMINAL_STATUSES:
        raise ValidationError(message = str(f"Workflow {workflow_id} is {status.get('status')} and cannot be resumed"))

    # Resume execution
    try:
        result = await executor.resume_workflow(
            workflow_id=workflow_id,
            user_id=request.user_id,
            resume_data=request.resume_data,
        )

        # Determine response status based on result
        result_status = extract_status_value(result.status)
        is_complete = result_status in TERMINAL_STATUSES
        # Audit: workflow resumed
        try:
            await emit_route_audit(
                action=AuditAction.WORKFLOW_RESUMED,
                context=_ctx,
                resource_type="Workflow",
                resource_id=workflow_id,
                details={
                    "outcome": "success",
                    "resumed_from_node": status.get("current_node"),
                    "result_status": result_status,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Audit logging failed for workflow resume {workflow_id}")

        return WorkflowResumeResponse(
            workflow_instance_id=workflow_id,
            status=result_status if is_complete else "resumed",
            resumed_from_node=status.get("current_node"),
            message=(
                f"Workflow {'completed' if is_complete else 'resumed'} "
                f"from node: {status.get('current_node', 'unknown')}"
            ),
            estimated_completion_seconds=0 if is_complete else 60,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if isinstance(exc, ValueError):
            logger.warning("workflow_resume_value_error", extra={"error_type": type(exc).__name__})
            raise NotFoundError(message = "Workflow not found")
        if isinstance(exc, CheckpointConflictError):
            raise_normalized_with_log(
                exc,
                status_code=409,
                message="Checkpoint conflict",
                error_code="CHECKPOINT_CONFLICT",
                logger=logger,
                log_message="workflow_resume_checkpoint_conflict",
                **exc.metadata,
            )
        if isinstance(exc, WorkflowExecutionError):
            raise_normalized_with_log(
                exc,
                status_code=403,
                message="Workflow resume blocked by approval policy",
                error_code="APPROVAL_POLICY_BLOCKED",
                logger=logger,
                log_message="workflow_resume_execution_error",
            )
        raise_normalized_with_log(
            exc,
            status_code=500,
            message="Failed to resume workflow",
            error_code="WORKFLOW_RESUME_FAILED",
            logger=logger,
            log_message=f"Unexpected error resuming workflow {workflow_id}",
        )


@router.post("/workflows/{workflow_id}/pause", response_model=WorkflowPauseResponse)
async def pause_workflow(
    workflow_id: str,
    request: WorkflowPauseRequest,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> WorkflowPauseResponse:
    """Pause a running workflow.

    This endpoint pauses workflow execution at the current node.
    The workflow can be resumed later using the resume endpoint.

    Example:
        POST /v1/workflows/wf-123/pause
        {
            "user_id": "user-001",
            "reason": "Human review required"
        }

    Returns:
        200 OK - Workflow paused
        404 Not Found - Workflow not found
        400 Bad Request - Workflow not in pausable state (completed/failed/cancelled)
        503 Service Unavailable - Workflow executor not available
    """
    # Check current status
    status = await executor.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    current_status = status.get("status")
    if current_status in TERMINAL_STATUSES:
        raise ValidationError(message = str(f"Workflow {workflow_id} is {current_status} and cannot be paused"))

    if current_status == "paused":
        raise ValidationError(message = str(f"Workflow {workflow_id} is already paused"))

    # Pause execution
    try:
        paused = await executor.pause_workflow(
            workflow_id=workflow_id,
            user_id=request.user_id,
            reason=request.reason,
        )

        if not paused:
            raise ServiceUnavailableError(message="Failed to pause workflow")

        # Audit: workflow paused
        try:
            await emit_route_audit(
                action=AuditAction.WORKFLOW_PAUSED,
                context=_ctx,
                resource_type="Workflow",
                resource_id=workflow_id,
                details={"reason": request.reason, "outcome": "success"},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Audit logging failed for workflow pause {workflow_id}")

        return WorkflowPauseResponse(
            workflow_instance_id=workflow_id,
            status="paused",
            paused_at=datetime.now(UTC).isoformat(),
            current_node=status.get("current_node"),
            message=f"Workflow paused at node: {status.get('current_node', 'unknown')}",
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if isinstance(exc, ValueError):
            logger.warning("workflow_pause_value_error", extra={"error_type": type(exc).__name__})
            raise NotFoundError(message = "Workflow not found")
        raise_normalized_with_log(
            exc,
            status_code=500,
            message="Failed to pause workflow",
            error_code="WORKFLOW_PAUSE_FAILED",
            logger=logger,
            log_message=f"Unexpected error pausing workflow {workflow_id}",
        )




@router.get("/workflows/{workflow_id}/events")
async def get_workflow_events(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StreamingResponse:
    """Get workflow events via Server-Sent Events (SSE).

    Streams real-time workflow progress events.

    Example:
        GET /v1/workflows/{id}/events

        Event: workflow_event
        data: {"event_id": "...", "event_type": "node_started", ...}
    """
    # Enforce tenant isolation before streaming
    status = await executor.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    async def event_generator():
        """Generate SSE events for workflow."""
        last_status = None

        while True:
            # Get current status
            status = await executor.get_workflow_status(workflow_id)

            if not status:
                yield f"event: error\ndata: {json.dumps({'message': 'Workflow not found'})}\n\n"
                break

            # Send event if status changed
            if status != last_status:
                event = WorkflowEvent(
                    event_id=f"evt-{datetime.now(UTC).timestamp()}",
                    event_type="status_update",
                    timestamp=datetime.now(UTC).isoformat(),
                    message=f"Workflow status: {status.get('status')}",
                    payload=WorkflowEventPayload(
                        id=workflow_id,
                        status=status.get("status"),
                        progress=status.get("progress_percentage"),
                        current_node=status.get("current_node"),
                        normalized_progress=normalize_workflow_progress(
                            status=status,
                            message=f"Workflow status: {status.get('status')}",
                        ).model_dump(),
                    ).model_dump(),
                )

                yield f"event: workflow_event\ndata: {json.dumps(event.model_dump())}\n\n"

                last_status = status

            # Check if workflow is complete
            if status.get("status") in TERMINAL_STATUSES:
                # Send completion event
                event = WorkflowEvent(
                    event_id=f"evt-{datetime.now(UTC).timestamp()}",
                    event_type="workflow_complete",
                    timestamp=datetime.now(UTC).isoformat(),
                    message=f"Workflow {status.get('status')}",
                    payload=WorkflowEventPayload(
                        id=workflow_id,
                        status=status.get("status"),
                        progress=status.get("progress_percentage", 100.0),
                    ).model_dump(),
                )
                yield f"event: workflow_event\ndata: {json.dumps(event.model_dump())}\n\n"
                break

            # Wait before next poll
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


class ArchiveWorkflowResponse(BaseModel):
    """Archive workflow response."""

    workflow_id: str
    status: str
    archived_at: str


@router.post("/workflows/{workflow_id}/archive", response_model=ArchiveWorkflowResponse)
async def archive_workflow(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> ArchiveWorkflowResponse:
    """Archive a workflow.

    Soft-deletes a workflow by setting metadata["archived"] = True.
    Archived workflows are excluded from list endpoints.
    Idempotent: repeated calls return the existing archived_at timestamp.
    """
    status = await executor.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))

    # Enforce tenant isolation
    workflow_tenant = status.get("tenant_id")
    if workflow_tenant and str(workflow_tenant) != str(_ctx.tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))

    try:
        result = await executor.archive_workflow(workflow_id, tenant_id=_ctx.tenant_id)
    except PermissionError as e:
        logger.warning("workflow_archive_permission_denied", extra={"error": repr(e)})
        raise AuthorizationError(message = "Permission denied to archive workflow")

    if result is None:
        raise ServiceUnavailableError(message=f"Failed to archive workflow {workflow_id}")

    archived_at = result.get("archived_at", datetime.now(UTC).isoformat())

    # Emit audit event (best-effort)
    try:
        await emit_route_audit(
            action=AuditAction.UPDATE,
            context=_ctx,
            resource_type="Workflow",
            resource_id=workflow_id,
            details={"archived_at": archived_at, "outcome": "success"},
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(f"Audit logging failed for archive of workflow {workflow_id}")

    return ArchiveWorkflowResponse(
        workflow_id=workflow_id,
        status="archived",
        archived_at=archived_at,
    )
