"""Extraction API routes for Layer 2.

Handles entity & relationship extraction, combined extraction+ingestion,
batch extraction, status queries, quarantine records, ontology entities,
provenance tracking, and SSE event streaming.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
)
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer2_extraction.api.deps import RequestContext, require_authenticated
from layer2_extraction.api.extraction_config import (
    build_idempotency_key as _build_idempotency_key,
)
from layer2_extraction.api.extraction_config import (
    validated_extraction_config as _validated_extraction_config,
)
from layer2_extraction.api.pipeline_status import pipeline_response_payload
from layer2_extraction.api.schemas import (
    EntityListResponse,
    ExtractAndIngestResponse,
    ExtractionStatusResponse,
    ExtractRequest,
    ExtractResponse,
    ProvenanceResponse,
    QuarantineStatusResponse,
    RelationshipsResponse,
)
from layer2_extraction.api.sse_stream import _job_event_generator
from layer2_extraction.integration.job_store import JobStore, PipelineJob, build_job_store
from layer2_extraction.integration.quarantine_store import (
    QuarantineStore,
    build_quarantine_store,
)
from layer2_extraction.output.provenance import get_provenance_tracker

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["extraction"])


class extract_batchResult(TypedDictModel):
    batch_job_id: str
    job_ids: list[str]
    status: str
    total_jobs: int


def _get_active_job_store() -> JobStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "job_store"):
        return main_mod.job_store
    return build_job_store()


def _get_active_quarantine_store() -> QuarantineStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "quarantine_store"):
        return main_mod.quarantine_store
    return build_quarantine_store()


def _get_active_datetime():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "datetime"):
        return main_mod.datetime
    return datetime


def _get_run_extraction_fn():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "run_extraction"):
        return main_mod.run_extraction
    from layer2_extraction.api.pipeline_runner import run_extraction

    return run_extraction


def _get_run_extract_and_ingest_fn():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "run_extract_and_ingest"):
        return main_mod.run_extract_and_ingest
    from layer2_extraction.api.pipeline_runner import run_extract_and_ingest

    return run_extract_and_ingest


def _pipeline_response(job: PipelineJob) -> ExtractionStatusResponse:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "_pipeline_response")
        and main_mod._pipeline_response is not _pipeline_response
    ):
        return main_mod._pipeline_response(job)
    return ExtractionStatusResponse(**pipeline_response_payload(job))


def _require_authenticated_tenant_id(tenant_id: Any, *, operation: str) -> str:
    """Require authenticated tenant context and fail closed when missing."""
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "_require_authenticated_tenant_id")
        and main_mod._require_authenticated_tenant_id is not _require_authenticated_tenant_id
    ):
        return main_mod._require_authenticated_tenant_id(tenant_id, operation=operation)

    if tenant_id is None:
        raise AuthorizationError(
            message="Request failed",
            details={
                "code": "tenant_context_required",
                "message": f"Authenticated tenant context is required for {operation}.",
            },
        )
    normalized = str(tenant_id).strip()
    if not normalized:
        raise AuthorizationError(
            message="Request failed",
            details={
                "code": "tenant_context_required",
                "message": f"Authenticated tenant context is required for {operation}.",
            },
        )
    return normalized


@router.post("/v1/extract", response_model=ExtractResponse)
async def extract(
    request: ExtractRequest,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Start an extraction job.

    Extracts entities and relationships from provided Markdown content
    and generates RDF/OWL output.
    """
    tenant_id = _require_authenticated_tenant_id(ctx.tenant_id, operation="extraction job creation")

    job_id = str(uuid4())
    job_store = _get_active_job_store()
    dt_cls = _get_active_datetime()

    await job_store.set(
        PipelineJob(
            job_id=job_id,
            extraction_status="pending",
            ingestion_status="skipped",
            created_at=dt_cls.now(UTC).isoformat(),
            entities_extracted=0,
            relationships_extracted=0,
            retry_count=0,
            last_error=None,
            next_retry_at=None,
            completed_at=None,
            tenant_id=tenant_id,
        )
    )

    config = _validated_extraction_config(
        request.extraction_config,
        tenant_id=tenant_id,
        operation="extraction job creation",
    )

    run_extraction_fn = _get_run_extraction_fn()

    background_tasks.add_task(
        run_extraction_fn,
        job_id=job_id,
        source_url=request.source_url,
        content=request.markdown_content,
        config=config,
    )

    return ExtractResponse(
        extraction_job_id=job_id, status="queued", message="Extraction job started"
    )


@router.post("/v1/extract-and-ingest", response_model=ExtractAndIngestResponse)
async def extract_and_ingest(
    request: ExtractRequest,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Start a combined extraction and ingestion pipeline job."""
    tenant_id = _require_authenticated_tenant_id(
        ctx.tenant_id, operation="extraction+ingestion job creation"
    )

    idempotency_key = _build_idempotency_key(
        tenant_id=tenant_id,
        source_url=request.source_url,
        content_id=request.content_id,
        extraction_config=request.extraction_config,
    )
    job_store = _get_active_job_store()
    existing_job_id = await job_store.get_job_id_for_idempotency_key(idempotency_key)

    config = _validated_extraction_config(
        request.extraction_config,
        tenant_id=tenant_id,
        operation="extraction+ingestion job creation",
    )

    run_extract_and_ingest_fn = _get_run_extract_and_ingest_fn()

    if existing_job_id:
        existing_job = await job_store.get(existing_job_id, tenant_id=tenant_id)
        if (
            existing_job
            and existing_job.extraction_status == "completed"
            and existing_job.ingestion_status == "completed"
        ):
            return ExtractAndIngestResponse(
                job_id=existing_job.job_id,
                overall_status=existing_job.overall_status,
                extraction_status=existing_job.extraction_status,
                ingestion_status=existing_job.ingestion_status,
                message="Extraction and ingestion already completed for idempotency key",
            )
        if existing_job:
            background_tasks.add_task(
                run_extract_and_ingest_fn,
                job_id=existing_job.job_id,
                source_url=request.source_url,
                content=request.markdown_content,
                config=config,
            )
            return ExtractAndIngestResponse(
                job_id=existing_job.job_id,
                overall_status=existing_job.overall_status,
                extraction_status=existing_job.extraction_status,
                ingestion_status=existing_job.ingestion_status,
                message="Extraction and ingestion retry queued for existing idempotency key",
            )

    job_id = str(uuid4())
    dt_cls = _get_active_datetime()

    await job_store.set(
        PipelineJob(
            job_id=job_id,
            extraction_status="pending",
            ingestion_status="pending",
            created_at=dt_cls.now(UTC).isoformat(),
            entities_extracted=0,
            relationships_extracted=0,
            retry_count=0,
            last_error=None,
            next_retry_at=None,
            completed_at=None,
            tenant_id=tenant_id,
        )
    )
    await job_store.set_job_id_for_idempotency_key(idempotency_key, job_id)

    background_tasks.add_task(
        run_extract_and_ingest_fn,
        job_id=job_id,
        source_url=request.source_url,
        content=request.markdown_content,
        config=config,
    )

    return ExtractAndIngestResponse(
        job_id=job_id,
        overall_status="pending",
        extraction_status="pending",
        ingestion_status="pending",
        message="Extraction and ingestion job started",
    )


@router.get("/v1/extract/status/{job_id}", response_model=ExtractionStatusResponse)
async def get_extraction_status(job_id: str, ctx: RequestContext = Depends(require_authenticated)):
    """Get status of a combined extraction and ingestion job."""
    job_store = _get_active_job_store()
    job = await job_store.get(job_id, tenant_id=str(ctx.tenant_id))
    if not job:
        raise NotFoundError(message="Job not found")

    return _pipeline_response(job)


@router.get("/v1/quarantine/{job_id}")
async def get_quarantine_status(job_id: str, ctx: RequestContext = Depends(require_authenticated)):
    tenant_id = str(ctx.tenant_id)
    quarantine_store = _get_active_quarantine_store()
    record = await quarantine_store.get_by_job(tenant_id=tenant_id, job_id=job_id)
    if record is None:
        raise NotFoundError(message="Quarantine record not found")
    return QuarantineStatusResponse.model_validate(record.model_dump())


@router.get("/v1/quarantine")
async def list_quarantine_jobs(ctx: RequestContext = Depends(require_authenticated)):
    tenant_id = str(ctx.tenant_id)
    quarantine_store = _get_active_quarantine_store()
    records = await quarantine_store.list(tenant_id=tenant_id)
    return [QuarantineStatusResponse.model_validate(r.model_dump()) for r in records]


@router.post("/v1/extract/batch")
async def extract_batch(
    requests: list[ExtractRequest],
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Start a batch extraction job."""
    tenant_id = _require_authenticated_tenant_id(
        ctx.tenant_id, operation="batch extraction job creation"
    )

    batch_id = str(uuid4())
    job_ids = []
    run_extraction_fn = _get_run_extraction_fn()

    for req in requests:
        job_id = str(uuid4())
        job_ids.append(job_id)
        config = _validated_extraction_config(
            req.extraction_config,
            tenant_id=tenant_id,
            operation="batch extraction job creation",
        )
        background_tasks.add_task(
            run_extraction_fn,
            job_id=job_id,
            source_url=req.source_url,
            content=req.markdown_content,
            config=config,
        )

    return extract_batchResult.model_validate(
        {
            "batch_job_id": batch_id,
            "job_ids": job_ids,
            "status": "queued",
            "total_jobs": len(requests),
        }
    )


@router.get("/v1/entities")
async def list_entities(
    entity_type: str | None = Query(
        None, enum=["Capability", "UseCase", "Persona", "ValueDriver", "Feature"]
    ),
    limit: int = Query(100, ge=1, le=1000),
    ctx: RequestContext = Depends(require_authenticated),
):
    """List entities in the ontology.

    Note: In a full implementation, this would query a persistent store.
    For now, returns empty list (entities are in RDF files).
    """
    _ = ctx.tenant_id
    return EntityListResponse(entity_type=entity_type or "all", entities=[], total=0)


@router.get("/v1/entities/{entity_id}/relationships")
async def get_relationships(entity_id: str, ctx: RequestContext = Depends(require_authenticated)):
    """Get relationships for an entity.

    Note: In a full implementation, this would query the graph database.
    """
    _ = ctx.tenant_id
    return RelationshipsResponse(entity_id=entity_id, incoming=[], outgoing=[])


@router.get("/v1/provenance/{job_id}")
async def get_provenance(
    job_id: str,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Get full provenance trace for an extraction job. Requires authentication."""
    tracker = get_provenance_tracker()
    activity = tracker.get_activity(job_id)

    if not activity:
        raise NotFoundError(message="Job not found")

    chain = activity.get_provenance_chain()

    return ProvenanceResponse(
        activity_id=chain["activity_id"],
        source=chain["source"],
        extraction=chain["extraction"],
        steps=chain["steps"],
        output=chain["output"],
    )


@router.get("/v1/provenance/entity/{entity_id}")
async def get_entity_provenance(
    entity_id: str,
    ctx: RequestContext = Depends(require_authenticated),
):
    """Get provenance for a specific entity. Requires authentication."""
    tracker = get_provenance_tracker()
    chain = tracker.get_provenance_for_entity(entity_id)

    if not chain:
        raise NotFoundError(message="Entity provenance not found")

    return chain


@router.get("/v1/extract/jobs/{job_id}/events")
async def stream_job_events(job_id: str, ctx: RequestContext = Depends(require_authenticated)):
    """Stream real-time events for a pipeline job via SSE.

    Returns a Server-Sent Events stream with progress updates,
    status changes, entity discovery, and log messages.
    """
    tenant_id = str(ctx.tenant_id)
    job_store = _get_active_job_store()
    if not await job_store.get(job_id, tenant_id=tenant_id):
        raise NotFoundError(message=str(f"Job {job_id} not found"))

    return StreamingResponse(
        _job_event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
