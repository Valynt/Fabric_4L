from __future__ import annotations

"""Checkpoint, replay, and resume helpers for the orchestration executor.

This module intentionally keeps the behavior previously embedded in
``executor.OrchestrationController`` so public controller methods can delegate
without changing their contracts.
"""
import asyncio
import hashlib
import json
import logging
from datetime import datetime as _dt
from typing import Any, TypeVar

from ..models.agent_state import AgentState, BaseAgentState  # noqa: TID252
from ..observability import Layer4LifecycleLogger  # noqa: TID252
from ..policies.replay_conflict import (  # noqa: TID252
    ReplayConflictError,
    ReplayConflictResolver,
    ReplayDecision,
)

logger = logging.getLogger(__name__)
lifecycle_logger = Layer4LifecycleLogger(logger)

_WorkflowErrorT = TypeVar("_WorkflowErrorT", bound=Exception)
_CheckpointConflictT = TypeVar("_CheckpointConflictT", bound=Exception)


def compute_state_hash(state: AgentState) -> str:
    """Compute a deterministic hash for checkpoint conflict detection."""
    canonical = json.dumps(
        {
            "workflow_id": state.workflow_id,
            "run_id": state.run_id,
            "trace_id": state.trace_id,
            "tenant_id": state.tenant_id,
            "workflow_type": str(
                state.workflow_type.value
                if hasattr(state.workflow_type, "value")
                else state.workflow_type
            ),
            "current_node": state.current_node,
            "status": str(
                state.status.value if hasattr(state.status, "value") else state.status
            ),
            "input_data": state.input_data,
            "output_data": state.output_data,
            "metadata": {
                k: v
                for k, v in (state.metadata or {}).items()
                if k not in ("run_envelope", "checkpoint_hash")
            },
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def resolve_resume_policy(
    controller: Any,
    *,
    workflow_id: str,
    state: AgentState,
    workflow_execution_error_type: type[_WorkflowErrorT],
    checkpoint_conflict_error_type: type[_CheckpointConflictT],
    target_checkpoint_id: str | None = None,
) -> None:
    """Validate a resume attempt against the canonical ReplayConflictPolicy."""
    resolver = ReplayConflictResolver()
    checkpoint_hash = controller._compute_state_hash(state)

    expected_hash = (state.metadata or {}).get("checkpoint_hash")

    checkpoint_id = target_checkpoint_id or str(state.current_node or "latest")
    run_id = state.run_id or workflow_id
    latest_hash = await controller._get_latest_persisted_checkpoint_hash(
        tenant_id=str(state.tenant_id),
        workflow_id=workflow_id,
        run_id=run_id,
        checkpoint_id=checkpoint_id,
    )

    workflow_type = str(
        state.workflow_type.value
        if hasattr(state.workflow_type, "value")
        else state.workflow_type
    )
    tenant_id_for_metrics = str(state.tenant_id or "unknown")

    if latest_hash != checkpoint_hash:
        try:
            from ..metrics.prometheus_metrics import get_metrics  # noqa: TID252

            metrics = get_metrics()
            if metrics:
                metrics.increment_checkpoint_collision_outcome(
                    workflow_type=workflow_type,
                    tenant_id=tenant_id_for_metrics,
                    outcome="mismatch",
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug(
                "Failed to record checkpoint collision mismatch metric", exc_info=True
            )
        conflict_metadata = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "checkpoint_id": checkpoint_id,
            "expected_hash": checkpoint_hash,
            "actual_hash": latest_hash,
        }
        lifecycle_logger.emit(
            stage="checkpoint_conflict",
            context=controller._lifecycle_context(
                workflow_id,
                tenant_id=tenant_id_for_metrics,
                checkpoint_id=checkpoint_id,
            ),
            **conflict_metadata,
        )
        raise checkpoint_conflict_error_type(
            "Checkpoint hash mismatch", conflict_metadata
        )
    try:
        from ..metrics.prometheus_metrics import get_metrics  # noqa: TID252

        metrics = get_metrics()
        if metrics:
            metrics.increment_checkpoint_collision_outcome(
                workflow_type=workflow_type,
                tenant_id=tenant_id_for_metrics,
                outcome="match",
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.debug(
            "Failed to record checkpoint collision match metric", exc_info=True
        )

    checkpoint_created_at = state.paused_at or state.started_at
    if isinstance(checkpoint_created_at, str):
        checkpoint_created_at = _dt.fromisoformat(
            checkpoint_created_at.replace("Z", "+00:00")
        )

    try:
        resolver.validate_resume_attempt(
            workflow_status=state.status,
            checkpoint_created_at=checkpoint_created_at,
            checkpoint_hash=checkpoint_hash,
            expected_hash=expected_hash,
            latest_checkpoint_hash=latest_hash,
        )
    except ReplayConflictError as rce:
        raise workflow_execution_error_type(f"Replay conflict: {rce}") from rce

    tenant_id = state.tenant_id or "unknown"
    try:
        decision = resolver.evaluate_duplicate_replay(
            run_id=run_id,
            tenant_id=tenant_id,
            checkpoint_id=target_checkpoint_id,
            seen_fingerprints=controller._seen_replay_fingerprints,
        )
        if decision == ReplayDecision.REJECT:
            raise ReplayConflictError("Replay rejected: duplicate replay detected")
    except ReplayConflictError as rce:
        raise workflow_execution_error_type(f"Replay conflict: {rce}") from rce

    fingerprint = resolver.compute_replay_fingerprint(
        run_id=run_id,
        tenant_id=tenant_id,
        checkpoint_id=target_checkpoint_id,
    )
    controller._seen_replay_fingerprints.add(fingerprint)


async def get_latest_persisted_checkpoint_hash(
    controller: Any,
    *,
    tenant_id: str,
    workflow_id: str,
    run_id: str,
    checkpoint_id: str,
    workflow_execution_error_type: type[_WorkflowErrorT],
) -> str:
    """Load the latest persisted checkpoint hash from durable state."""
    conn = (
        controller.checkpoint_saver.conn
        if controller.checkpoint_saver and hasattr(controller.checkpoint_saver, "conn")
        else None
    )
    if conn is not None and hasattr(conn, "fetchrow"):
        row = await conn.fetchrow(
            """
            SELECT checkpoint->'channel_values' as state_data
            FROM checkpoints
            WHERE thread_id = $1
              AND checkpoint_id = $2
              AND checkpoint->'channel_values'->>'tenant_id' = $3
            ORDER BY created_at DESC
            LIMIT 1
            """,
            workflow_id,
            checkpoint_id,
            tenant_id,
        )
        if row and isinstance(row.get("state_data"), dict):
            return controller._compute_state_hash(
                BaseAgentState.model_validate(row["state_data"])
            )

    latest_state = await controller.state_manager.load_state(workflow_id)
    if latest_state is None:
        raise workflow_execution_error_type(
            f"No persisted checkpoint state for tenant={tenant_id} run_id={run_id} "
            f"workflow_id={workflow_id} checkpoint_id={checkpoint_id}"
        )
    return controller._compute_state_hash(latest_state)


class CheckpointReplayService:
    """Service implementing checkpoint and replay policy behind narrow protocols."""

    def __init__(
        self,
        state_manager: Any,
        checkpoint_saver: Any = None,
        seen_replay_fingerprints: set[str] | None = None,
    ):
        self.state_manager = state_manager
        self.checkpoint_saver = checkpoint_saver
        self._seen_replay_fingerprints = (
            seen_replay_fingerprints if seen_replay_fingerprints is not None else set()
        )

    def _compute_state_hash(self, state: AgentState) -> str:
        return compute_state_hash(state)

    def compute_state_hash(self, state: AgentState) -> str:
        return compute_state_hash(state)

    def _lifecycle_context(
        self,
        workflow_id: str,
        *,
        tenant_id: str | None = None,
        checkpoint_id: str | None = None,
    ) -> Any:
        from ..observability import Layer4EventContext

        kwargs: dict[str, Any] = {
            "request_id": workflow_id,
            "trace_id": workflow_id,
            "tenant_id": tenant_id or "unknown",
            "workflow_id": workflow_id,
            "run_id": workflow_id,
            "provider_name": "langgraph",
        }
        if checkpoint_id is not None:
            kwargs["checkpoint_id"] = checkpoint_id
        return Layer4EventContext(**kwargs)

    async def get_latest_persisted_checkpoint_hash(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        run_id: str,
        checkpoint_id: str,
        workflow_execution_error_type: type[Exception] = RuntimeError,
    ) -> str:
        return await get_latest_persisted_checkpoint_hash(
            self,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            run_id=run_id,
            checkpoint_id=checkpoint_id,
            workflow_execution_error_type=workflow_execution_error_type,
        )

    async def resolve_resume_policy(
        self,
        *,
        workflow_id: str,
        state: AgentState,
        workflow_execution_error_type: type[Exception] = RuntimeError,
        checkpoint_conflict_error_type: type[Exception] = RuntimeError,
        target_checkpoint_id: str | None = None,
    ) -> None:
        await resolve_resume_policy(
            self,
            workflow_id=workflow_id,
            state=state,
            workflow_execution_error_type=workflow_execution_error_type,
            checkpoint_conflict_error_type=checkpoint_conflict_error_type,
            target_checkpoint_id=target_checkpoint_id,
        )
