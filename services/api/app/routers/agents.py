from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from value_fabric.shared.error_handling.exceptions import ConflictError, NotFoundError
from value_fabric.shared.identity.context import get_request_context

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import AgentRun, WorkflowResponse
from app.services.agent_orchestrator import ERR_RUN_NOT_FOUND, orchestrator

router = APIRouter(prefix="/agents", tags=["Agents"])


def _current_user_id() -> str | None:
    ctx = get_request_context()
    return str(ctx.user_id) if ctx is not None and ctx.user_id else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        try:
            return [_json_safe(item) for item in sorted(value, key=str)]
        except Exception:
            return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()
    return str(value)


def _sse_frame(payload: dict[str, Any]) -> str:
    serialized_payload = json.dumps(_json_safe(payload), ensure_ascii=False, separators=(",", ":"))
    return f"data: {serialized_payload}\n\n"


# Canonical naming: backend domain model is "run" (AgentRun).
# Compatibility naming: frontend workflow hooks still call "workflow" routes.
# The compatibility routes below adapt /agents/workflows* <-> /agents/runs*.
def _run_to_workflow_payload(run: AgentRun) -> dict[str, Any]:
    updated_at = run.updated_at or run.created_at
    return {
        "workflow_id": run.id,
        "workflow_instance_id": run.id,
        "id": run.id,
        "name": run.workflow_type,
        "workflow_type": run.workflow_type,
        "status": run.status,
        "progress": 100 if run.status == "completed" else 0,
        "progress_percentage": 100 if run.status == "completed" else 0,
        "created_at": run.created_at,
        "updated_at": updated_at,
        "started_at": run.created_at,
        "completed_at": updated_at if run.status in {"completed", "cancelled", "failed"} else None,
        "result": run.output,
        "input": run.input,
        "tenant_id": run.tenant_id,
    }


@router.post("/runs", response_model=AgentRun, status_code=201)
async def create_agent_run(payload: dict[str, Any], tenant_id: str = Depends(tenant_required)):
    run = orchestrator.create_run(
        tenant_id=tenant_id,
        workflow_type=payload.get("workflow_type", "unknown"),
        account_id=payload.get("account_id"),
        input_data=payload.get("input"),
        user_id=_current_user_id(),
    )
    return run


@router.get("/runs/{run_id}", response_model=AgentRun)
async def get_agent_run(run_id: str, tenant_id: str = Depends(tenant_required)):
    run = orchestrator.get_run(run_id, tenant_id=tenant_id)
    if not run:
        raise NotFoundError(message="Agent run not found")
    return run


@router.post("/runs/{run_id}/resume", response_model=AgentRun)
async def resume_agent_run(run_id: str, tenant_id: str = Depends(tenant_required)):
    try:
        return orchestrator.resume_run(run_id, tenant_id=tenant_id, user_id=_current_user_id())
    except ValueError as exc:
        if str(exc) == ERR_RUN_NOT_FOUND:  # ban-str-e-allow
            raise NotFoundError(message="Agent run not found")
        raise


@router.post("/runs/{run_id}/cancel", response_model=AgentRun)
async def cancel_agent_run(run_id: str, tenant_id: str = Depends(tenant_required)):
    try:
        return orchestrator.cancel_run(run_id, tenant_id=tenant_id)
    except ValueError as exc:
        if str(exc) == ERR_RUN_NOT_FOUND:  # ban-str-e-allow
            raise NotFoundError(message="Agent run not found")
        raise


@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: dict[str, Any], tenant_id: str = Depends(tenant_required)):
    run = orchestrator.create_run(
        tenant_id=tenant_id,
        workflow_type=payload.get("workflow_type", "unknown"),
        account_id=payload.get("account_id"),
        input_data=payload.get("inputs"),
        user_id=_current_user_id(),
    )
    return _run_to_workflow_payload(run)


@router.get("/workflows/active", response_model=list[WorkflowResponse])
async def list_active_workflows(tenant_id: str = Depends(tenant_required)):
    active_like_statuses = {"pending", "running", "paused", "interrupted"}
    runs = db.agent_runs.list(tenant_id=tenant_id)
    active_runs = [run for run in runs if run.status in active_like_statuses]
    refreshed: list[AgentRun] = []
    for run in active_runs:
        refreshed_run = await asyncio.to_thread(
            orchestrator.get_run,
            run.id,
            tenant_id=tenant_id,
        )
        if refreshed_run and refreshed_run.status in active_like_statuses:
            refreshed.append(refreshed_run)
    return [_run_to_workflow_payload(r) for r in refreshed]


@router.get("/workflows/{id}", response_model=WorkflowResponse)
async def get_workflow(id: str, tenant_id: str = Depends(tenant_required)):
    run = orchestrator.get_run(id, tenant_id=tenant_id)
    if not run:
        raise NotFoundError(message="Workflow not found")
    return _run_to_workflow_payload(run)


@router.delete("/workflows/{id}", response_model=WorkflowResponse)
async def cancel_workflow(id: str, tenant_id: str = Depends(tenant_required)):
    try:
        cancelled = orchestrator.cancel_run(id, tenant_id=tenant_id)
    except ValueError as exc:
        if str(exc) == ERR_RUN_NOT_FOUND:  # ban-str-e-allow
            raise NotFoundError(message="Workflow not found")
        raise
    return _run_to_workflow_payload(cancelled)


@router.post("/workflows/{id}/pause", response_model=WorkflowResponse)
async def pause_workflow(id: str, tenant_id: str = Depends(tenant_required)):
    run = orchestrator.get_run(id, tenant_id=tenant_id)
    if not run:
        raise NotFoundError(message="Workflow not found")
    if run.status not in {"pending", "running", "interrupted"}:
        raise ConflictError(
            message=f"Workflow is {run.status} and cannot be paused",
        )
    paused = orchestrator.pause_run(id, tenant_id=tenant_id, user_id=_current_user_id())
    return _run_to_workflow_payload(paused)


@router.post("/workflows/{id}/resume", response_model=WorkflowResponse)
async def resume_workflow(id: str, tenant_id: str = Depends(tenant_required)):
    try:
        resumed = orchestrator.resume_run(id, tenant_id=tenant_id, user_id=_current_user_id())
    except ValueError as exc:
        if str(exc) == ERR_RUN_NOT_FOUND:  # ban-str-e-allow
            raise NotFoundError(message="Workflow not found")
        raise
    return _run_to_workflow_payload(resumed)


@router.get("/workflows/{id}/events")
async def workflow_events(id: str, tenant_id: str = Depends(tenant_required)):
    run = orchestrator.get_run(id, tenant_id=tenant_id)
    if not run:
        raise NotFoundError(message="Workflow not found")

    async def stream() -> Any:
        yield _sse_frame({"payload": _run_to_workflow_payload(run)})
        yield _sse_frame(
            {
                "payload": {
                    "workflow_id": run.id,
                    "status": run.status,
                    "updated_at": datetime.now(UTC),
                }
            }
        )

    return StreamingResponse(stream(), media_type="text/event-stream")
