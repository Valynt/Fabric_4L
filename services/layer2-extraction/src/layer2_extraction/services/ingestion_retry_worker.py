"""Ingestion retry worker and background processor for Layer 2 extraction pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from layer2_extraction.domain.models import (
    ChallengeEntity,
    ExtractionResult,
    FinancialMetricEntity,
    GoalEntity,
    InitiativeEntity,
    KPIEntity,
    RelationshipEntity,
    SystemEntity,
)
from layer2_extraction.domain.validation import (
    validate_extraction_result,
    validate_relationship_for_persistence,
)
from layer2_extraction.generation.rdf_generator import generate_rdf
from layer2_extraction.integration.job_store import JobStore
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.pending_ingestion_store import PendingIngestionStore
from layer2_extraction.observability.websocket import WebSocketManager

logger = structlog.get_logger(__name__)

MAX_INGESTION_RETRIES: int = 5
RETRY_BASE_SECONDS: float = 2.0


async def queue_for_retry(
    *,
    pending_ingestion_store: PendingIngestionStore,
    job_store: JobStore,
    set_pipeline_job_fn: Callable[..., Awaitable[None]],
    serialize_artifacts_fn: Callable[[Any], dict[str, Any]],
    tenant_id: str,
    job_id: str,
    source_url: str,
    artifacts: Any,
    error_detail: str,
    retry_count: int = 0,
    retry_base_seconds: float = RETRY_BASE_SECONDS,
) -> None:
    """Queue an extraction result for deferred Layer 3 ingestion retry."""
    delay = retry_base_seconds * (2**retry_count)
    next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
    payload_json = serialize_artifacts_fn(artifacts)
    await pending_ingestion_store.enqueue(
        tenant_id=tenant_id,
        job_id=job_id,
        source_url=source_url,
        payload_json=payload_json,
        retry_count=retry_count,
        next_retry_at=next_retry_at,
        last_error=error_detail,
    )
    await set_pipeline_job_fn(
        job_id,
        ingestion_status="pending_retry",
        last_error=error_detail,
    )
    logger.info(
        "Ingestion queued for retry",
        tenant_id=tenant_id,
        job_id=job_id,
        retry_count=retry_count,
        next_retry_at=next_retry_at.isoformat(),
    )


async def attempt_ingestion(
    *,
    job_store: JobStore,
    pending_ingestion_store: PendingIngestionStore,
    ws_manager: WebSocketManager,
    l3_client: Layer3KnowledgeClient,
    set_pipeline_job_fn: Callable[..., Awaitable[None]],
    serialize_artifacts_fn: Callable[[Any], dict[str, Any]],
    tenant_id: str,
    job_id: str,
    source_url: str,
    artifacts: Any,
    retry_count: int = 0,
    retry_base_seconds: float = RETRY_BASE_SECONDS,
    max_retries: int = MAX_INGESTION_RETRIES,
) -> bool:
    """Attempt ingestion of extraction artifacts into Layer 3.

    Returns True if ingested immediately; False if queued for retry.
    """
    await set_pipeline_job_fn(job_id, ingestion_status="in_progress")
    await ws_manager.broadcast_progress(
        job_id,
        {
            "step": "ingesting",
            "progress": 0.85,
            "entities": len(artifacts.entities),
            "relationships": len(artifacts.relationships),
        },
    )

    try:
        entities = artifacts.entities
        relationships = artifacts.relationships

        # Validate extraction result
        ext_result = ExtractionResult(
            tenant_id=tenant_id,
            goals=[e for e in entities if isinstance(e, GoalEntity)],
            initiatives=[e for e in entities if isinstance(e, InitiativeEntity)],
            challenges=[e for e in entities if isinstance(e, ChallengeEntity)],
            kpis=[e for e in entities if isinstance(e, KPIEntity)],
            financial_metrics=[
                e for e in entities if isinstance(e, FinancialMetricEntity)
            ],
            systems=[e for e in entities if isinstance(e, SystemEntity)],
            relationships=relationships,
        )
        val_result = validate_extraction_result(ext_result)
        if not val_result.is_valid:
            logger.warning(
                "Extracted entities failed validation during ingestion attempt",
                tenant_id=tenant_id,
                job_id=job_id,
                errors=val_result.errors,
            )

        # Validate each relationship for persistence
        for rel in relationships:
            rel_val = validate_relationship_for_persistence(rel, entities)
            if not rel_val.is_valid:
                logger.warning(
                    "Relationship failed persistence validation",
                    tenant_id=tenant_id,
                    job_id=job_id,
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    rel_type=rel.relationship_type,
                    errors=rel_val.errors,
                )

        # Generate RDF triples
        rdf_triples = generate_rdf(entities, relationships, tenant_id=tenant_id)
        artifacts.rdf_triples = rdf_triples

        ingest_res = await l3_client.ingest_subgraph(
            tenant_id=tenant_id,
            entities=entities,
            relationships=relationships,
            rdf_triples=rdf_triples,
            source_url=source_url,
        )

        nodes_created = ingest_res.get("nodes_created", len(entities))
        edges_created = ingest_res.get("relationships_created", len(relationships))
        completed_at = datetime.now(UTC)

        await set_pipeline_job_fn(
            job_id,
            ingestion_status="completed",
            nodes_created=nodes_created,
            edges_created=edges_created,
            completed_at=completed_at,
        )

        await ws_manager.broadcast_progress(
            job_id,
            {
                "step": "completed",
                "progress": 1.0,
                "nodes_created": nodes_created,
                "edges_created": edges_created,
            },
        )
        logger.info(
            "Layer 3 ingestion succeeded",
            tenant_id=tenant_id,
            job_id=job_id,
            nodes_created=nodes_created,
            edges_created=edges_created,
        )
        return True

    except Exception as exc:
        err_msg = str(exc)
        logger.warning(
            "Layer 3 ingestion attempt failed",
            tenant_id=tenant_id,
            job_id=job_id,
            retry_count=retry_count,
            error=err_msg,
        )

        if retry_count < max_retries:
            await queue_for_retry(
                pending_ingestion_store=pending_ingestion_store,
                job_store=job_store,
                set_pipeline_job_fn=set_pipeline_job_fn,
                serialize_artifacts_fn=serialize_artifacts_fn,
                tenant_id=tenant_id,
                job_id=job_id,
                source_url=source_url,
                artifacts=artifacts,
                error_detail=err_msg,
                retry_count=retry_count,
                retry_base_seconds=retry_base_seconds,
            )
        else:
            completed_at = datetime.now(UTC)
            await set_pipeline_job_fn(
                job_id,
                ingestion_status="failed",
                last_error=f"Max retries exceeded ({max_retries}): {err_msg}",
                completed_at=completed_at,
            )
            logger.error(
                "Layer 3 ingestion exhausted all retries",
                tenant_id=tenant_id,
                job_id=job_id,
                error=err_msg,
            )

        return False


async def process_pending_ingestions(
    *,
    pending_ingestion_store: PendingIngestionStore,
    job_store: JobStore,
    l3_client: Layer3KnowledgeClient,
    attempt_ingestion_fn: Callable[..., Awaitable[bool]],
    deserialize_artifacts_fn: Callable[[dict[str, Any]], Any],
    set_pipeline_job_fn: Callable[..., Awaitable[None]],
    retry_base_seconds: float = RETRY_BASE_SECONDS,
    max_retries: int = MAX_INGESTION_RETRIES,
) -> int:
    """Scan and process pending ingestions that are due for retry.

    Returns the number of records processed.
    """
    due_items = await pending_ingestion_store.get_due_for_retry()
    processed = 0

    for item in due_items:
        processed += 1
        job_id = item["job_id"]
        tenant_id = item["tenant_id"]
        source_url = item["source_url"]
        retry_count = item["retry_count"]
        payload_json = item["payload_json"]

        # Atomic lock/claim
        acquired = await pending_ingestion_store.mark_in_flight(job_id)
        if not acquired:
            continue

        try:
            artifacts = deserialize_artifacts_fn(payload_json)
        except Exception as exc:
            logger.error(
                "Failed to deserialize artifacts for pending ingestion",
                job_id=job_id,
                error=str(exc),
            )
            await pending_ingestion_store.delete(job_id)
            await set_pipeline_job_fn(
                job_id,
                ingestion_status="failed",
                last_error=f"Artifact deserialization error: {exc}",
                completed_at=datetime.now(UTC),
            )
            continue

        success = await attempt_ingestion_fn(
            tenant_id=tenant_id,
            job_id=job_id,
            source_url=source_url,
            artifacts=artifacts,
            retry_count=retry_count + 1,
            retry_base_seconds=retry_base_seconds,
            max_retries=max_retries,
        )

        if success:
            await pending_ingestion_store.delete(job_id)

    return processed


async def pending_ingestion_retry_loop(
    *,
    pending_ingestion_store: PendingIngestionStore,
    process_fn: Callable[[], Awaitable[int]],
    retry_poll_seconds: float = 5.0,
) -> None:
    """Background task continuously draining due pending ingestions."""
    logger.info(
        "Starting background pending ingestion retry loop",
        poll_interval=retry_poll_seconds,
    )
    while True:
        try:
            await process_fn()
        except asyncio.CancelledError:
            logger.info("Pending ingestion retry loop cancelled")
            break
        except Exception as exc:
            logger.exception("Error in pending ingestion retry loop", error=str(exc))

        try:
            await asyncio.sleep(retry_poll_seconds)
        except asyncio.CancelledError:
            break
