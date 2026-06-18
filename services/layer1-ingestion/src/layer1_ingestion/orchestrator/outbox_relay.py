"""Transactional outbox relay for pipeline events.

Polls the EventOutbox table and dispatches pending events to stage-specific
Celery tasks. The same row is marked dispatched (or failed) on a best-effort
basis; the downstream stage handler is responsible for idempotency.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import EventOutbox, OutboxStatus

from .coordinator import PipelineCoordinator


# Map of stage names to Celery task import paths.  These are populated lazily
# to avoid a circular import with the tasks module.
_STAGE_TASKS: dict[str, str] = {
    "VALIDATING_ACCESS": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "RESOLVING_CONNECTOR": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "FETCHING_SOURCE": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "APPLYING_POLICY": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "NORMALIZING": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "CHUNKING": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "EXTRACTING": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "BUILDING_CLAIMS": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "VALIDATING_CLAIMS": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "PROJECTING_SUMMARY": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "NEEDS_USER_ACTION": "layer1_ingestion.shared.tasks.run_pipeline_stage",
    "FAILED_RETRYABLE": "layer1_ingestion.shared.tasks.run_pipeline_stage",
}

# Maximum dispatch attempts before dead-lettering.
MAX_DISPATCH_ATTEMPTS = 5


def dispatch_pending_pipeline_events(
    db: Session,
    max_events: int = 100,
    dispatcher: Callable[[str, dict[str, Any]], None] | None = None,
) -> int:
    """Dispatch up to ``max_events`` pending pipeline events.

    Returns the number of events dispatched.
    """
    if dispatcher is None:
        dispatcher = _default_celery_dispatcher

    events = (
        db.query(EventOutbox)
        .filter(
            EventOutbox.status == OutboxStatus.PENDING.value,
            EventOutbox.stage_name.isnot(None),
        )
        .order_by(EventOutbox.created_at)
        .limit(max_events)
        .all()
    )

    dispatched = 0
    for event in events:
        try:
            dispatcher(event.stage_name, event.payload)
            event.status = OutboxStatus.DISPATCHED.value
            event.dispatched_at = datetime.now(UTC)
            dispatched += 1
        except Exception as exc:
            event.attempts += 1
            event.last_error = str(exc)
            if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                event.status = OutboxStatus.DEAD_LETTER.value
                event.dead_lettered_at = datetime.now(UTC)
    db.flush()
    return dispatched


def _default_celery_dispatcher(stage_name: str, payload: dict[str, Any]) -> None:
    """Default dispatcher: send a Celery task for the stage."""
    from celery import current_app

    task_name = _STAGE_TASKS.get(stage_name)
    if task_name is None:
        raise ValueError(f"No task registered for stage {stage_name!r}")

    current_app.send_task(
        task_name,
        args=[stage_name, payload],
        queue="ingestion",
    )


def run_pipeline_stage_from_payload(
    db: Session,
    stage_name: str,
    payload: dict[str, Any],
) -> None:
    """Entry point for Celery workers to execute a pipeline stage.

    Loads the run, validates the step, executes the stage handler, and
    advances the run transactionally.
    """
    import uuid

    run_id = uuid.UUID(payload["run_id"])
    tenant_id = uuid.UUID(payload["tenant_id"])

    from .stage_handlers import get_stage_handler

    handler = get_stage_handler(stage_name)
    coordinator = PipelineCoordinator(db)
    handler.run(db, coordinator, run_id, tenant_id, stage_name)
