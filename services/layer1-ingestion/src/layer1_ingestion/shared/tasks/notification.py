"""Notification stage task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from datetime import UTC, datetime
from uuid import UUID

from value_fabric.shared.error_handling import sanitize_log_error

from ..database import get_db_session
from ..models import (
    AccountIntelligencePacket,
    EventOutbox,
    JobStatus,
    OutboxStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    SourceCorpus,
)
from ..otel_celery import start_celery_span
from ..task_contracts import notification_stageResult
from ..tasks import (
    _update_stage,
    dispatch_outbox_event,
)
from .tasks_bootstrap import celery_app, logger


@celery_app.task(name="layer1_ingestion.shared.tasks.notification_stage", bind=True)
def notification_stage(self, prev_result: dict, tenant_id: str):
    """Stage 9: Notification (webhooks, callbacks).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting notification stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.notification",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    return notification_stageResult.model_validate(
                        {"success": False, "job_id": str(job_id), "error": "Job not found"}
                    ).model_dump()

                _update_stage(session, job_id, PipelineStage.NOTIFICATION, "RUNNING")
                job.progress_stage = PipelineStage.NOTIFICATION.value
                session.commit()

                # Complete job
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.now(UTC)
                job.progress_percent_complete = 100
                job.progress_stage = PipelineStage.NOTIFICATION.value

                _update_stage(session, job_id, PipelineStage.NOTIFICATION, "COMPLETED")
                session.commit()

                # Update target stats
                target = session.query(ScrapingTarget).get(job.target_id)
                if target:
                    target.success_count += 1
                    target.last_success_at = datetime.now(UTC)
                    # Calculate average execution time
                    if job.started_at and job.completed_at:
                        duration = (job.completed_at - job.started_at).total_seconds() * 1000
                        total_duration = (
                            target.average_execution_time_ms * (target.success_count - 1) + duration
                        )
                        target.average_execution_time_ms = int(
                            total_duration / target.success_count
                        )
                    session.commit()

                # Skill-aware event emission via durable transactional outbox.
                # Events are persisted in the same session as job completion so
                # they are only emitted after durable storage succeeds.
                if job.downstream_events and job.skill_name:
                    # Resolve the output record ID for the event payload.
                    output_id: str | None = None
                    if job.output_contract == "SourceCorpus":
                        corpus = (
                            session.query(SourceCorpus)
                            .filter(
                                SourceCorpus.job_id == job_id,
                                SourceCorpus.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        output_id = str(corpus.id) if corpus else None
                    elif job.output_contract == "AccountIntelligencePacket":
                        packet = (
                            session.query(AccountIntelligencePacket)
                            .filter(
                                AccountIntelligencePacket.job_id == job_id,
                                AccountIntelligencePacket.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        output_id = str(packet.id) if packet else None

                    emitted_at = datetime.now(UTC).isoformat()
                    outbox_ids: list[UUID] = []

                    for event_type in job.downstream_events:
                        outbox_row = EventOutbox(
                            tenant_id=job.tenant_id,
                            event_type=event_type,
                            aggregate_type=job.output_contract or "unknown",
                            aggregate_id=output_id or str(job_id),
                            payload={
                                "event_type": event_type,
                                "tenant_id": str(job.tenant_id),
                                "job_id": str(job_id),
                                "output_contract": job.output_contract,
                                "output_id": output_id,
                                "skill_name": job.skill_name,
                                "aggregate_type": job.output_contract or "unknown",
                                "aggregate_id": output_id or str(job_id),
                                "emitted_at": emitted_at,
                            },
                            status=OutboxStatus.PENDING.value,
                        )
                        session.add(outbox_row)
                        session.flush()
                        outbox_ids.append(outbox_row.id)
                        logger.info(
                            "EventOutbox row created",
                            event_id=str(outbox_row.id),
                            event_type=event_type,
                            job_id=str(job_id),
                            tenant_id=str(job.tenant_id),
                        )

                    # Commit outbox rows together with job completion.
                    session.commit()

                    # Enqueue async dispatch for each outbox row with tenant context
                    for event_id in outbox_ids:
                        dispatch_outbox_event.apply_async(
                            args=[str(event_id), str(job.tenant_id)],
                            countdown=1,
                        )

                logger.info("Job completed successfully", job_id=str(job_id))
                return notification_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id), "error": None}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Notification stage failed",
                job_id=str(job_id),
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.NOTIFICATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            return notification_stageResult.model_validate(
                {"success": False, "job_id": str(job_id), "error": "Notification stage failed"}
            ).model_dump()
