from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models.agent_state import WorkflowStatus


async def mark_workflow_running(*, state_manager: Any, workflow_id: str, initial_state: Any) -> None:
    initial_state.status = WorkflowStatus.RUNNING
    initial_state.started_at = initial_state.started_at or datetime.now(UTC)
    await state_manager.save_state(workflow_id, initial_state)


async def persist_workflow_failure(*, state_manager: Any, workflow_id: str, initial_state: Any, exc: Exception) -> None:
    failed = await state_manager.load_state(workflow_id) or initial_state
    failed.status = WorkflowStatus.FAILED
    failed.completed_at = datetime.now(UTC)
    failed.errors.append(str(exc))
    await state_manager.save_state(workflow_id, failed)
