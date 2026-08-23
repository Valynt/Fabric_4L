from __future__ import annotations

"""Redis-backed durable CRM sync job runner."""


import asyncio
import json
import logging
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy import select
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext

from ..database import db_session_for_context, get_session_factory
from ..integrations.core.observations import (
    sync_interrupted,
    sync_partial,
    sync_started,
    sync_succeeded,
)
from ..integrations.core.state import apply_observation
from ..models.account import CRMProvider
from ..models.crm_sync_job import CRMSyncJob, CRMSyncJobStatus
from .crm_sync_queue import CRM_SYNC_QUEUE_KEY, enqueue_crm_sync_job

logger = logging.getLogger(__name__)


class CRMSyncJobRunner:
    """Consumes queued CRM sync jobs from Redis and executes them durably."""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        await self.recover_pending_jobs()
        self._task = asyncio.create_task(self._run(), name="crm-sync-job-runner")
        logger.info("CRM sync job runner started")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CRM sync job runner stopped")

    async def recover_pending_jobs(self) -> None:
        factory = get_session_factory()
        async with factory() as session:
            from ..database import _mark_session_tenant_bypass  # noqa: PLC2701

            _mark_session_tenant_bypass(session, reason="crm_sync_job_recovery")
            result = await session.execute(
                select(CRMSyncJob).where(
                    CRMSyncJob.status.in_(
                        [CRMSyncJobStatus.QUEUED, CRMSyncJobStatus.RUNNING]
                    )
                )
            )
            jobs = list(result.scalars().all())
        for job in jobs:
            await enqueue_crm_sync_job(
                redis_client=self._redis,
                job_id=str(job.id),
                tenant_id=job.tenant_id,
                provider=str(job.provider.value if hasattr(job.provider, "value") else job.provider),
            )
        if jobs:
            logger.info("Recovered %s CRM sync jobs into Redis queue", len(jobs))

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                item = await self._redis.brpop(CRM_SYNC_QUEUE_KEY, timeout=5)
                if not item:
                    continue
                _, payload = item
                await self._handle_payload(payload)
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                pass
            except Exception:
                logger.exception("CRM sync job runner loop failed")

    async def _handle_payload(self, payload: str) -> None:
        data = json.loads(payload)
        job_id = str(data["job_id"])
        tenant_id = str(data["tenant_id"])
        provider = CRMProvider(str(data["provider"]))
        context = RequestContext(tenant_id=tenant_id)

        async with db_session_for_context(context) as db:
            from .crm_sync_service import CRMSyncService
            from .integration_service import IntegrationService

            integration_service = IntegrationService(db)
            sync_service = CRMSyncService(db)

            result = await db.execute(
                select(CRMSyncJob).where(
                    CRMSyncJob.id == job_id,
                    CRMSyncJob.tenant_id == tenant_id,
                )
            )
            job = result.scalar_one_or_none()
            if job is None or job.status == CRMSyncJobStatus.CANCELLED:
                return

            integration = await integration_service.get_integration(tenant_id, provider)
            if integration is None:
                job.status = CRMSyncJobStatus.FAILED
                job.started_at = job.started_at or datetime.now(UTC)
                job.finished_at = datetime.now(UTC)
                job.error_summary = f"No {provider.value} integration found"
                return

            job.status = CRMSyncJobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            await apply_observation(db, integration, sync_started())

            try:
                stats = await sync_service.sync_provider(provider, tenant_id=tenant_id)
                job.records_synced = int(stats["synced"])
                job.records_updated = int(stats["updated"])
                job.records_failed = int(stats["failed"])
                job.finished_at = datetime.now(UTC)
                if stats["failed"] > 0:
                    job.status = CRMSyncJobStatus.FAILED
                    job.error_summary = "; ".join(stats["errors"][:3]) or "Sync failed"
                    await apply_observation(db, integration, sync_partial())
                    integration.last_error_message = job.error_summary
                else:
                    job.status = CRMSyncJobStatus.SUCCEEDED
                    job.error_summary = None
                    await apply_observation(db, integration, sync_succeeded())
                    integration.last_error_message = None
                    integration.last_successful_sync_at = datetime.now(UTC)
                integration.records_synced = job.records_synced + job.records_updated
                integration.records_updated = job.records_updated
                integration.records_failed = job.records_failed
                integration.last_sync_at = datetime.now(UTC)
                try:
                    await emit_audit_event(
                        action=AuditAction.UPDATE,
                        resource_type="sync_job",
                        resource_id=str(job.id),
                        tenant_id=tenant_id,
                        user_id=job.requested_by,
                        outcome=AuditOutcome.SUCCESS,
                        details={"provider": provider.value, "status": job.status.value},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Failed to emit sync job success audit event")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("CRM sync job failed: tenant=%s provider=%s job_id=%s", tenant_id, provider.value, job_id)
                job.status = CRMSyncJobStatus.FAILED
                job.finished_at = datetime.now(UTC)
                sanitized = f"{type(exc).__name__}: sync_job_failed"
                job.error_summary = sanitized
                await apply_observation(db, integration, sync_interrupted(message=sanitized))
                integration.last_sync_at = datetime.now(UTC)
                integration.last_error_message = sanitized
                try:
                    await emit_audit_event(
                        action=AuditAction.UPDATE,
                        resource_type="sync_job",
                        resource_id=str(job.id),
                        tenant_id=tenant_id,
                        user_id=job.requested_by,
                        outcome=AuditOutcome.FAILURE,
                        details={"provider": provider.value, "error_type": type(exc).__name__},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Failed to emit sync job failure audit event")


