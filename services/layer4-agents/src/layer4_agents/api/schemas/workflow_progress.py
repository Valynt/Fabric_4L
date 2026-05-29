from __future__ import annotations

"""Normalized workflow progress schemas for polling and streaming clients."""


from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowProgressActionableState(BaseModel):
    """Actionable next state for UI guidance."""

    can_retry: bool = False
    can_resume: bool = False
    can_cancel: bool = False
    requires_user_action: bool = False
    next_action: str | None = None


class WorkflowProgressSchema(BaseModel):
    """Frontend-facing normalized progress model shared by polling/streaming."""

    step_id: str | None = None
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled", "unknown"]
    percent: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str
    started_at: str | None = None
    updated_at: str
    completed_at: str | None = None
    actionable_next_state: WorkflowProgressActionableState


def normalize_workflow_progress(
    *,
    status: dict[str, Any],
    message: str | None = None,
    updated_at: str | None = None,
) -> WorkflowProgressSchema:
    """Map internal workflow status/event payloads to normalized progress schema."""
    state = str(status.get("status", "unknown"))
    current_node = status.get("current_node")
    percent = float(status.get("progress_percentage", status.get("progress", 0.0)) or 0.0)

    return WorkflowProgressSchema(
        step_id=str(current_node) if current_node else None,
        status=state if state in {"pending", "running", "paused", "completed", "failed", "cancelled"} else "unknown",
        percent=percent,
        message=message or f"Workflow status: {state}",
        started_at=status.get("started_at"),
        updated_at=updated_at or datetime.now(UTC).isoformat(),
        completed_at=status.get("completed_at"),
        actionable_next_state=WorkflowProgressActionableState(
            can_retry=state in {"failed", "cancelled"},
            can_resume=state == "paused",
            can_cancel=state in {"pending", "running"},
            requires_user_action=bool(status.get("pause_point")),
            next_action=("resume" if state == "paused" else "view_results" if state == "completed" else "wait"),
        ),
    )

