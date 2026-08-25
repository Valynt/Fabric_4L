from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..models.agent_state import WorkflowStatus

logger = logging.getLogger(__name__)


def _fmt_enum(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


async def mark_workflow_running(
    *, state_manager: Any, workflow_id: str, initial_state: Any
) -> None:
    initial_state.status = WorkflowStatus.RUNNING
    initial_state.started_at = initial_state.started_at or datetime.now(UTC)
    await state_manager.save_state(workflow_id, initial_state)


async def persist_workflow_failure(
    *, state_manager: Any, workflow_id: str, initial_state: Any, exc: Exception
) -> None:
    failed = await state_manager.load_state(workflow_id) or initial_state
    failed.status = WorkflowStatus.FAILED
    failed.completed_at = datetime.now(UTC)
    # Server-side: log full repr for diagnostics; persistence gets sanitized/truncated entry
    logger.error("workflow_failure_persisted", exc_info=exc)
    sanitized = f"{type(exc).__name__}: workflow_failure"
    failed.errors.append(sanitized)
    await state_manager.save_state(workflow_id, failed)


async def archive_workflow_state(
    *,
    state_manager: Any,
    workflow_id: str,
    tenant_id: str | None = None,
    workflow_tenant: str | None = None,
    workflow_metadata: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Archive workflow state scoped by tenant."""
    state = await state_manager.load_state(workflow_id)
    if not state:
        return None

    resolved_tenant = workflow_tenant
    if resolved_tenant is None and workflow_metadata:
        resolved_tenant = workflow_metadata.get(workflow_id, {}).get("tenant_id")
    if resolved_tenant is None and hasattr(state, "tenant_id"):
        resolved_tenant = getattr(state, "tenant_id", None)

    if tenant_id and resolved_tenant and str(resolved_tenant) != str(tenant_id):
        raise PermissionError(
            f"Workflow {workflow_id} belongs to tenant {resolved_tenant}, not {tenant_id}"
        )

    if state.metadata.get("archived"):
        return {"archived_at": state.metadata.get("archived_at")}

    state.metadata["archived"] = True
    state.metadata["archived_at"] = datetime.now(UTC).isoformat()
    await state_manager.save_state(workflow_id, state)
    return {"archived_at": state.metadata["archived_at"]}


async def recover_orphaned_workflow_states(
    *,
    state_manager: Any,
    active_workflow_ids: set[str],
    format_enum: Any | None = None,
) -> list[dict[str, Any]]:
    """Scan and recover orphaned workflows from state manager."""
    logger.info("Scanning for orphaned workflows to recover...")
    formatter = format_enum or _fmt_enum
    orphaned_ids = await state_manager.list_active_workflows()
    recovered = []

    for workflow_id in orphaned_ids:
        if workflow_id in active_workflow_ids:
            continue

        try:
            state = await state_manager.load_state(workflow_id)
            if not state:
                continue

            state.status = WorkflowStatus.INTERRUPTED
            state.errors.append(
                f"Workflow interrupted by pod restart at {datetime.now(UTC).isoformat()}. "
                "Resume manually or via API."
            )
            await state_manager.save_state(workflow_id, state)

            recovered.append(
                {
                    "workflow_id": workflow_id,
                    "workflow_type": formatter(state.workflow_type),
                    "status": formatter(state.status),
                    "previous_status": "RUNNING",
                    "current_node": state.current_node,
                    "recovery_available": True,
                }
            )

            logger.warning(
                f"Marked orphaned workflow {workflow_id} as INTERRUPTED "
                f"(was at node: {state.current_node})"
            )

        except (ValueError, RuntimeError) as e:
            logger.error(
                "Failed to recover workflow",
                extra={"workflow_id": workflow_id, "error_type": type(e).__name__},
                exc_info=True,
            )
            recovered.append(
                {
                    "workflow_id": workflow_id,
                    "status": "ERROR",
                    "error": "Workflow recovery failed",
                    "error_code": "WORKFLOW_RECOVERY_ERROR",
                }
            )

    if recovered:
        logger.info(
            "Recovery complete: %d workflows marked as INTERRUPTED", len(recovered)
        )
    else:
        logger.info("No orphaned workflows found")

    return recovered


class WorkflowLifecyclePersistenceService:
    """Service implementing lifecycle persistence behind narrow protocols."""

    def __init__(self, state_manager: Any):
        self.state_manager = state_manager

    async def mark_workflow_running(self, workflow_id: str, initial_state: Any) -> None:
        await mark_workflow_running(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
            initial_state=initial_state,
        )

    async def persist_workflow_failure(
        self, workflow_id: str, initial_state: Any, exc: Exception
    ) -> None:
        await persist_workflow_failure(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
            initial_state=initial_state,
            exc=exc,
        )

    async def persist_interruption_if_needed(self, workflow_id: str) -> None:
        from .execution_checkpointing import persist_interruption_if_needed

        await persist_interruption_if_needed(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
        )

    async def archive_workflow(
        self,
        workflow_id: str,
        tenant_id: str | None = None,
        workflow_tenant: str | None = None,
    ) -> dict[str, Any] | None:
        return await archive_workflow_state(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            workflow_tenant=workflow_tenant,
        )

    async def recover_workflows(
        self, active_workflow_ids: set[str]
    ) -> list[dict[str, Any]]:
        return await recover_orphaned_workflow_states(
            state_manager=self.state_manager,
            active_workflow_ids=active_workflow_ids,
        )
