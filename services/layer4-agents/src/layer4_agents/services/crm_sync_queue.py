from __future__ import annotations

"""Lightweight CRM sync job queue module.

This module exists to break the static import cycle between
``crm_sync_service``, ``integration_service``, and ``crm_sync_job_runner``.
It intentionally does NOT import any of those service modules at module scope.
"""


import json
import logging
import os

import redis.asyncio as redis
from value_fabric.shared.redis_ha import create_async_redis_client

logger = logging.getLogger(__name__)

CRM_SYNC_QUEUE_KEY = "layer4:crm_sync_jobs"


async def enqueue_crm_sync_job(
    *,
    redis_client: redis.Redis | None,
    job_id: str,
    tenant_id: str,
    provider: str,
) -> None:
    """Enqueue a CRM sync job on the Redis-backed queue.

    Args:
        redis_client: Optional existing Redis client. If None, a short-lived
            client is created from ``REDIS_URL``.
        job_id: UUID of the persisted ``CRMSyncJob``.
        tenant_id: Tenant that owns the job.
        provider: CRM provider value (e.g. ``salesforce`` or ``hubspot``).

    Raises:
        RuntimeError: If no ``redis_client`` is provided and ``REDIS_URL`` is not set.
    """
    payload = json.dumps(
        {"job_id": job_id, "tenant_id": tenant_id, "provider": provider},
        separators=(",", ":"),
    )
    if redis_client is not None:
        await redis_client.lpush(CRM_SYNC_QUEUE_KEY, payload)  # type: ignore[misc]
        return

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL must be configured for CRM sync job queueing")
    temp_client = create_async_redis_client(redis_url, decode_responses=True)
    try:
        await temp_client.lpush(CRM_SYNC_QUEUE_KEY, payload)
    finally:
        await temp_client.aclose()
