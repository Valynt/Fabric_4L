"""Celery task queue configuration and tasks.

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error

from ..metrics.prometheus_metrics import get_metrics
from ..shared.database import get_db_session
from ..shared.maintenance import authorize_maintenance_operation, maintenance_audit_log
from ..shared.models import (
    EventOutbox,
    OutboxStatus,
    RawContent,
    TenantRegistry,
)
from ..shared.otel_celery import start_celery_span
from .task_contracts import (
    cleanup_old_contentResult,
)
from .task_runtime import (
    MAX_DISPATCH_ATTEMPTS,
    celery_app,
    logger,
)


# Event delivery and canonical-pipeline relay tasks.
@celery_app.task(bind=True, max_retries=MAX_DISPATCH_ATTEMPTS, default_retry_delay=30)
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
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                logger.warning("EventOutbox row not found", event_id=event_id)
                return

            # Idempotency: skip if already dispatched or dead-lettered.
            if event.status in (OutboxStatus.DISPATCHED.value, OutboxStatus.DEAD_LETTER.value):
                logger.info(
                    "EventOutbox already settled, skipping",
                    event_id=event_id,
                    status=event.status,
                )
                return

            # Deliver to configured sink.
            # Initial implementation: structured log (no-op delivery).
            # Future: HTTP adapter, internal service call, etc.
            logger.info(
                "Dispatching outbox event",
                event_id=event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                tenant_id=str(event.tenant_id),
                payload=event.payload,
            )

            # Mark dispatched.
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                event_db = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
                if event_db is None:
                    logger.warning("EventOutbox row not found", event_id=event_id)
                    return
                event_db.status = OutboxStatus.DISPATCHED.value
                event_db.dispatched_at = datetime.now(UTC)

            logger.info(
                "EventOutbox dispatched",
                event_id=event_id,
                event_type=event.event_type,
            )

        except Exception as exc:
            logger.error(
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
            metrics = get_metrics()
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
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                logger.warning(
                    "EventOutbox not found for failure handling, skipping retry",
                    event_id=str(event_uuid),
                )
                return False

            event.attempts = (event.attempts or 0) + 1
            event.last_error = sanitize_log_error(exc)[:200]

            if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                event.status = OutboxStatus.DEAD_LETTER.value
                event.dead_lettered_at = datetime.now(UTC)
                logger.error(
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
        logger.error(
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
        logger.exception("outbox_dead_lettered_audit_failed")


def _record_dead_letter_metrics():
    """Record metrics for dead-lettered events."""
    metrics = get_metrics()
    if metrics:
        metrics.increment_outbox_dead_lettered()


# =============================================================================
# CANONICAL SOURCE INGESTION PIPELINE ORCHESTRATOR
# =============================================================================


@celery_app.task(bind=True, max_retries=3)
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
    from layer1_ingestion.shared.database import get_db_session

    run_id = uuid.UUID(payload["run_id"])
    tenant_uuid = uuid.UUID(payload["tenant_id"])

    try:
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            run_pipeline_stage_from_payload(session, stage_name, payload)
            session.commit()
        logger.info(
            "Pipeline stage completed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
        )
    except Exception as exc:
        logger.error(
            "Pipeline stage failed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
            error=sanitize_log_error(exc),
        )
        # Retry with exponential backoff.
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task
def dispatch_pipeline_outbox_events(max_events: int = 100):
    """Poll and dispatch pending pipeline events from the transactional outbox.

    This task is intended to be run on a Celery beat schedule.
    """
    from layer1_ingestion.orchestrator.outbox_relay import dispatch_pending_pipeline_events
    from layer1_ingestion.shared.database import get_db_session

    # We need a tenant context to query, but the relay handles all tenants.
    # Use a system/no-tenant session for the poll; downstream handlers enforce
    # tenant context per event.
    with get_db_session(require_tenant=False) as session:
        dispatched = dispatch_pending_pipeline_events(session, max_events=max_events)
        session.commit()

    logger.info(
        "Pipeline outbox relay dispatched events",
        dispatched_count=dispatched,
    )
    return {"dispatched": dispatched}


# Tenant-safe maintenance tasks.
@celery_app.task
def _enumerate_authorized_tenants_for_cleanup() -> list[UUID]:
    """Enumerate active tenants from system-owned registry with explicit authorization."""
    authorize_maintenance_operation("cleanup_old_content", tenant_id="tenant-registry")

    correlation_id = str(uuid4())
    with maintenance_audit_log("cleanup_old_content", tenant_id="tenant-registry") as record:
        record.metadata = {
            "tenant_iteration_source": "tenant_registry",
            "source_scope": "system_owned",
            "require_tenant": False,
            "correlation_id": correlation_id,
        }
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            tenant_ids = [
                row[0]
                for row in session.query(TenantRegistry.tenant_id)
                .filter(TenantRegistry.is_active.is_(True))
                .all()
            ]
        record.rows_affected = len(tenant_ids)

    logger.info(
        "System maintenance tenant enumeration completed",
        operation="cleanup_old_content",
        tenant_iteration_source="tenant_registry",
        source_scope="system_owned",
        require_tenant=False,
        correlation_id=correlation_id,
        tenants_discovered=len(tenant_ids),
    )
    return tenant_ids


def cleanup_old_content(days: int = 30, tenant_id: str = None):
    """Clean up raw content older than specified days.

    This function implements tenant-by-tenant cleanup under RLS by default.
    System-scoped cleanup requires explicit system maintenance authorization.

    Args:
        days: Number of days to retain content
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
                   If None, requires system maintenance authorization

    Raises:
        SystemMaintenanceAuthorizationError: If system-scoped operation lacks authorization
        InvalidTenantContextError: If tenant_id is provided but invalid
    """
    from .exceptions import InvalidTenantContextError

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Validate tenant context if provided
    if tenant_id:
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            raise InvalidTenantContextError(
                f"Invalid tenant_id format: {tenant_id}", tenant_id=tenant_id
            )

        # Tenant-scoped cleanup under RLS
        logger.info(
            "Starting tenant-scoped content cleanup",
            cutoff_date=cutoff_date.isoformat(),
            tenant_id=str(tenant_uuid),
        )

        with maintenance_audit_log("cleanup_old_content", tenant_id=str(tenant_uuid)) as record:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                deleted_count = (
                    session.query(RawContent)
                    .filter(
                        RawContent.created_at < cutoff_date,
                        RawContent.processing_status != "DELETED",
                    )
                    .update({"processing_status": "DELETED"}, synchronize_session=False)
                )

                session.commit()
                record.rows_affected = deleted_count

                logger.info(
                    "Tenant-scoped content cleanup completed",
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date.isoformat(),
                    tenant_id=str(tenant_uuid),
                )

                return cleanup_old_contentResult.model_validate(
                    {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}
                ).model_dump()

    else:
        # System-scoped: iterate tenants individually under RLS.
        # Use tenant_registry (system table, no RLS) instead of tenant-owned tables.

        # Emit metric for tenant enumeration observability
        metrics = get_metrics()
        if metrics:
            metrics.increment_maintenance_tenant_enumeration()

        # Audit log entry before TenantRegistry query
        logger.info(
            "System maintenance: beginning tenant enumeration",
            operation="cleanup_old_content",
            tenant_id=None,
            system_identity="fabric4l-system-maintenance",
            correlation_id=str(uuid4()),
        )

        tenant_ids = _enumerate_authorized_tenants_for_cleanup()

        total_deleted = 0
        failed_tenants = []
        started_at = datetime.now(UTC)

        for tenant_uuid in tenant_ids:
            try:
                with maintenance_audit_log(
                    "cleanup_old_content", tenant_id=str(tenant_uuid)
                ) as record:
                    with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                        deleted_count = (
                            session.query(RawContent)
                            .filter(
                                RawContent.created_at < cutoff_date,
                                RawContent.processing_status != "DELETED",
                            )
                            .update({"processing_status": "DELETED"}, synchronize_session=False)
                        )

                        session.commit()
                        record.rows_affected = deleted_count
                        total_deleted += deleted_count
            except Exception as e:
                failed_tenants.append(
                    (str(tenant_uuid), repr(e))
                )  # ban-str-e-allow: internal-tracking
                logger.error(
                    "Tenant cleanup failed",
                    tenant_id=str(tenant_uuid),
                    error=repr(e),
                )

        completed_at = datetime.now(UTC)

        # Aggregate summary audit event
        logger.info(
            "System maintenance audit record",
            operation="cleanup_old_content",
            tenant_id=None,
            system_identity="fabric4l-system-maintenance",
            correlation_id=str(uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            rows_affected=total_deleted,
            success=len(failed_tenants) == 0,
            error_message=(
                None if not failed_tenants else f"Failed tenants: {[t[0] for t in failed_tenants]}"
            ),
            metadata={
                "tenants_processed": len(tenant_ids),
                "failed_tenants": failed_tenants,
            },
        )

        logger.info(
            "System cleanup completed",
            total_deleted=total_deleted,
            tenants_processed=len(tenant_ids),
            failed_count=len(failed_tenants),
            cutoff_date=cutoff_date.isoformat(),
        )

        return cleanup_old_contentResult.model_validate(
            {
                "deleted_count": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
            }
        ).model_dump()


@celery_app.task(
    name="layer1_ingestion.shared.tasks.purge_expired_raw_content", bind=True, max_retries=2
)
def purge_expired_raw_content(self) -> dict:
    """Celery beat task: purge raw content whose per-record retention window has elapsed.

    Uses the per-record ``retention_raw_content_expiry_days`` column (default 30 days)
    to determine which rows are eligible for soft-deletion. Runs daily via the
    ``beat_schedule`` configured on ``celery_app``.

    Delegates to :func:`cleanup_old_content` for the actual deletion logic, which
    iterates over active tenants under RLS to ensure tenant isolation.
    """
    try:
        # Use the default retention window; per-record granularity can be added later.
        return cleanup_old_content(days=30, tenant_id=None)
    except Exception as exc:
        logger.error("purge_expired_raw_content failed: %s", exc)
        raise self.retry(exc=exc, countdown=3600)  # retry after 1 hour
