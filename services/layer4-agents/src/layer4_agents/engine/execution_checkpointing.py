from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from ..models.agent_state import WorkflowStatus


async def persist_interruption_if_needed(*, state_manager: Any, workflow_id: str) -> None:
    paused = await state_manager.load_state(workflow_id)
    if paused and paused.status in {WorkflowStatus.PAUSED, WorkflowStatus.INTERRUPTED}:
        return
    if paused:
        paused.status = WorkflowStatus.INTERRUPTED
        paused.metadata["interrupted_at"] = datetime.now(UTC).isoformat()
        paused.metadata["interruption_reason"] = "task cancellation"
        await state_manager.save_state(workflow_id, paused)


def record_checkpoint_corruption(
    workflow_type: str,
    tenant_id: str,
    reason: str = "hash_mismatch",
) -> None:
    """Emit checkpoint corruption metric if metrics are initialized.

    Args:
        workflow_type: Type of workflow whose checkpoint is corrupted.
        tenant_id: Owning tenant identifier.
        reason: Classification of corruption (e.g. 'hash_mismatch', 'unreadable').
    """
    try:
        from ..metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics:
            metrics.increment_checkpoint_corruption(
                workflow_type=workflow_type,
                tenant_id=tenant_id,
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        pass
