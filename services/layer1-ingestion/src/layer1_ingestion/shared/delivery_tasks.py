"""Pipeline notification and transactional outbox delivery tasks."""

from datetime import UTC, datetime
from uuid import UUID

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error

from ..shared.models import (
    AccountIntelligencePacket,
    EventOutbox,
    JobStatus,
    OutboxStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    SourceCorpus,
)
from ..shared.otel_celery import start_celery_span
from .task_contracts import (
    notification_stageResult,
)

__all__ = [
    "notification_stage",
    "dispatch_outbox_event",
    "_handle_dispatch_failure",
    "_emit_dead_letter_audit",
    "_record_dead_letter_metrics",
    "run_pipeline_stage",
    "dispatch_pipeline_outbox_events",
]

from . import tasks as _compat
from .tasks import (
    MAX_DISPATCH_ATTEMPTS,
    celery_app,
)


@celery_app.task(name="layer1_ingestion.shared.tasks.notification_stage", bind=True)
def notification_stage(self, prev_result: dict, tenant_id: str):
    """Stage 9: Notification (webhooks, callbacks).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    _compat.logger.info(
        "Starting notification stage", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )
    with start_celery_span(
        self,
        "l1.pipeline.notification",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    return notification_stageResult.model_validate(
                        {"success": False, "job_id": str(job_id), "error": "Job not found"}
                    ).model_dump()

                _compat._update_stage(session, job_id, PipelineStage.NOTIFICATION, "RUNNING")
                job.progress_stage = PipelineStage.NOTIFICATION.value
                session.commit()

                # Complete job
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.now(UTC)
                job.progress_percent_complete = 100
                job.progress_stage = PipelineStage.NOTIFICATION.value

                _compat._update_stage(session, job_id, PipelineStage.NOTIFICATION, "COMPLETED")
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
                        _compat.logger.info(
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

                _compat.logger.info("Job completed successfully", job_id=str(job_id))
                return notification_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id), "error": None}
                ).model_dump()

        except Exception as exc:
            _compat.logger.error(
                "Notification stage failed",
                job_id=str(job_id),
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _compat._update_stage(
                    session,
                    job_id,
                    PipelineStage.NOTIFICATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            return notification_stageResult.model_validate(
                {"success": False, "job_id": str(job_id), "error": "Notification stage failed"}
            ).model_dump()


# =============================================================================
# EVENT OUTBOX DISPATCHER
# =============================================================================


@celery_app.task(
    name="layer1_ingestion.shared.tasks.dispatch_outbox_event",
    bind=True,
    max_retries=MAX_DISPATCH_ATTEMPTS,
    default_retry_delay=30,
)
def dispatch_outbox_event(self, event_id: str, tenant_id: str):
    """Deliver a single EventOutbox record to configured sinks.

    On success: marks the row as dispatched.
    On failure: increments attempts, records last_error, retries with backoff.
    After MAX_DISPATCH_ATTEMPTS: moves to dead_letter.

    The initial sink is a structured log. The architecture supports adding
    HTTP adapter or other delivery mechanisms without changing this task.

    Args:
        event_id: The event UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    event_uuid = UUID(event_id)
    tenant_uuid = UUID(tenant_id)

    with start_celery_span(
        self,
        "l1.pipeline.dispatch_outbox",
        attributes={"event_id": str(event_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                _compat.logger.warning("EventOutbox row not found", event_id=event_id)
                return

            # Idempotency: skip if already dispatched or dead-lettered.
            if event.status in (OutboxStatus.DISPATCHED.value, OutboxStatus.DEAD_LETTER.value):
                _compat.logger.info(
                    "EventOutbox already settled, skipping",
                    event_id=event_id,
                    status=event.status,
                )
                return

            # Deliver to configured sink.
            # Initial implementation: structured log (no-op delivery).
            # Future: HTTP adapter, internal service call, etc.
            _compat.logger.info(
                "Dispatching outbox event",
                event_id=event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                tenant_id=str(event.tenant_id),
                payload=event.payload,
            )

            # Mark dispatched.
            event.status = OutboxStatus.DISPATCHED.value
            event.dispatched_at = datetime.now(UTC)
            session.commit()

            _compat.logger.info(
                "EventOutbox dispatched",
                event_id=event_id,
                event_type=event.event_type,
            )

        except Exception as exc:
            _compat.logger.error(
                "EventOutbox dispatch failed",
                event_id=event_id,
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(exc),
                attempt=self.request.retries + 1,
            )

            should_retry = _handle_dispatch_failure(
                event_uuid, tenant_uuid, exc, self.request.retries
            )

            if not should_retry:
                return  # Dead-lettered, do not retry

            # Retry with exponential backoff.
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="notification", reason="dispatch_failure")
            raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))


def _handle_dispatch_failure(
    event_uuid: UUID, tenant_uuid: UUID, exc: Exception, current_retries: int
) -> bool:
    """Handle dispatch failure and return whether to retry.

    Returns False if event was dead-lettered (no retry), True otherwise.
    """
    try:
        with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                _compat.logger.warning(
                    "EventOutbox not found for failure handling, skipping retry",
                    event_id=str(event_uuid),
                )
                return False

            event.attempts = (event.attempts or 0) + 1
            event.last_error = sanitize_log_error(exc)[:200]

            if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                event.status = OutboxStatus.DEAD_LETTER.value
                event.dead_lettered_at = datetime.now(UTC)
                _compat.logger.error(
                    "EventOutbox dead-lettered after max attempts",
                    event_id=str(event_uuid),
                    event_type=event.event_type,
                    attempts=event.attempts,
                )
                _emit_dead_letter_audit(event_uuid, tenant_uuid, event)
                _record_dead_letter_metrics()
                session.commit()
                return False  # Do not retry dead-lettered events
            else:
                event.status = OutboxStatus.FAILED.value
                session.commit()
                return True
    except Exception as inner_exc:
        _compat.logger.error(
            "Failed to record outbox dispatch error",
            event_id=str(event_uuid),
            error_code="NOTIFICATION_ERROR",
            error=sanitize_log_error(inner_exc),
        )
        return True


def _emit_dead_letter_audit(event_uuid: UUID, tenant_uuid: UUID, event):
    """Emit audit event for dead-lettered outbox event."""
    try:
        emit_audit_event(
            action=AuditAction.OUTBOX_DEAD_LETTERED,
            outcome=AuditOutcome.FAILURE,
            tenant_id=tenant_uuid,
            resource_type="EventOutbox",
            resource_id=str(event_uuid),
            details={
                "event_type": event.event_type,
                "attempts": event.attempts,
                "last_error": event.last_error,
            },
        )
    except Exception:
        _compat.logger.exception("outbox_dead_lettered_audit_failed")


def _record_dead_letter_metrics():
    """Record metrics for dead-lettered events."""
    metrics = _compat.get_metrics()
    if metrics:
        metrics.increment_outbox_dead_lettered()


# =============================================================================
# CANONICAL SOURCE INGESTION PIPELINE ORCHESTRATOR
# =============================================================================


@celery_app.task(name="layer1_ingestion.shared.tasks.run_pipeline_stage", bind=True, max_retries=3)
def run_pipeline_stage(self, stage_name: str, payload: dict):
    """Execute a single stage of the canonical source ingestion pipeline.

    Loads the run, validates the current step, delegates to the stage handler,
    and advances the run transactionally.

    Args:
        stage_name: IngestionRunStatus value for the stage to execute.
        payload: Outbox event payload containing run_id, tenant_id, etc.
    """
    import uuid

    from layer1_ingestion.orchestrator.outbox_relay import run_pipeline_stage_from_payload

    run_id = uuid.UUID(payload["run_id"])
    tenant_uuid = uuid.UUID(payload["tenant_id"])

    try:
        with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            run_pipeline_stage_from_payload(session, stage_name, payload)
            session.commit()
        _compat.logger.info(
            "Pipeline stage completed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
        )
    except Exception as exc:
        _compat.logger.error(
            "Pipeline stage failed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
            error=sanitize_log_error(exc),
        )
        # Retry with exponential backoff.
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task(name="layer1_ingestion.shared.tasks.dispatch_pipeline_outbox_events")
def dispatch_pipeline_outbox_events(max_events: int = 100):
    """Poll and dispatch pending pipeline events from the transactional outbox.

    This task is intended to be run on a Celery beat schedule.
    """
    from layer1_ingestion.orchestrator.outbox_relay import dispatch_pending_pipeline_events

    # We need a tenant context to query, but the relay handles all tenants.
    # Use a system/no-tenant session for the poll; downstream handlers enforce
    # tenant context per event.
    with _compat.get_db_session(require_tenant=False) as session:
        dispatched = dispatch_pending_pipeline_events(session, max_events=max_events)
        session.commit()

    _compat.logger.info(
        "Pipeline outbox relay dispatched events",
        dispatched_count=dispatched,
    )
    return {"dispatched": dispatched}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
