from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..models.agent_state import WorkflowStatus

logger = logging.getLogger(__name__)


async def mark_workflow_running(*, state_manager: Any, workflow_id: str, initial_state: Any) -> None:
    initial_state.status = WorkflowStatus.RUNNING
    initial_state.started_at = initial_state.started_at or datetime.now(UTC)
    await state_manager.save_state(workflow_id, initial_state)


async def persist_workflow_failure(*, state_manager: Any, workflow_id: str, initial_state: Any, exc: Exception) -> None:
    failed = await state_manager.load_state(workflow_id) or initial_state
    failed.status = WorkflowStatus.FAILED
    failed.completed_at = datetime.now(UTC)
    # Server-side: log full repr for diagnostics; persistence gets sanitized/truncated entry
    logger.error("workflow_failure_persisted", exc_info=exc)
    sanitized = f"{type(exc).__name__}: workflow_failure"
    failed.errors.append(sanitized)
    await state_manager.save_state(workflow_id, failed)
