"""Celery task queue configuration and tasks for Layer 2 Extraction.

Provides async task processing for entity and relationship extraction,
enabling scalable queue-based processing instead of synchronous HTTP calls.
"""

import logging
import os

from celery import Celery
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.redis_ha import get_celery_redis_broker_config


def _require_task_tenant_id(config: dict) -> str:
    """Require verified tenant context on a queued task payload; fail closed.

    Raises ValueError (non-retryable) when the payload carries no usable
    tenant_id, so tenantless or blank-tenant jobs never reach processing.
    """
    tenant_id = (config or {}).get("tenant_id")
    if tenant_id is None or not str(tenant_id).strip():
        raise ValueError("tenant_id is required in config for extraction task")
    return str(tenant_id).strip()

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_broker_url, celery_transport_options = get_celery_redis_broker_config(redis_url)

# Initialize Celery app
celery_app = Celery(
    "layer2_extraction",
    broker=celery_broker_url,
    backend=celery_broker_url,
    include=["layer2_extraction.shared.tasks"],
)

# Celery configuration - matches L1 patterns for consistency
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
    # Dead letter queue configuration
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_default_rate_limit="100/m",
    # Define dead letter queue
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "layer2_dlq": {
            "exchange": "layer2_dlq",
            "routing_key": "layer2_dlq",
        },
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    broker_transport_options=celery_transport_options,
    result_backend_transport_options=celery_transport_options,
    # Backpressure configuration
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=500000,
    # Graceful shutdown configuration
    worker_shutdown_timeout=30,
    worker_cancel_long_running_tasks_on_shutdown=True,
)

logger = logging.getLogger(__name__)

# Re-export at module level so tests can patch them via layer2_extraction.shared.tasks


# =============================================================================
# EXTRACTION TASKS
# =============================================================================


@celery_app.task(bind=True, max_retries=3)
async def run_extraction_task(self, job_id: str, source_url: str, content: str, config: dict, mark_pipeline_complete: bool = True):
    """Execute full extraction pipeline via Celery task.

    Wraps the async run_extraction function for Celery compatibility.
    This task is dispatched by L1 when processing raw content.

    Args:
        job_id: Unique job identifier
        source_url: Source URL of the content
        content: Raw content to extract from
        config: Extraction configuration dict (must include tenant_id)
        mark_pipeline_complete: Whether to mark pipeline as complete

    Returns:
        dict with success status and job_id
    """
    logger.info("Starting extraction task", extra={"job_id": job_id, "source_url": source_url})

    # Validate tenant_id in config (fail closed, non-retryable)
    _require_task_tenant_id(config)

    try:
        # Import here to avoid circular dependencies
        from layer2_extraction.api.main import run_extraction

        await run_extraction(
            job_id=job_id,
            source_url=source_url,
            content=content,
            config=config,
            mark_pipeline_complete=mark_pipeline_complete,
        )

        logger.info("Extraction task completed", extra={"job_id": job_id})
        return {
            "success": True,
            "job_id": job_id,
        }

    except AuthorizationError:
        # Tenant-context failures (e.g. tenant_context_mismatch from a forged
        # or stale payload) are terminal: fail closed without retrying.
        logger.error(
            "Extraction task rejected: tenant context failure",
            extra={"job_id": job_id},
        )
        raise
    except Exception as exc:
        logger.error("Extraction task failed", extra={"job_id": job_id, "error": str(exc)})
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
async def extract_entities_task(self, job_id: str, content: str, config: dict):
    """Extract entities from content via Celery task.

    Args:
        job_id: Unique job identifier
        content: Raw content to extract from
        config: Extraction configuration dict

    Returns:
        dict with extracted entities and metadata
    """
    logger.info("Starting entity extraction task", extra={"job_id": job_id})

    # Fail closed on missing tenant context (non-retryable)
    _require_task_tenant_id(config)

    try:
        # Import here to avoid circular dependencies
        from layer2_extraction.extraction.chunker import chunk_markdown
        from layer2_extraction.extraction.llm_extractor import EntityExtractor

        # Chunk content
        chunks = chunk_markdown(content, source_url=config.get("source_url", ""), chunk_size=2000, chunk_overlap=200)

        # Extract entities from chunks
        extractor = EntityExtractor()
        all_entities = []

        for chunk in chunks:
            entities = await extractor.extract_entities(chunk, config.get("extraction_schema"))
            all_entities.extend(entities)

        logger.info("Entity extraction task completed", extra={"job_id": job_id, "entity_count": len(all_entities)})
        return {
            "success": True,
            "job_id": job_id,
            "entities": all_entities,
            "entity_count": len(all_entities),
        }

    except Exception as exc:
        logger.error("Entity extraction task failed", extra={"job_id": job_id, "error": str(exc)})
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
async def extract_relationships_task(self, job_id: str, entities: list, config: dict):
    """Extract relationships between entities via Celery task.

    Args:
        job_id: Unique job identifier
        entities: List of extracted entities
        config: Extraction configuration dict

    Returns:
        dict with extracted relationships and metadata
    """
    logger.info("Starting relationship extraction task", extra={"job_id": job_id})

    # Fail closed on missing tenant context (non-retryable)
    _require_task_tenant_id(config)

    try:
        # Import here to avoid circular dependencies
        from layer2_extraction.extraction.llm_extractor import RelationshipExtractor

        # Extract relationships
        extractor = RelationshipExtractor()
        relationships = await extractor.extract_relationships(entities, config.get("extraction_schema"))

        logger.info("Relationship extraction task completed", extra={"job_id": job_id, "relationship_count": len(relationships)})
        return {
            "success": True,
            "job_id": job_id,
            "relationships": relationships,
            "relationship_count": len(relationships),
        }

    except Exception as exc:
        logger.error("Relationship extraction task failed", extra={"job_id": job_id, "error": str(exc)})
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
