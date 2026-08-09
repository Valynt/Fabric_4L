"""Celery task queue configuration and tasks.

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

import asyncio
import os
from urllib.parse import urlparse

import httpx
import structlog

# Compatibility exports: callers and tests historically patch dependencies on
# this module. Implementations resolve these names through this facade.
from celery import (
    Celery,
    chain,  # noqa: F401
)
from celery.schedules import crontab

from ..compliance.robots_checker import RobotsChecker  # noqa: F401
from ..compliance.url_safety import validate_url_safety  # noqa: F401
from ..crawler.decision_store import CrawlDecisionRepository  # noqa: F401
from ..crawler.playwright_crawler import PlaywrightCrawler  # noqa: F401
from ..crawler.quality_gate import QualityGate  # noqa: F401
from ..crawler.smart_router import SmartRouter  # noqa: F401
from ..metrics.prometheus_metrics import get_metrics  # noqa: F401
from ..shared.database import get_db_session  # noqa: F401
from ..shared.maintenance import (  # noqa: F401
    authorize_maintenance_operation,
    maintenance_audit_log,
)
from ..shared.models import JobStageDetail, ScrapingJob, ScrapingTarget  # noqa: F401
from ..skills import get_skill  # noqa: F401

try:
    from value_fabric.shared.identity.jwt import encode_service_jwt  # noqa: F401
except ImportError:
    encode_service_jwt = None  # type: ignore

from value_fabric.shared.redis_ha import get_celery_redis_broker_config

from ..shared.config import settings

# Maximum delivery attempts before an outbox event is dead-lettered.
MAX_DISPATCH_ATTEMPTS = 5


def _domain_class(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return "unknown"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "regulated"
    if host.endswith(".internal") or host.endswith(".local"):
        return "internal"
    return "public"


logger = structlog.get_logger()


async def _verify_l3_graph_population(tenant_id: str, source_version_id: str) -> int:
    """Verify L3 graph has entities from the given source version.

    Calls L3 /v1/query/entities with source_version_id filter and returns count.
    """

    from ..shared.config import settings

    l3_url = settings.layer3_api_url
    service_secret = os.getenv("SERVICE_AUTH_SECRET", "")

    headers = {
        "X-Tenant-ID": tenant_id,
        "X-Service-Auth": service_secret,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{l3_url}/v1/query/entities",
                params={"source_version_id": source_version_id, "limit": 1},
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("total", 0)
    except Exception as e:
        logger.warning(
            "L3 graph verification failed",
            tenant_id=tenant_id,
            source_version_id=source_version_id,
            error=str(e),
        )
    return 0


def _run_async(coro):
    # In a Celery worker there is no running event loop, so run the coroutine
    # to completion. When called from an async test context (e.g. pytest-asyncio)
    # with a running loop, return the coroutine so the caller can await it.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return coro


_celery_broker_url, _celery_transport_options = get_celery_redis_broker_config(settings.redis_url)

# Initialize Celery app
celery_app = Celery(
    "layer1_ingestion",
    broker=_celery_broker_url,
    backend=_celery_broker_url,
    include=["layer1_ingestion.shared.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={},
    # P0-02: Dead letter queue configuration
    task_reject_on_worker_lost=True,  # Reject tasks when worker dies
    task_acks_late=True,  # Ack after task completes
    task_default_retry_delay=60,  # Default retry delay in seconds
    task_max_retries=3,  # Max retries before sending to DLQ
    task_default_rate_limit="100/m",  # Rate limit per task
    # Define dead letter queue
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "ingestion": {
            "exchange": "ingestion",
            "routing_key": "ingestion",
        },
        "processing": {
            "exchange": "processing",
            "routing_key": "processing",
        },
        "layer1_dlq": {
            "exchange": "layer1_dlq",
            "routing_key": "layer1_dlq",
        },
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    broker_transport_options=_celery_transport_options,
    result_backend_transport_options=_celery_transport_options,
    # P0-03: Backpressure configuration
    worker_max_tasks_per_child=100,  # Recycle worker after 100 tasks
    worker_max_memory_per_child=500000,  # 500MB max memory per worker
    # P0-06: Graceful shutdown configuration
    worker_shutdown_timeout=30,  # 30s grace period for in-progress tasks
    worker_cancel_long_running_tasks_on_shutdown=True,
    # Data retention: purge expired raw content daily at 03:00 UTC.
    beat_schedule={
        "purge-expired-raw-content": {
            "task": "layer1_ingestion.shared.tasks.purge_expired_raw_content",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "default"},
        },
    },
)


# =============================================================================
# PIPELINE ORCHESTRATION
# =============================================================================


# Import task modules after ``celery_app`` is configured. These re-exports retain
# the historical ``layer1_ingestion.shared.tasks`` import surface while keeping
# task implementations grouped by responsibility.
from .crawl_maintenance_tasks import *  # noqa: E402,F403
from .delivery_tasks import *  # noqa: E402,F403
from .pipeline_tasks import *  # noqa: E402,F403
