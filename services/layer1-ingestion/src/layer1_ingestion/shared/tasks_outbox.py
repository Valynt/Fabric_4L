"""Transactional outbox dispatch (facade).

This module re-exports the transactional outbox-relay group from
``layer1_ingestion.shared.tasks``, which remains the single source of truth.
It provides a cohesive import surface for outbox dispatch and pipeline-stage
relay without moving any implementation.

Important: these bindings are snapshots of the canonical module. Celery task
names (including ``run_pipeline_stage`` and ``dispatch_pipeline_outbox_events``,
which are path-derived) and persistent patches keep addressing
``layer1_ingestion.shared.tasks.<name>`` exactly as before.
"""

from .tasks import (
    _emit_dead_letter_audit,
    _handle_dispatch_failure,
    _record_dead_letter_metrics,
    dispatch_outbox_event,
    dispatch_pipeline_outbox_events,
    run_pipeline_stage,
)

__all__ = [
    "_emit_dead_letter_audit",
    "_handle_dispatch_failure",
    "_record_dead_letter_metrics",
    "dispatch_outbox_event",
    "dispatch_pipeline_outbox_events",
    "run_pipeline_stage",
]
