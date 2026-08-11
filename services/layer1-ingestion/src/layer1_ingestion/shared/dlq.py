"""Dead-letter queue (DLQ) routing helpers for Layer 1 Celery tasks (P0-02 / V1-QUEUE-001).

The ``layer1_dlq`` queue was declared in Celery config (``task_queues``) but
nothing ever routed to it: Celery's Redis transport has no broker-side
dead-lettering, so a task failing its final retry vanished with only a log
line. ``tasks.py`` wires these helpers into the Celery ``task_failure`` signal
(exhausted tasks are republished to ``layer1_dlq``) and into the DLQ consumer
task (durable dead-letter recording).

Hermetic module: standard library only, so the routing policy can be
unit-tested without the Celery/HTTP/Playwright service stack.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

DLQ_QUEUE_NAME = "layer1_dlq"
DLQ_TASK_NAME = "layer1_ingestion.shared.tasks.record_dead_lettered_task"
MAX_ERROR_LENGTH = 500


def should_route_to_dlq(retries: int, max_retries: int | None) -> bool:
    """Return True when a failed task has exhausted its retry budget.

    ``max_retries=None`` means retry forever — such tasks are never
    dead-lettered. With ``max_retries=0`` the first failure routes
    immediately (``retries >= 0``).
    """
    if max_retries is None:
        return False
    return retries >= max_retries


def extract_failure_context(args: Any, kwargs: Any) -> tuple[str | None, str | None]:
    """Best-effort (tenant_id, job_id) extraction from a failed task's payload.

    Recognised shapes:
    - kwargs: ``tenant_id=...``, ``job_id=...`` (always wins)
    - pipeline stage tasks: ``(prev_result_dict_with_job_id, tenant_id)``
    - orchestrator tasks: ``(job_id, tenant_id)``

    Never fabricates: unknown shapes yield ``(None, None)`` and the DLQ
    consumer falls back to log-only recording.
    """
    kwargs = kwargs if isinstance(kwargs, dict) else {}
    tenant_id = kwargs.get("tenant_id")
    job_id = kwargs.get("job_id")

    positional = list(args) if isinstance(args, (list, tuple)) else []
    if tenant_id is None and len(positional) >= 2 and isinstance(positional[1], str):
        tenant_id = positional[1]
    if job_id is None and positional:
        first = positional[0]
        if isinstance(first, str):
            job_id = first
        elif isinstance(first, dict) and isinstance(first.get("job_id"), str):
            job_id = first["job_id"]

    return (
        str(tenant_id) if tenant_id is not None else None,
        str(job_id) if job_id is not None else None,
    )


def build_dlq_envelope(
    *,
    task_name: str,
    task_id: str | None,
    tenant_id: str | None,
    job_id: str | None,
    error: str | None,
    retries: int,
    max_retries: int | None,
) -> dict[str, Any]:
    """Build the bounded dead-letter envelope published to ``layer1_dlq``."""
    bounded_error = (error or "")[:MAX_ERROR_LENGTH] or None
    return {
        "original_task": task_name,
        "original_task_id": task_id,
        "error": bounded_error,
        "retries_exhausted": retries,
        "max_retries": max_retries,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "dead_lettered_at": datetime.now(UTC).isoformat(),
    }
