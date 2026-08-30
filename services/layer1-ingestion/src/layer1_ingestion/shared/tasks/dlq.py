"""Dead-letter recording task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from typing import Any
from uuid import UUID

from value_fabric.shared.error_handling import sanitize_log_error

from ...metrics.prometheus_metrics import get_metrics
from ..database import get_db_session
from ..dlq import DLQ_QUEUE_NAME
from ..models import (
    JobError,
    ScrapingJob,
)
from ..tasks import (
    celery_app,
    logger,
)


@celery_app.task(name="layer1_ingestion.shared.tasks.record_dead_lettered_task", queue=DLQ_QUEUE_NAME, max_retries=0)
def record_dead_lettered_task(envelope: dict[str, Any]) -> dict[str, Any]:
    """Consume a dead-letter envelope and durably record the failure (P0-02).

    Persists a JobError with error_code TASK_DEAD_LETTERED and stage
    DEAD_LETTER when the envelope carries a tenant_id + job_id. Missing
    context is handled log-only so the DLQ consumer itself does not spin.
    """
    tenant_id = envelope.get("tenant_id")
    job_id = envelope.get("job_id")
    original_task = envelope.get("original_task", "unknown")

    try:
        metrics = get_metrics()
        if metrics:
            metrics.increment_task_dead_lettered(original_task=original_task)
    except Exception as exc:
        logger.warning("Failed to increment DLQ metric", error=sanitize_log_error(exc))

    if not tenant_id or not job_id:
        logger.warning(
            "Dead-letter envelope missing tenant_id or job_id; log-only",
            envelope=envelope,
        )
        return {"recorded": False, "reason": "missing_tenant_or_job"}

    try:
        tenant_uuid = UUID(tenant_id)
        job_uuid = UUID(job_id)
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_uuid)
            job_tenant_id = job.tenant_id if job else tenant_uuid
            error_record = JobError(
                job_id=job_uuid,
                tenant_id=job_tenant_id,
                stage="DEAD_LETTER",
                error_code="TASK_DEAD_LETTERED",
                error_message=envelope.get("error")
                or "Task exhausted retries and was dead-lettered",
                retryable=False,
            )
            session.add(error_record)
            session.commit()
            logger.info(
                "Dead-lettered task recorded",
                job_id=str(job_uuid),
                tenant_id=str(tenant_uuid),
                original_task=original_task,
            )
            return {"recorded": True, "job_id": job_id}
    except Exception as exc:
        logger.error(
            "Failed to record dead-lettered task",
            error=sanitize_log_error(exc),
            envelope=envelope,
        )
        raise
