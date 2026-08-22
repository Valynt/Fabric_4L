"""Ingestion runner and retry queue management for Layer 2 extraction service.

Handles dispatching extracted artifacts to Layer 3 Knowledge service, tracking retry
attempts, rescheduling failed ingestion jobs, and background retry loops.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from datetime import UTC, datetime
from typing import Any, cast

import structlog

from layer2_extraction.api.pipeline_status import (
    pipeline_response_payload,
)
from layer2_extraction.api.retry_queue import (
    ExtractionArtifactsPayload,
    deserialize_artifacts,
    next_retry_at,
    pending_retry_state,
    pipeline_job_kwargs_for_pending_record,
    serialize_artifacts,
)
from layer2_extraction.api.schemas import ExtractionStatusResponse
from layer2_extraction.api.websocket import get_pipeline_ws_manager
from layer2_extraction.integration.job_store import JobStore, PipelineJob, build_job_store
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.pending_ingestion_store import (
    PendingIngestionRecord,
    PendingIngestionStore,
    build_pending_ingestion_store,
)
from layer2_extraction.output.rdf_generator import generate_rdf
from layer2_extraction.validation.artifact_validator import (
    validate_extraction_result,
    validate_relationship_for_persistence,
)

logger = structlog.get_logger(__name__)

RETRY_POLL_SECONDS = int(os.getenv("INGESTION_RETRY_POLL_SECONDS", "30"))
RETRY_BASE_SECONDS = int(os.getenv("INGESTION_RETRY_BASE_SECONDS", "60"))
MAX_INGESTION_RETRIES = int(os.getenv("INGESTION_MAX_RETRIES", "5"))
_pending_ingestion_retry_task: asyncio.Task | None = None
_UNSET = object()


def _get_active_job_store() -> JobStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "job_store"):
        return main_mod.job_store
    return build_job_store()


def _get_active_pending_ingestion_store() -> PendingIngestionStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "pending_ingestion_store"):
        return main_mod.pending_ingestion_store
    return build_pending_ingestion_store()


def _get_active_ws_manager():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "_ws_manager"):
        return main_mod._ws_manager
    return get_pipeline_ws_manager()


def _get_active_layer3_client_class():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "Layer3KnowledgeClient"):
        return main_mod.Layer3KnowledgeClient
    return Layer3KnowledgeClient


def _get_active_datetime():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "datetime"):
        return main_mod.datetime
    return datetime


def _pipeline_response(job: PipelineJob) -> ExtractionStatusResponse:
    return ExtractionStatusResponse(**pipeline_response_payload(job))


def _serialize_artifacts(artifacts: Any) -> tuple[str, str]:
    return serialize_artifacts(
        ExtractionArtifactsPayload(
            result=artifacts.result,
            relationships=artifacts.relationships,
        )
    )


def _deserialize_artifacts(result_json: str, relationships_json: str) -> Any:
    artifacts = deserialize_artifacts(result_json, relationships_json)
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "ExtractionArtifacts"):
        artifacts_cls = main_mod.ExtractionArtifacts
    else:
        from layer2_extraction.api.pipeline_runner import ExtractionArtifacts

        artifacts_cls = ExtractionArtifacts
    return artifacts_cls(result=artifacts.result, relationships=artifacts.relationships)


async def _set_pipeline_job(
    job_id: str,
    extraction_status: str | None = None,
    ingestion_status: str | None = None,
    entities_extracted: int | None = None,
    relationships_extracted: int | None = None,
    retry_count: int | None = None,
    last_error: object = _UNSET,
    next_retry_at: object = _UNSET,
    completed_at: datetime | None = None,
) -> None:
    job_store = _get_active_job_store()
    job = await job_store.get(job_id)
    if not job:
        return
    if extraction_status is not None:
        job.extraction_status = extraction_status
    if ingestion_status is not None:
        job.ingestion_status = ingestion_status
    if entities_extracted is not None:
        job.entities_extracted = entities_extracted
    if relationships_extracted is not None:
        job.relationships_extracted = relationships_extracted
    if retry_count is not None:
        job.retry_count = retry_count
    if last_error is not _UNSET:
        job.last_error = cast(str | None, last_error)
    if next_retry_at is not _UNSET:
        job.next_retry_at = cast(datetime | None, next_retry_at)
    if completed_at is not None:
        job.completed_at = completed_at.isoformat() if completed_at else None
    # Persist to job store
    await job_store.set(job)


async def _queue_for_retry(
    job_id: str,
    source_url: str,
    artifacts: Any,
    last_error: str,
    retry_count: int,
) -> None:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "_queue_for_retry")
        and main_mod._queue_for_retry is not _queue_for_retry
    ):
        return await main_mod._queue_for_retry(
            job_id, source_url, artifacts, last_error, retry_count
        )

    dt_cls = _get_active_datetime()
    pending_store = _get_active_pending_ingestion_store()

    next_retry_dt = next_retry_at(
        now=dt_cls.now(UTC),
        retry_base_seconds=RETRY_BASE_SECONDS,
        retry_count=retry_count,
        fromtimestamp=dt_cls.fromtimestamp,
    )
    result_json, relationships_json = _serialize_artifacts(artifacts)

    await pending_store.enqueue(
        job_id=job_id,
        source_url=source_url,
        extraction_result_json=result_json,
        relationships_json=relationships_json,
        retry_count=retry_count,
        next_retry_at=next_retry_dt,
        max_retries=MAX_INGESTION_RETRIES,
        last_error=last_error,
    )

    await _set_pipeline_job(
        job_id,
        ingestion_status="queued",
        retry_count=retry_count,
        last_error=last_error,
        next_retry_at=next_retry_dt,
    )


async def _attempt_ingestion(job_id: str, source_url: str, artifacts: Any) -> bool:
    job_store = _get_active_job_store()
    pending_store = _get_active_pending_ingestion_store()
    ws_mgr = _get_active_ws_manager()
    client_cls = _get_active_layer3_client_class()
    dt_cls = _get_active_datetime()

    client = client_cls()
    try:
        job = await job_store.get(job_id)
        current_retry = job.retry_count if job else 0
        await _set_pipeline_job(job_id, ingestion_status="running", next_retry_at=None)

        # Broadcast ingestion start
        await ws_mgr.broadcast_ingestion_status(
            job_id=job_id,
            status="running",
            retry_count=current_retry,
            max_retries=MAX_INGESTION_RETRIES,
        )

        # P1-3: MANDATORY VALIDATION GATE before L3 ingestion
        validate_extraction_result(artifacts.result)
        for rel in artifacts.relationships:
            validate_relationship_for_persistence(rel)

        # Layer 2 owns RDF generation; the L3 client only speaks the L3 HTTP contract.
        rdf_data = generate_rdf(artifacts.result, artifacts.relationships)
        response = await client.ingest_rdf_data(
            rdf_data=rdf_data,
            source_url=source_url,
            extraction_job_id=job_id,
            tenant_id=artifacts.result.tenant_id,
            content_hash=hashlib.sha256(source_url.encode()).hexdigest(),
            prompt_template_version=artifacts.result.prompt_template_version,
            prompt_template_hash=artifacts.result.prompt_template_hash,
        )
        if response.success:
            await _set_pipeline_job(
                job_id,
                ingestion_status="completed",
                last_error=None,
                next_retry_at=None,
                completed_at=dt_cls.now(UTC),
            )

            # Get updated job for retry count
            updated_job = await job_store.get(job_id)
            final_retry = updated_job.retry_count if updated_job else 0

            # Broadcast ingestion success
            await ws_mgr.broadcast_ingestion_status(
                job_id=job_id,
                status="completed",
                retry_count=final_retry,
                max_retries=MAX_INGESTION_RETRIES,
                entities_loaded=response.entities_loaded,
                relationships_loaded=response.relationships_loaded,
            )

            # Broadcast overall pipeline completion
            job = await job_store.get(job_id)
            if job is None:
                return True
            await ws_mgr.broadcast_pipeline_complete(
                job_id=job_id,
                status="completed",
                entities_extracted=job.entities_extracted,
                relationships_extracted=job.relationships_extracted,
                entities_loaded=response.entities_loaded,
                relationships_loaded=response.relationships_loaded,
            )

            await pending_store.complete(job_id)
            return True

        job = await job_store.get(job_id)
        retry_count = (job.retry_count + 1) if job else 1

        # Broadcast ingestion failure with retry
        await ws_mgr.broadcast_ingestion_status(
            job_id=job_id,
            status="retrying" if retry_count <= MAX_INGESTION_RETRIES else "failed",
            retry_count=retry_count,
            max_retries=MAX_INGESTION_RETRIES,
            error=response.error or response.message,
        )

        await _queue_for_retry(
            job_id=job_id,
            source_url=source_url,
            artifacts=artifacts,
            last_error=response.error or response.message,
            retry_count=retry_count,
        )
        return False
    finally:
        await client.close()


async def _process_pending_ingestions() -> None:
    job_store = _get_active_job_store()
    pending_store = _get_active_pending_ingestion_store()
    client_cls = _get_active_layer3_client_class()
    dt_cls = _get_active_datetime()

    now = dt_cls.now(UTC)
    records: list[PendingIngestionRecord] = await pending_store.get_due(now)
    for record in records:
        if not await job_store.exists(record.job_id):
            await job_store.set(
                PipelineJob(
                    **pipeline_job_kwargs_for_pending_record(
                        record,
                        created_at=dt_cls.now(UTC),
                    )
                )
            )

        artifacts = _deserialize_artifacts(record.extraction_result_json, record.relationships_json)
        client = client_cls()
        try:
            healthy = await client.health_check()
        finally:
            await client.close()

        if not healthy:
            retry_count = record.retry_count + 1
            if retry_count >= record.max_retries:
                await pending_store.complete(record.job_id)
                await _set_pipeline_job(
                    record.job_id,
                    ingestion_status="failed",
                    retry_count=retry_count,
                    last_error="Layer 3 unavailable after max retries",
                    next_retry_at=None,
                    completed_at=dt_cls.now(UTC),
                )
            else:
                retry_state = pending_retry_state(
                    now=dt_cls.now(UTC),
                    current_retry_count=record.retry_count,
                    retry_base_seconds=RETRY_BASE_SECONDS,
                    fromtimestamp=dt_cls.fromtimestamp,
                )
                await pending_store.reschedule(
                    job_id=record.job_id,
                    retry_count=retry_state.retry_count,
                    last_error=retry_state.last_error,
                    next_retry_at=retry_state.next_retry_at,
                )
                await _set_pipeline_job(
                    record.job_id,
                    ingestion_status="queued",
                    retry_count=retry_state.retry_count,
                    last_error=retry_state.last_error,
                    next_retry_at=retry_state.next_retry_at,
                )
            continue

        success = await _attempt_ingestion(record.job_id, record.source_url, artifacts)
        if not success:
            metadata = await pending_store.get_retry_metadata(record.job_id)
            if metadata:
                job = await job_store.get(record.job_id)
                current_retry = job.retry_count if job else 0
                await _set_pipeline_job(
                    record.job_id,
                    retry_count=metadata.get("retry_count", current_retry),
                    last_error=metadata.get("last_error"),
                    next_retry_at=(
                        dt_cls.fromisoformat(metadata["next_retry_at"])
                        if metadata.get("next_retry_at")
                        else None
                    ),
                )


async def _pending_ingestion_retry_loop() -> None:
    while True:
        try:
            await _process_pending_ingestions()
        except Exception as exc:
            logger.exception("Pending ingestion retry loop error: %s", exc)
        await asyncio.sleep(RETRY_POLL_SECONDS)
