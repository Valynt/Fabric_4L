"""Celery app bootstrap for the Layer 1 task package.

The tasks package used to be a single monolith where ``celery_app``, ``logger``
and the shared bootstrap lived alongside every task. After the R1 split into
``tasks/*.py`` submodules, importing these globals back from the package
``__init__`` creates a circular import (``__init__`` re-exports submodule tasks
at its tail, submodules import ``celery_app`` at module scope for decorators),
which breaks mypy resolution and risks import-time surprises.

This leaf module owns the immutable bootstrap state.  Submodules and the
package ``__init__`` both import ``celery_app`` and ``logger`` from here so
there is exactly one definition site and no cycle.
"""

import structlog
from celery import Celery
from celery.schedules import crontab

from value_fabric.shared.redis_ha import get_celery_redis_broker_config

from ..config import settings

logger = structlog.get_logger()

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