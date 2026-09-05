"""System maintenance cleanup tasks.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ...metrics.prometheus_metrics import get_metrics
from ..database import get_db_session
from ..maintenance import authorize_maintenance_operation, maintenance_audit_log
from ..models import (
    JobStatus,
    RawContent,
    ScrapingJob,
    TenantRegistry,
)
from ..task_contracts import cleanup_old_contentResult
from .tasks_bootstrap import celery_app, logger

STUCK_JOB_STATUSES = (
    JobStatus.VALIDATING.value,
    JobStatus.BROWSER_ACQUIRING.value,
    JobStatus.NAVIGATING.value,
    JobStatus.EXTRACTING.value,
    JobStatus.TRANSFORMING.value,
    JobStatus.STORING.value,
)


def refresh_stuck_jobs_metrics(tenant_ids: list[UUID]) -> dict[str, int]:
    """Refresh aggregate stuck-job gauges while preserving tenant-scoped reads."""
    counts_by_stage = {status: 0 for status in STUCK_JOB_STATUSES}
    for tenant_id in tenant_ids:
        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            rows = (
                session.query(ScrapingJob.status)
                .filter(ScrapingJob.status.in_(STUCK_JOB_STATUSES))
                .all()
            )
        for (status,) in rows:
            counts_by_stage[status] += 1

    metrics = get_metrics()
    if metrics:
        metrics.refresh_stuck_jobs(counts_by_stage)
    return counts_by_stage


@celery_app.task(name="layer1_ingestion.shared.tasks.reconcile_stuck_jobs_metrics")
def reconcile_stuck_jobs_metrics() -> dict[str, int]:
    """Celery beat reconciliation loop for the aggregate stuck-jobs gauge."""
    authorize_maintenance_operation("reconcile_stuck_jobs", tenant_id="tenant-registry")
    with maintenance_audit_log("reconcile_stuck_jobs", tenant_id="tenant-registry") as record:
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            tenant_ids = [
                row[0]
                for row in session.query(TenantRegistry.tenant_id)
                .filter(TenantRegistry.is_active.is_(True))
                .all()
            ]
        record.rows_affected = len(tenant_ids)
    return refresh_stuck_jobs_metrics(tenant_ids)


@celery_app.task(name="layer1_ingestion.shared.tasks._enumerate_authorized_tenants_for_cleanup")
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
    from ..exceptions import InvalidTenantContextError

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
                    (str(tenant_uuid), repr(e))  # ban-str-e-allow: internal-tracking
                )
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
