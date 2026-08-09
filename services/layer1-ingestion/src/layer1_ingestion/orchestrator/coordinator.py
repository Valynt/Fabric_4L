"""Pipeline coordinator: transactionally advance ingestion runs and emit outbox events.

All coordinator methods are synchronous and operate on an open SQLAlchemy
session. The caller is responsible for committing the session.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import (
    EventOutbox,
    IngestionRunStatus,
    IngestionRunStep,
    IngestionRunStepStatus,
    OutboxStatus,
    SourceIngestionRun,
)

from .state_machine import PipelineStateMachine


class PipelineCoordinator:
    """Coordinate state transitions, step records, and outbox events."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._state_machine = PipelineStateMachine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_run(self, run: SourceIngestionRun) -> SourceIngestionRun:
        """Create the first pipeline step and advance the run to VALIDATING_ACCESS.

        The run is expected to be freshly created in ACCEPTED state.
        """
        if run.status != IngestionRunStatus.ACCEPTED.value:
            raise ValueError(f"Run must be ACCEPTED to start, got {run.status}")

        self._state_machine.transition(
            IngestionRunStatus.ACCEPTED.value,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        step = self._create_step(
            run,
            IngestionRunStatus.VALIDATING_ACCESS.value,
            IngestionRunStepStatus.PENDING,
        )
        run.status = IngestionRunStatus.VALIDATING_ACCESS.value
        run.current_step_id = step.id
        run.started_at = datetime.now(UTC)
        self._emit_event(
            run,
            event_type="fabric.run.stage_requested.v1",
            stage_name=IngestionRunStatus.VALIDATING_ACCESS.value,
            payload=self._stage_payload(run, step),
        )
        return run

    def advance(
        self,
        run: SourceIngestionRun,
        to_state: str,
        *,
        output_artifact_ids: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_detail_safe: str | None = None,
    ) -> IngestionRunStep:
        """Advance a run to ``to_state`` and create a new step transactionally.

        Completes the current step (if any) and starts the next one.
        """
        self._state_machine.transition(run.status, to_state)

        current_step = self._get_current_step(run)
        if current_step is not None and current_step.status == IngestionRunStepStatus.RUNNING.value:
            self._complete_step(
                current_step,
                output_artifact_ids=output_artifact_ids or {},
            )

        next_step_status = IngestionRunStepStatus.PENDING
        if to_state in (
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        ):
            next_step_status = IngestionRunStepStatus.CANCELLED

        new_step = self._create_step(
            run,
            to_state,
            next_step_status,
            input_artifact_ids=self._artifact_ids_from_step(current_step),
        )
        if error_code:
            new_step.error_code = error_code
            new_step.error_detail_safe = error_detail_safe or ""

        run.status = to_state
        run.current_step_id = new_step.id
        if PipelineStateMachine.is_terminal(to_state):
            run.completed_at = datetime.now(UTC)

        self._emit_event(
            run,
            event_type="fabric.run.stage_requested.v1",
            stage_name=to_state,
            payload=self._stage_payload(run, new_step),
        )
        return new_step

    def mark_step_running(self, step: IngestionRunStep) -> None:
        """Mark a pending step as running and record the start time."""
        if step.status != IngestionRunStepStatus.PENDING.value:
            raise ValueError(f"Step must be PENDING to start, got {step.status}")
        step.status = IngestionRunStepStatus.RUNNING.value
        step.started_at = datetime.now(UTC)

    def mark_step_completed(
        self,
        step: IngestionRunStep,
        output_artifact_ids: dict[str, Any],
    ) -> None:
        """Mark a running step as completed with output artifact references."""
        if step.status != IngestionRunStepStatus.RUNNING.value:
            raise ValueError(f"Step must be RUNNING to complete, got {step.status}")
        self._complete_step(step, output_artifact_ids)

    def mark_step_failed(
        self,
        step: IngestionRunStep,
        error_code: str,
        error_detail_safe: str,
    ) -> None:
        """Mark a running step as failed."""
        if step.status != IngestionRunStepStatus.RUNNING.value:
            raise ValueError(f"Step must be RUNNING to fail, got {step.status}")
        step.status = IngestionRunStepStatus.FAILED.value
        step.error_code = error_code
        step.error_detail_safe = error_detail_safe
        step.completed_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_step(
        self,
        run: SourceIngestionRun,
        stage_name: str,
        status: IngestionRunStepStatus,
        input_artifact_ids: dict[str, Any] | None = None,
    ) -> IngestionRunStep:
        attempt = self._next_attempt(run, stage_name)
        step = IngestionRunStep(
            id=uuid.uuid4(),
            tenant_id=run.tenant_id,
            run_id=run.id,
            stage_name=stage_name,
            attempt=attempt,
            status=status.value,
            input_artifact_ids=input_artifact_ids or {},
            output_artifact_ids={},
        )
        self._db.add(step)
        self._db.flush()
        return step

    def _next_attempt(self, run: SourceIngestionRun, stage_name: str) -> int:
        from sqlalchemy import func

        last_attempt = (
            self._db.query(func.coalesce(func.max(IngestionRunStep.attempt), 0))
            .filter(
                IngestionRunStep.run_id == run.id,
                IngestionRunStep.stage_name == stage_name,
            )
            .scalar()
        )
        return int(last_attempt) + 1

    def _get_current_step(self, run: SourceIngestionRun) -> IngestionRunStep | None:
        if run.current_step_id is None:
            return None
        return (
            self._db.query(IngestionRunStep)
            .filter(IngestionRunStep.id == run.current_step_id)
            .first()
        )

    def _complete_step(
        self,
        step: IngestionRunStep,
        output_artifact_ids: dict[str, Any],
    ) -> None:
        step.status = IngestionRunStepStatus.COMPLETED.value
        step.output_artifact_ids = output_artifact_ids
        step.completed_at = datetime.now(UTC)

    def _artifact_ids_from_step(
        self, step: IngestionRunStep | None
    ) -> dict[str, Any]:
        if step is None:
            return {}
        return dict(step.output_artifact_ids or {})

    def _emit_event(
        self,
        run: SourceIngestionRun,
        event_type: str,
        stage_name: str,
        payload: dict[str, Any],
    ) -> EventOutbox:
        event = EventOutbox(
            id=uuid.uuid4(),
            tenant_id=run.tenant_id,
            event_type=event_type,
            aggregate_type="source_ingestion_run",
            aggregate_id=str(run.id),
            stage_name=stage_name,
            topic=f"fabric.run.{stage_name.lower()}",
            payload=payload,
            status=OutboxStatus.PENDING,
        )
        self._db.add(event)
        self._db.flush()
        return event

    def _stage_payload(
        self,
        run: SourceIngestionRun,
        step: IngestionRunStep,
    ) -> dict[str, Any]:
        return {
            "tenant_id": str(run.tenant_id),
            "run_id": str(run.id),
            "source_id": str(run.source_id),
            "source_version_id": str(run.source_version_id),
            "stage_name": step.stage_name,
            "attempt": step.attempt,
            "step_id": str(step.id),
            "input_artifact_ids": step.input_artifact_ids or {},
            "correlation_id": run.correlation_id,
            "requested_outputs": run.requested_outputs or [],
            "emitted_at": datetime.now(UTC).isoformat(),
        }
