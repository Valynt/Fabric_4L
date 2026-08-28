from __future__ import annotations

"""Background scheduler for periodic CRM account synchronization.

Integrates CRMSyncService with TaskScheduler for automated background syncing
of Salesforce and HubSpot accounts at configured intervals.

SECURITY: All sync operations run with proper tenant context. The scheduler
enumerates enabled integrations per-tenant and executes sync with RLS-enforced
sessions. Never sets app.tenant_id to empty string.
"""


import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..database import _clear_local_tenant_context, db_session_for_context, get_session_factory
from ..engine.scheduler import TaskScheduler
from ..engine.types import ScheduledTask, TaskPriority
from ..integration.connectors.core.observations import (
    sync_interrupted,
    sync_partial,
    sync_started,
    sync_succeeded,
)
from ..integration.connectors.core.state import apply_observation
from ..models.account import CRMProvider
from ..models.integration import Integration
from .crm_sync_service import CRMSyncService
from .integration_service import IntegrationService


class CRMSyncScheduler_get_statusResult(TypedDictModel):
    batch_size: Any
    running: Any
    scheduled_tasks: Any
    scheduler_stats: Any
    sync_interval_minutes: Any


class CRMSyncScheduler__execute_syncResult(TypedDictModel):
    error: str | None = None
    reason: str | None = None
    skipped: bool | None = None


logger = logging.getLogger(__name__)
_SYNC_JOBS: dict[str, asyncio.Task[None]] = {}


class CRMSyncScheduler:
    """Schedules and manages periodic CRM account synchronization.

        Uses TaskScheduler for background execution with BACKGROUND priority
    to avoid impacting user-facing workflows.

        Configuration:
        - CRM_SYNC_INTERVAL_MINUTES: Default sync interval (default: 60)
        - CRM_SYNC_BATCH_SIZE: Default records per sync batch (default: 100)
        - CRM_SYNC_MAX_TENANTS_PER_BATCH: Max tenants to sync in one sweep (default: 100)
    """

    def __init__(self, scheduler: TaskScheduler | None = None):
        """Initialize the CRM sync scheduler.

        Args:
            scheduler: TaskScheduler instance to use. Creates new if None.
        """
        self._scheduler = scheduler or TaskScheduler(max_concurrent_tasks=10)
        self._sync_interval_minutes = int(os.getenv("CRM_SYNC_INTERVAL_MINUTES", "60"))
        self._batch_size = int(os.getenv("CRM_SYNC_BATCH_SIZE", "100"))
        self._max_tenants_per_batch = int(os.getenv("CRM_SYNC_MAX_TENANTS_PER_BATCH", "100"))
        self._running = False
        self._scheduled_task_ids: list[str] = []

    async def start(self) -> None:
        """Start the CRM sync scheduler.

        Schedules a periodic sweep task that discovers enabled integrations
        per-tenant and enqueues individual sync jobs with proper tenant context.
        """
        if self._running:
            logger.warning("CRMSyncScheduler already running")
            return

        await self._scheduler.start()
        self._running = True

        # Schedule periodic tenant sweep (single task that fans out to tenant-specific syncs)
        await self._schedule_tenant_sweep()

        logger.info(
            "CRM sync scheduler started: interval=%smin, batch_size=%s, max_tenants=%s",
            self._sync_interval_minutes,
            self._batch_size,
            self._max_tenants_per_batch,
        )

    async def stop(self) -> None:
        """Stop the CRM sync scheduler.

        Cancels pending sync tasks and stops the underlying scheduler.
        """
        if not self._running:
            return

        self._running = False

        # Cancel all scheduled sync tasks
        for task_id in self._scheduled_task_ids:
            try:
                await self._scheduler.cancel_task(task_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Failed to cancel sync task %s: %s", task_id, e)

        self._scheduled_task_ids.clear()
        await self._scheduler.stop()

        logger.info("CRM sync scheduler stopped")

    async def _schedule_tenant_sweep(self) -> None:
        """Schedule the next tenant sweep task."""
        if not self._running:
            return

        next_run = datetime.now(UTC) + timedelta(minutes=self._sync_interval_minutes)
        task_id = f"crm_tenant_sweep_{next_run.isoformat()}"

        task = ScheduledTask(
            priority=TaskPriority.BACKGROUND.value,
            scheduled_time=next_run,
            task_id=task_id,
            workflow_instance_id="crm_background_sync",
            capability="crm_sync",
            agent_type="CRMSyncScheduler",
            context={"sweep": True},
            parameters={"sweep": True},
            timeout_seconds=3600,  # 1 hour timeout for full sweep
        )

        scheduled_id = await self._scheduler.schedule_task(task)
        self._scheduled_task_ids.append(scheduled_id)

        logger.debug("Scheduled tenant sweep for %s", next_run.isoformat())

    async def _execute_tenant_sweep(self) -> dict[str, Any]:
        """Execute a sweep across all tenants with enabled CRM integrations.

        Returns:
            Sweep statistics: tenants_checked, syncs_triggered, errors
        """
        stats = {
            "tenants_checked": 0,
            "syncs_triggered": 0,
            "errors": [],
        }

        factory = get_session_factory()
        async with factory() as admin_db:
            # SECURITY: This query runs with admin context to enumerate tenants.
            # The actual syncs use per-tenant sessions with RLS.
            # Use a raw connection without tenant filter to find all integrations.
            await _clear_local_tenant_context(admin_db)

            try:
                result = await admin_db.execute(
                    select(Integration.tenant_id, Integration.provider)
                    .where(Integration.enabled == True)  # noqa: E712
                    .distinct()
                    .limit(self._max_tenants_per_batch)
                )
                tenant_providers = result.all()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Failed to enumerate tenant integrations: %s", e)
                stats["errors"].append(f"enumeration_failed: {e}")
                return stats

        for row in tenant_providers:
            tenant_id = row.tenant_id
            provider_str = row.provider

            stats["tenants_checked"] += 1

            try:
                provider = CRMProvider(provider_str)
            except ValueError:
                logger.warning(
                    "Skipping invalid provider '%s' for tenant %s", provider_str, tenant_id
                )
                stats["errors"].append(f"invalid_provider:{tenant_id}:{provider_str}")
                continue

            try:
                await self._execute_sync_for_tenant(tenant_id, provider)
                stats["syncs_triggered"] += 1
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(
                    "Sync failed for tenant=%s provider=%s: %s", tenant_id, provider_str, e
                )
                stats["errors"].append(f"sync_failed:{tenant_id}:{provider_str}:{type(e).__name__}")

        # Schedule next sweep
        await self._schedule_tenant_sweep()

        logger.info(
            "Tenant sweep complete: checked=%s, triggered=%s, errors=%s",
            stats["tenants_checked"],
            stats["syncs_triggered"],
            len(stats["errors"]),
        )

        return stats

    async def _execute_sync_for_tenant(
        self, tenant_id: str, provider: CRMProvider
    ) -> dict[str, Any]:
        """Execute CRM sync for a single tenant with proper tenant context.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider type

        Returns:
            Sync statistics
        """
        # Build a RequestContext for this tenant
        context = RequestContext(tenant_id=tenant_id)

        async with db_session_for_context(context) as db:
            integration_service = IntegrationService(db)
            integration = await integration_service.get_integration(tenant_id, provider)

            if not integration:
                logger.debug("No integration for tenant=%s provider=%s", tenant_id, provider.value)
                return {"skipped": True, "reason": "not_configured"}

            if not integration.enabled:
                logger.debug(
                    "Integration disabled for tenant=%s provider=%s", tenant_id, provider.value
                )
                return {"skipped": True, "reason": "disabled"}

            # Update sync status through the reducer.
            await apply_observation(db, integration, sync_started())
            await db.commit()

            try:
                sync_service = CRMSyncService(db, batch_size=self._batch_size)
                stats = await sync_service.sync_provider(provider, tenant_id=tenant_id)

                integration.records_synced = stats.get("synced", 0) + stats.get("updated", 0)
                integration.records_updated = stats.get("updated", 0)
                integration.records_failed = stats.get("failed", 0)
                integration.last_sync_at = datetime.now(UTC)

                if stats.get("failed", 0) > 0:
                    await apply_observation(db, integration, sync_partial())
                    integration.last_error_message = (
                        "; ".join(stats.get("errors", [])[:3]) or "Sync failed"
                    )
                else:
                    await apply_observation(db, integration, sync_succeeded())
                    integration.last_successful_sync_at = datetime.now(UTC)
                    integration.last_error_message = None

                await db.commit()
                return stats

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception(
                    "Background CRM sync failed: tenant=%s provider=%s",
                    tenant_id,
                    provider.value,
                )
                await apply_observation(db, integration, sync_interrupted(message=str(exc)))
                integration.last_sync_at = datetime.now(UTC)
                integration.last_error_message = f"{type(exc).__name__}: sync_failed"
                await db.commit()
                raise

    async def _execute_sync(self, provider_str: str, incremental: bool = True) -> dict[str, Any]:
        """DEPRECATED: Execute sync without tenant context.

        This method is kept for backward compatibility but should not be used.
        Use _execute_sync_for_tenant instead.
        """
        logger.warning("_execute_sync called without tenant_id — use _execute_sync_for_tenant")
        try:
            _provider = CRMProvider(provider_str)
        except ValueError:
            logger.error("Invalid CRM provider: %s", provider_str)
            return CRMSyncScheduler__execute_syncResult.model_validate(
                {"error": f"Invalid provider: {provider_str}"}
            )

        return CRMSyncScheduler__execute_syncResult.model_validate(
            {"skipped": True, "reason": "deprecated_path"}
        )

    async def trigger_sync_now(
        self,
        tenant_id: str | None = None,
        provider: CRMProvider | None = None,
        incremental: bool = True,
    ) -> dict[str, Any]:
        """Manually trigger a sync immediately.

        Args:
            tenant_id: Specific tenant to sync, or None for all tenants
            provider: Specific provider to sync, or None for all providers
            incremental: If True, only sync recently modified records

        Returns:
            Sync statistics
        """
        if tenant_id and provider:
            return await self._execute_sync_for_tenant(tenant_id, provider)

        # Sweep all tenants
        return await self._execute_tenant_sweep()

    def get_status(self) -> dict[str, Any]:
        """Get scheduler status and statistics.

        Returns:
            Status dict with configuration and scheduler stats
        """
        return CRMSyncScheduler_get_statusResult.model_validate(
            {
                "running": self._running,
                "sync_interval_minutes": self._sync_interval_minutes,
                "batch_size": self._batch_size,
                "scheduled_tasks": len(self._scheduled_task_ids),
                "scheduler_stats": self._scheduler.get_stats(),
            }
        )


# Global scheduler instance for singleton access
_crm_sync_scheduler: CRMSyncScheduler | None = None


async def get_crm_sync_scheduler() -> CRMSyncScheduler:
    """Get or create the global CRM sync scheduler instance.

    Returns:
        CRMSyncScheduler singleton
    """
    global _crm_sync_scheduler
    if _crm_sync_scheduler is None:
        _crm_sync_scheduler = CRMSyncScheduler()
    return _crm_sync_scheduler
