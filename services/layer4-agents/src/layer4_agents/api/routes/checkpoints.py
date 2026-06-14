from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
)

"""Checkpoint timeline API for workflow state history and rewind.

Provides endpoints for:
- Listing checkpoint history for a workflow
- Comparing state between checkpoints
- Resuming from a specific checkpoint
- State diff visualization
"""


import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.audit import AuditAction
from value_fabric.shared.error_handling.middleware import get_request_id
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...engine.executor import OrchestrationController
from ..common.audit import emit_route_audit
from .workflows import get_executor


class _calculate_state_diffResult(TypedDictModel):
    added: Any
    modified: Any
    removed: Any
    summary: Any
    unchanged: Any

class _summarize_stateResult(TypedDictModel):
    pass

class _get_checkpoint_dataResult(TypedDictModel):
    checkpoint_id: Any
    node_name: Any
    state: Any
    thread_id: Any
    timestamp: Any
    workflow_type: Any

logger = logging.getLogger(__name__)
checkpoint_router = APIRouter()

class CheckpointQueryError(RuntimeError):
    """Raised when checkpoint storage cannot be queried safely."""


# ============================================================================
# Request/Response Models
# ============================================================================


class CheckpointInfo(BaseModel):
    """Information about a single checkpoint."""

    checkpoint_id: str = Field(..., alias="checkpoint_id")
    thread_id: str = Field(..., description="Workflow thread ID")
    node_name: str = Field(..., description="Node that completed before this checkpoint")
    timestamp: str = Field(..., description="ISO timestamp of checkpoint")
    step_number: int = Field(..., description="Step number in execution sequence")
    state_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary of state at this checkpoint"
    )

    model_config = ConfigDict(populate_by_name=True)


class CheckpointListResponse(BaseModel):
    """Response containing checkpoint timeline."""

    workflow_id: str = Field(..., alias="workflow_id")
    checkpoints: list[CheckpointInfo]
    total_count: int
    current_checkpoint_id: str | None = Field(None, description="Most recent checkpoint ID")


class StateDiffRequest(BaseModel):
    """Request to compare two checkpoints."""

    checkpoint_a_id: str = Field(..., description="First checkpoint to compare")
    checkpoint_b_id: str = Field(..., description="Second checkpoint to compare")


class StateDiffResponse(BaseModel):
    """Response containing state differences."""

    workflow_id: str = Field(..., alias="workflow_id")
    checkpoint_a_id: str
    checkpoint_b_id: str
    timestamp_a: str
    timestamp_b: str
    added_fields: list[str] = Field(
        default_factory=list, description="Fields present in B but not A"
    )
    removed_fields: list[str] = Field(
        default_factory=list, description="Fields present in A but not B"
    )
    modified_fields: list[dict[str, Any]] = Field(
        default_factory=list, description="Fields with different values"
    )
    unchanged_fields: list[str] = Field(default_factory=list, description="Fields with same values")
    summary: str = Field(..., description="Human-readable summary of changes")


class ResumeFromCheckpointRequest(BaseModel):
    """Request to resume from a specific checkpoint."""

    checkpoint_id: str = Field(..., description="Checkpoint to resume from")
    resume_data: dict[str, Any] | None = Field(
        default_factory=dict, description="Optional modifications to state before resume"
    )
    skip_nodes: list[str] | None = Field(None, description="Node IDs to skip on resume")

    model_config = ConfigDict(extra="forbid")


class ResumeFromCheckpointResponse(BaseModel):
    """Response from checkpoint-based resume."""

    workflow_id: str = Field(..., alias="workflow_instance_id")
    resumed_from_checkpoint: str
    resumed_from_node: str
    status: str = Field(..., description="resumed, completed, or failed")
    message: str

    model_config = ConfigDict(populate_by_name=True)


class StateSnapshotResponse(BaseModel):
    """Full state snapshot at a checkpoint."""

    workflow_id: str = Field(..., alias="workflow_id")
    checkpoint_id: str
    timestamp: str
    node_name: str
    full_state: dict[str, Any] = Field(..., description="Complete state object")
    state_schema: str = Field(..., description="Workflow state type")


# ============================================================================
# API Routes
# ============================================================================


@checkpoint_router.get(
    "/workflows/{workflow_id}/checkpoints",
    response_model=CheckpointListResponse,
    tags=["checkpoints"],
    responses={403: {"description": "Workflow out of tenant scope"}, 404: {"description": "Workflow not found"}},
)
async def list_checkpoints(
    workflow_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Maximum checkpoints to return"),
    include_state: bool = Query(False, description="Include full state in summary"),
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> CheckpointListResponse:
    """Get checkpoint timeline for a workflow.

    Returns chronologically ordered list of checkpoints showing the
    execution history. Use this for:
    - Visual timeline of workflow progress
    - Selecting a point to resume from
    - Debugging by examining intermediate states

    Example:
        GET /v1/workflows/wf-123/checkpoints?limit=20

        Returns:
        {
            "workflow_id": "wf-123",
            "checkpoints": [
                {
                    "checkpoint_id": "chk-001",
                    "thread_id": "wf-123",
                    "node_name": "DOCUMENT_INGESTION",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "step_number": 1,
                    "state_summary": {"status": "running", "current_node": "DOCUMENT_INGESTION"}
                },
                ...
            ],
            "total_count": 5,
            "current_checkpoint_id": "chk-005"
        }
    """
    if executor.checkpoint_saver is None:
        raise ServiceUnavailableError(message = "Checkpointing not configured - cannot retrieve checkpoints")

    request_id = get_request_id(request)
    try:
        # Query LangGraph's Postgres saver for checkpoints
        await _require_workflow_tenant_access(
            executor=executor, workflow_id=workflow_id, tenant_id=_ctx.tenant_id
        )
        checkpoints = await _query_checkpoints(
            executor.checkpoint_saver, workflow_id, limit,
            tenant_id=str(_ctx.tenant_id),
            request_id=request_id,
        )

        return CheckpointListResponse(
            workflow_id=workflow_id,
            checkpoints=checkpoints,
            total_count=len(checkpoints),
            current_checkpoint_id=checkpoints[-1].checkpoint_id if checkpoints else None,
        )
    except CheckpointQueryError:
        logger.exception(
            "Failed to retrieve checkpoints",
            extra={"workflow_id": workflow_id, "thread_id": workflow_id, "request_id": request_id},
        )
        raise ServiceUnavailableError(
            message="Failed to retrieve checkpoints",
            details={
                "code": "CHECKPOINT_QUERY_FAILED",
                "workflow_id": workflow_id,
                "request_id": request_id,
            },
        )


@checkpoint_router.get(
    "/workflows/{workflow_id}/checkpoints/{checkpoint_id}/state",
    response_model=StateSnapshotResponse,
    tags=["checkpoints"],
    responses={403: {"description": "Workflow out of tenant scope"}, 404: {"description": "Workflow/checkpoint not found"}},
)
async def get_checkpoint_state(
    workflow_id: str,
    checkpoint_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StateSnapshotResponse:
    """Get full state snapshot at a specific checkpoint.

    Use this to inspect workflow state at any point in history.
    Useful for debugging and understanding execution flow.

    Example:
        GET /v1/workflows/wf-123/checkpoints/chk-001/state
    """
    if executor.checkpoint_saver is None:
        raise ServiceUnavailableError(message = "Checkpointing not configured")

    try:
        await _require_workflow_tenant_access(
            executor=executor, workflow_id=workflow_id, tenant_id=_ctx.tenant_id
        )
        state_data = await _get_checkpoint_data(
            executor.checkpoint_saver, workflow_id, checkpoint_id, _ctx.tenant_id
        )

        if not state_data:
            raise NotFoundError(message = str(f"Checkpoint {checkpoint_id} not found for workflow {workflow_id}"))

        return StateSnapshotResponse(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint_id,
            timestamp=state_data.get("timestamp", datetime.now(UTC).isoformat()),
            node_name=state_data.get("node_name", "unknown"),
            full_state=state_data.get("state", {}),
            state_schema=state_data.get("workflow_type", "unknown"),
        )

    except (HTTPException, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving checkpoint {checkpoint_id}: {e}")
        raise ServiceUnavailableError(message="Failed to retrieve checkpoint state")


@checkpoint_router.post(
    "/workflows/{workflow_id}/checkpoints/diff",
    response_model=StateDiffResponse,
    tags=["checkpoints"],
    responses={403: {"description": "Workflow out of tenant scope"}, 404: {"description": "Workflow/checkpoint not found"}},
)
async def compare_checkpoints(
    workflow_id: str,
    request: StateDiffRequest,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StateDiffResponse:
    """Compare state between two checkpoints.

    Shows exactly what changed between two points in execution.
    Useful for debugging and understanding node effects.

    Example:
        POST /v1/workflows/wf-123/checkpoints/diff
        {
            "checkpoint_a_id": "chk-001",
            "checkpoint_b_id": "chk-003"
        }

        Returns:
        {
            "workflow_id": "wf-123",
            "checkpoint_a_id": "chk-001",
            "checkpoint_b_id": "chk-003",
            "timestamp_a": "2024-01-15T10:30:00Z",
            "timestamp_b": "2024-01-15T10:32:00Z",
            "added_fields": ["calculation_results"],
            "removed_fields": [],
            "modified_fields": [
                {"field": "status", "old": "running", "new": "paused"}
            ],
            "unchanged_fields": ["workflow_id", "workflow_type"],
            "summary": "Added calculation_results, status changed from running to paused"
        }
    """
    if executor.checkpoint_saver is None:
        raise ServiceUnavailableError(message = "Checkpointing not configured")

    try:
        await _require_workflow_tenant_access(
            executor=executor, workflow_id=workflow_id, tenant_id=_ctx.tenant_id
        )
        # Get both checkpoint states
        state_a = await _get_checkpoint_data(
            executor.checkpoint_saver, workflow_id, request.checkpoint_a_id, _ctx.tenant_id
        )
        state_b = await _get_checkpoint_data(
            executor.checkpoint_saver, workflow_id, request.checkpoint_b_id, _ctx.tenant_id
        )

        if not state_a or not state_b:
            missing = []
            if not state_a:
                missing.append(request.checkpoint_a_id)
            if not state_b:
                missing.append(request.checkpoint_b_id)
            raise NotFoundError(message = str(f"Checkpoint(s) not found: {', '.join(missing)}"))

        # Calculate diff
        diff = _calculate_state_diff(state_a.get("state", {}), state_b.get("state", {}))

        return StateDiffResponse(
            workflow_id=workflow_id,
            checkpoint_a_id=request.checkpoint_a_id,
            checkpoint_b_id=request.checkpoint_b_id,
            timestamp_a=state_a.get("timestamp", ""),
            timestamp_b=state_b.get("timestamp", ""),
            added_fields=diff["added"],
            removed_fields=diff["removed"],
            modified_fields=diff["modified"],
            unchanged_fields=diff["unchanged"],
            summary=diff["summary"],
        )

    except (HTTPException, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error comparing checkpoints: {e}")
        raise ServiceUnavailableError(message="Failed to compare checkpoints")


@checkpoint_router.post(
    "/workflows/{workflow_id}/resume-from-checkpoint",
    response_model=ResumeFromCheckpointResponse,
    tags=["checkpoints"],
    responses={403: {"description": "Workflow out of tenant scope"}, 404: {"description": "Workflow/checkpoint not found"}},
)
async def resume_from_checkpoint(
    workflow_id: str,
    request: ResumeFromCheckpointRequest,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> ResumeFromCheckpointResponse:
    """Resume workflow from a specific checkpoint.

    Rewinds execution to a previous point and continues from there.
    Optionally modify state before resuming or skip specific nodes.

    Example:
        POST /v1/workflows/wf-123/resume-from-checkpoint
        {
            "checkpoint_id": "chk-002",
            "resume_data": {"approved": true},
            "skip_nodes": ["validation_node"]
        }
    """
    if executor.checkpoint_saver is None:
        raise ServiceUnavailableError(message = "Checkpointing not configured - cannot resume from checkpoint")

    try:
        await _require_workflow_tenant_access(
            executor=executor, workflow_id=workflow_id, tenant_id=_ctx.tenant_id
        )
        # Get the checkpoint data
        try:
            checkpoint_data = await _get_checkpoint_data(
                executor.checkpoint_saver, workflow_id, request.checkpoint_id, _ctx.tenant_id
            )
        except TypeError as exc:
            if "positional" not in str(exc):
                raise
            checkpoint_data = await _get_checkpoint_data(
                executor.checkpoint_saver, workflow_id, request.checkpoint_id
            )

        if not checkpoint_data:
            raise NotFoundError(message = str(f"Checkpoint {request.checkpoint_id} not found"))

        actor_user_id = str(_ctx.user_id) if _ctx.user_id is not None else "anonymous"

        # Resume workflow with checkpoint state and server-resolved actor identity
        result = await executor.resume_from_checkpoint(
            workflow_id=workflow_id,
            checkpoint_id=request.checkpoint_id,
            user_id=actor_user_id,
            resume_data=request.resume_data,
            skip_nodes=request.skip_nodes,
        )

        # Audit: checkpoint resumed
        try:
            await emit_route_audit(
                action=AuditAction.CHECKPOINT_RESUMED,
                context=_ctx,
                resource_type="Workflow",
                resource_id=workflow_id,
                details={
                    "outcome": "success",
                    "checkpoint_id": request.checkpoint_id,
                    "resumed_from_node": checkpoint_data.get("node_name", "unknown"),
                    "result_status": result.get("status", "resumed"),
                },
            )
        except Exception:
            logger.exception(f"Audit logging failed for checkpoint resume {workflow_id}")

        return ResumeFromCheckpointResponse(
            workflow_id=workflow_id,
            resumed_from_checkpoint=request.checkpoint_id,
            resumed_from_node=checkpoint_data.get("node_name", "unknown"),
            status=result.get("status", "resumed"),
            message=f"Workflow resumed from checkpoint at node: {checkpoint_data.get('node_name', 'unknown')}",
        )

    except (HTTPException, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error resuming from checkpoint: {e}")
        raise ServiceUnavailableError(message="Failed to resume from checkpoint")


# ============================================================================
# Helper Functions
# ============================================================================


async def _query_checkpoints(
    checkpoint_saver,
    thread_id: str,
    limit: int = 50,
    *,
    tenant_id: str | None = None,
    request_id: str | None = None,
) -> list[CheckpointInfo]:
    """Query checkpoints from LangGraph Postgres saver.

    Note: This uses LangGraph's checkpoint storage. The exact query
    depends on the AsyncPostgresSaver implementation details.
    """
    checkpoints = []

    try:
        # LangGraph's AsyncPostgresSaver stores checkpoints in a table
        # with thread_id as the key. We need to query this.
        conn = checkpoint_saver.conn if hasattr(checkpoint_saver, "conn") else None

        # Validate connection type to prevent SQL injection
        if conn is None:
            raise CheckpointQueryError("Checkpoint saver has no database connection")

        if not hasattr(conn, "fetch"):
            raise CheckpointQueryError(
                "Checkpoint saver connection doesn't support fetch operation"
            )

        if conn:
            # Query the checkpoint table
            rows = await conn.fetch(
                """
                SELECT thread_id, checkpoint_id, parent_checkpoint_id, 
                       checkpoint->'channel_values' as state_data,
                       checkpoint->'channel_versions' as versions,
                       created_at
                FROM checkpoints 
                WHERE thread_id = $1
                  AND checkpoint->'channel_values'->>'tenant_id' = $2
                ORDER BY created_at ASC
                LIMIT $3
                """,
                thread_id,
                tenant_id,
                limit,
            )

            for i, row in enumerate(rows):
                state_data = row["state_data"] or {}

                # Extract node name from state
                node_name = "unknown"
                if isinstance(state_data, dict):
                    node_name = state_data.get("current_node", "unknown")

                checkpoints.append(
                    CheckpointInfo(
                        checkpoint_id=row["checkpoint_id"],
                        thread_id=row["thread_id"],
                        node_name=node_name,
                        timestamp=row["created_at"].isoformat()
                        if row["created_at"]
                        else datetime.now(UTC).isoformat(),
                        step_number=i + 1,
                        state_summary=_summarize_state(state_data),
                    )
                )

    except CheckpointQueryError:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected checkpoint query failure",
            extra={"thread_id": thread_id, "workflow_id": thread_id, "request_id": request_id},
        )
        raise CheckpointQueryError("Unexpected checkpoint query failure") from e

    return checkpoints


async def _get_checkpoint_data(
    checkpoint_saver, thread_id: str, checkpoint_id: str, tenant_id: str
) -> dict[str, Any] | None:
    """Retrieve full checkpoint data."""
    try:
        conn = checkpoint_saver.conn if hasattr(checkpoint_saver, "conn") else None

        # Validate connection type to prevent SQL injection
        if conn is None:
            logger.warning("Checkpoint saver has no database connection")
            return None

        if not hasattr(conn, "fetchrow"):
            logger.error("Checkpoint saver connection doesn't support fetchrow operation")
            return None

        if conn:
            row = await conn.fetchrow(
                """
                SELECT thread_id, checkpoint_id, 
                       checkpoint->'channel_values' as state_data,
                       created_at
                FROM checkpoints 
                WHERE thread_id = $1
                  AND checkpoint_id = $2
                  AND checkpoint->'channel_values'->>'tenant_id' = $3
                """,
                thread_id,
                checkpoint_id,
                tenant_id,
            )

            if row:
                state_data = row["state_data"] or {}
                return _get_checkpoint_dataResult.model_validate({
                    "checkpoint_id": row["checkpoint_id"],
                    "thread_id": row["thread_id"],
                    "state": state_data,
                    "timestamp": row["created_at"].isoformat()
                    if row["created_at"]
                    else datetime.now(UTC).isoformat(),
                    "node_name": state_data.get("current_node", "unknown")
                    if isinstance(state_data, dict)
                    else "unknown",
                    "workflow_type": state_data.get("workflow_type", "unknown")
                    if isinstance(state_data, dict)
                    else "unknown",
                })


    except Exception as e:
        logger.error(f"Error retrieving checkpoint data: {e}")

    return None


def _summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Create a summary of state for checkpoint list."""
    if not isinstance(state, dict):
        return _summarize_stateResult.model_validate({})

    summary = {
        "status": state.get("status", "unknown"),
        "current_node": state.get("current_node", "unknown"),
    }

    # Add key output indicators
    output_data = state.get("output_data", {})
    if output_data:
        summary["output_keys"] = list(output_data.keys())[:5]

    return summary


def _calculate_state_diff(state_a: dict, state_b: dict) -> dict[str, Any]:
    """Calculate differences between two state dictionaries."""
    keys_a = set(state_a.keys())
    keys_b = set(state_b.keys())

    added = list(keys_b - keys_a)
    removed = list(keys_a - keys_b)
    unchanged = []
    modified = []

    for key in keys_a & keys_b:
        if state_a[key] == state_b[key]:
            unchanged.append(key)
        else:
            modified.append(
                {
                    "field": key,
                    "old": _truncate_value(state_a[key]),
                    "new": _truncate_value(state_b[key]),
                }
            )

    # Generate human-readable summary
    summary_parts = []
    if added:
        summary_parts.append(f"Added: {', '.join(added)}")
    if removed:
        summary_parts.append(f"Removed: {', '.join(removed)}")
    if modified:
        field_names = [m["field"] for m in modified]
        summary_parts.append(f"Modified: {', '.join(field_names)}")

    summary = "; ".join(summary_parts) if summary_parts else "No changes detected"

    return _calculate_state_diffResult.model_validate({
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "summary": summary,
    })


def _truncate_value(value: Any, max_length: int = 100) -> Any:
    """Truncate large values for diff display."""
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    if isinstance(value, (list, dict)):
        str_repr = str(value)
        if len(str_repr) > max_length:
            return f"<{type(value).__name__} length={len(value)}>"
    return value
async def _require_workflow_tenant_access(
    *,
    executor: OrchestrationController,
    workflow_id: str,
    tenant_id: str,
) -> None:
    """Fail-closed tenant gate for workflow-scoped checkpoint operations."""
    if not hasattr(executor, "get_workflow_status"):
        return
    status = await executor.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError(message = str(f"Workflow {workflow_id} not found"))
    workflow_tenant = status.get("tenant_id")
    if not workflow_tenant or str(workflow_tenant) != str(tenant_id):
        raise AuthorizationError(message = str(f"Workflow {workflow_id} does not belong to the current tenant"))
