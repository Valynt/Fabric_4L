"""HTTP endpoints for Layer 2 extraction and provenance workflows."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import Response
from value_fabric.shared.error_handling.exceptions import AuthorizationError, NotFoundError
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer2_extraction.api.deps import RequestContext, require_authenticated
from layer2_extraction.api.extraction_config import (
    build_idempotency_key as _build_idempotency_key,
)
from layer2_extraction.api.extraction_config import (
    validated_extraction_config as _validated_extraction_config,
)
from layer2_extraction.api.extraction_pipeline import (
    _pipeline_response,
    _require_authenticated_tenant_id,
)
from layer2_extraction.api.routes import health as health_routes
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
from layer2_extraction.integration.job_store import PipelineJob
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.metrics import get_metrics
from layer2_extraction.output.provenance import get_provenance_tracker
from layer2_extraction.shared_bootstrap import verify_metrics_access

router = APIRouter()
_app_start_time = 0.0
_psutil_module: object | None = None


def configure_health_dependencies(*, app_start_time: float, psutil_module: object | None) -> None:
    """Configure process-scoped dependencies used by the health endpoint."""
    global _app_start_time, _psutil_module
    _app_start_time = app_start_time
    _psutil_module = psutil_module


def _pipeline_api():
    """Resolve the compatibility facade lazily so existing patch points remain effective."""
    from layer2_extraction.api import main

    return main


class health_checkResult(TypedDictModel):
    dependencies: dict[str, object]
    metrics: dict[str, object]
    response_time_ms: float
    service: str
    status: str
    timestamp: str
    uptime_seconds: float
    version: str


class extract_batchResult(TypedDictModel):
    batch_job_id: str
    job_ids: list[str]
    status: str
    total_jobs: int


@router.get("/health")
async def health_check():
    """Health check endpoint with real metrics and dependency status."""
    payload = await health_routes.build_health_payload(
        app_start_time=_app_start_time,
        metrics=get_metrics(),
        layer3_client_factory=Layer3KnowledgeClient,
        psutil_module=_psutil_module,
    )
    return health_checkResult.model_validate(payload)


@router.get("/metrics")
async def metrics_endpoint(request: Request):
    """Prometheus metrics endpoint."""
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")

    metrics = get_metrics()

    if not metrics:
        return Response(
            content="# Metrics collection is disabled", status_code=503, media_type="text/plain"
        )

    try:
        metrics_data = metrics.get_metrics()
        return Response(content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8")
    except Exception as e:
        return Response(content=f"# Error: {e}", status_code=500, media_type="text/plain")


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

    # P1-3: MANDATORY VALIDATION GATE before job store persistence
    # PipelineJob requires tenant_id which is validated above
    await _pipeline_api().job_store.set(
        PipelineJob(
            job_id=job_id,
            extraction_status="pending",
            ingestion_status="skipped",
            created_at=datetime.now(UTC).isoformat(),
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

    # Queue extraction as background task
    background_tasks.add_task(
        _pipeline_api().run_extraction,
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
    existing_job_id = await _pipeline_api().job_store.get_job_id_for_idempotency_key(
        idempotency_key
    )

    config = _validated_extraction_config(
        request.extraction_config,
        tenant_id=tenant_id,
        operation="extraction+ingestion job creation",
    )

    if existing_job_id:
        existing_job = await _pipeline_api().job_store.get(existing_job_id, tenant_id=tenant_id)
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
                _pipeline_api().run_extract_and_ingest,
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

    await _pipeline_api().job_store.set(
        PipelineJob(
            job_id=job_id,
            extraction_status="pending",
            ingestion_status="pending",
            created_at=datetime.now(UTC).isoformat(),
            entities_extracted=0,
            relationships_extracted=0,
            retry_count=0,
            last_error=None,
            next_retry_at=None,
            completed_at=None,
            tenant_id=tenant_id,
        )
    )
    await _pipeline_api().job_store.set_job_id_for_idempotency_key(idempotency_key, job_id)

    background_tasks.add_task(
        _pipeline_api().run_extract_and_ingest,
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
    job = await _pipeline_api().job_store.get(job_id, tenant_id=str(ctx.tenant_id))
    if not job:
        raise NotFoundError(message="Job not found")

    return _pipeline_response(job)


@router.get("/v1/quarantine/{job_id}")
async def get_quarantine_status(job_id: str, ctx: RequestContext = Depends(require_authenticated)):
    tenant_id = str(ctx.tenant_id)
    record = await _pipeline_api().quarantine_store.get_by_job(tenant_id=tenant_id, job_id=job_id)
    if record is None:
        raise NotFoundError(message="Quarantine record not found")
    return QuarantineStatusResponse.model_validate(record.model_dump())


@router.get("/v1/quarantine")
async def list_quarantine_jobs(ctx: RequestContext = Depends(require_authenticated)):
    tenant_id = str(ctx.tenant_id)
    records = await _pipeline_api().quarantine_store.list(tenant_id=tenant_id)
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

    for req in requests:
        job_id = str(uuid4())
        job_ids.append(job_id)
        config = _validated_extraction_config(
            req.extraction_config,
            tenant_id=tenant_id,
            operation="batch extraction job creation",
        )
        background_tasks.add_task(
            _pipeline_api().run_extraction,
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
    # This would query Neo4j or similar in production, scoped to the authenticated tenant.
    _ = ctx.tenant_id
    return EntityListResponse(entity_type=entity_type or "all", entities=[], total=0)


@router.get("/v1/entities/{entity_id}/relationships")
async def get_relationships(entity_id: str, ctx: RequestContext = Depends(require_authenticated)):
    """Get relationships for an entity.

    Note: In a full implementation, this would query the graph database.
    """
    # This would query Neo4j or similar in production, scoped to the authenticated tenant.
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
