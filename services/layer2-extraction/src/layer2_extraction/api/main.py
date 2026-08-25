"""FastAPI application for Layer 2: Extraction Pipeline.

Provides REST API endpoints for:
- Extracting entities from content
- Batch extraction jobs
- Ontology queries
- Extraction status and results

Refactored into focused modules:
- `app_factory.py`: FastAPI app initialization, middleware, health probes, lifespan.
- `routes_extract.py`: Extraction endpoints, status, batch, ontology, provenance, and SSE routes.
- `pipeline_runner.py`: Pipeline execution stages, E2E local artifacts, and quarantine failure handling.
- `ingestion_runner.py`: Layer 3 ingestion dispatch, retry queueing, and background retry loop.
- `sse_stream.py`: SSE event generator and polling stream logic.
"""

from __future__ import annotations

import importlib

import structlog

# Third-party imports for health check
try:
    psutil = importlib.import_module("psutil")
except ImportError:
    psutil = None  # Health check will work without system metrics

from datetime import datetime

from fastapi import FastAPI

from layer2_extraction.api._shared import _current_environment
from layer2_extraction.api.app_factory import (
    _S2S_INTERNAL_PATHS,
    _TENANT_CONTEXT_EXEMPT_PATHS,
    _app_start_time,
    _is_strict_runtime,
    _pending_ingestion_probe,
    _quarantine_probe,
    create_app,
    health_checkResult,
    lifespan,
)
from layer2_extraction.api.ingestion_runner import (
    MAX_INGESTION_RETRIES,
    RETRY_BASE_SECONDS,
    _attempt_ingestion,
    _deserialize_artifacts,
    _pending_ingestion_retry_loop,
    _pending_ingestion_retry_task,
    _process_pending_ingestions,
    _queue_for_retry,
    _serialize_artifacts,
    _set_pipeline_job,
)
from layer2_extraction.api.pipeline_runner import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_RDF_OUTPUT_DIR,
    DEFAULT_SIMILARITY_THRESHOLD,
    PROGRESS_REPORT_INTERVAL,
    RELATIONSHIP_CONFIDENCE_OFFSET,
    ExtractionArtifacts,
    StampableEntity,
    _build_e2e_local_extraction_artifacts,
    _quarantine_validation_failure,
    _stamp_entity,
    get_entity_extractor,
    get_relationship_extractor,
    prompt_template_hash,
    prompt_template_version,
    run_extract_and_ingest,
    run_extraction,
)
from layer2_extraction.api.pipeline_status import (
    compute_overall_status as _compute_overall_status,
)
from layer2_extraction.api.routes_extract import (
    _pipeline_response,
    _require_authenticated_tenant_id,
    extract,
    extract_and_ingest,
    extract_batch,
    extract_batchResult,
    get_entity_provenance,
    get_extraction_status,
    get_provenance,
    get_quarantine_status,
    get_relationships,
    list_entities,
    list_quarantine_jobs,
    stream_job_events,
)
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
from layer2_extraction.api.sse_stream import (
    _SSE_LOG_LEVELS,
    _SSE_LOG_MESSAGES,
    _SSE_LOGGABLE_STATUSES,
    _SSE_POLL_INTERVAL_SECONDS,
    _SSE_PROGRESS_BOUNDARY_VALUES,
    _SSE_PROGRESS_THRESHOLD_PERCENT,
    _SSE_STATUS_PROGRESS_MAP,
    _SSE_TERMINAL_STATUSES,
    _job_event_generator,
)
from layer2_extraction.api.websocket import PipelineStage, get_pipeline_ws_manager
from layer2_extraction.integration.job_store import (
    JobStore,
    PipelineJob,
    build_job_store,
)
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.pending_ingestion_store import (
    PendingIngestionRecord,
    PendingIngestionStore,
    SqlitePendingIngestionStore,
    build_pending_ingestion_store,
)
from layer2_extraction.integration.quarantine_store import (
    QuarantineRecord,
    QuarantineStore,
    build_quarantine_store,
)
from layer2_extraction.metrics import MetricsMiddleware, get_metrics, initialize_metrics
from layer2_extraction.models import (
    Capability,
    ExtractionResult,
    Persona,
    PredicateType,
    Relationship,
    RoleType,
    SeniorityLevel,
    UseCase,
    ValueCategory,
    ValueDriver,
)
from layer2_extraction.output.provenance import (
    ExtractionStep,
    get_provenance_tracker,
)
from layer2_extraction.output.rdf_generator import generate_rdf
from layer2_extraction.shared_bootstrap import (
    create_fabric_app,
    install_metrics_middleware,
    register_health_endpoint,
    verify_metrics_access,
)
from layer2_extraction.validation import EntailmentValidator, ValidationSeverity
from layer2_extraction.validation.artifact_validator import (
    ArtifactValidationError,
    validate_extraction_result,
    validate_for_persistence,
    validate_relationship_for_persistence,
)


def _current_environment() -> str | None:
    """Return the normalized runtime environment for auth fail-closed policy checks.

    Local bypass of startup auth-key enforcement is allowed only when an explicit
    development/test environment is configured. Missing or custom environments
    are treated as strict by ``is_strict_environment``.
    """
    for key in ("LAYER2_ENV", "ENVIRONMENT", "APP_ENV"):
        value = os.getenv(key, "").strip()
        if value:
            return value.lower()
    return None


def _is_strict_runtime() -> bool:
    """Return whether Layer 2 must enforce strict startup safety checks."""
    environment = _current_environment()
    return is_strict_environment(environment or "unknown")


# App start time for uptime calculation
_app_start_time = time.time()

# WebSocket manager for real-time pipeline streaming
_ws_manager = get_pipeline_ws_manager()

# Simple lifespan function
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    # Startup
    logger.info("Layer2 extraction service starting up")
    yield
    # Shutdown
    logger.info("Layer2 extraction service shutting down")


# Public unauthenticated probes. All business/API and internal extraction routes
# must establish tenant context; S2S-only extraction routes stay outside this
# allowlist so they continue through the dedicated S2S JWT guard below.
_TENANT_CONTEXT_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/health",
    "/health/live",
    "/ready",
    "/readiness",
})

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None
try:
    import redis.asyncio as _redis_async
    _redis_client = _redis_async.Redis.from_url(_redis_url, decode_responses=True)
except Exception:
    pass


async def _pending_ingestion_probe() -> ProbeResult:
    """Readiness probe for the pending-ingestion store."""
    return await health_routes.pending_ingestion_probe(pending_ingestion_store)


async def _quarantine_probe() -> ProbeResult:
    """Readiness probe for the quarantine store."""
    return await health_routes.quarantine_probe(quarantine_store)


reject_insecure_bypass_in_production(service_name="layer2-extraction")
app = create_fabric_app(
    service_name="layer2-extraction",
    title="Layer 2 Extraction Service",
    version="1.0.0",
    description="Extraction pipeline for entities and relationships from content",
    lifespan=lifespan,
    health_probes=[
        RedisHealthProbe(name="redis", _client=_redis_client),
        CallableProbe(name="pending_ingestion_store", fn=_pending_ingestion_probe),
        CallableProbe(name="quarantine_store", fn=_quarantine_probe),
    ],
    readiness_path="/ready",
    enforcement_rollout=EnforcementRolloutConfig(
        tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
        health_checks=HealthChecksConfig(route_opt_out_paths=_TENANT_CONTEXT_EXEMPT_PATHS),
    ),
    enforce_tenant_context=True,
    instrument_telemetry=True,
)

# Register health endpoint
register_health_endpoint(app, service_name="layer2-extraction")

# Install Layer 2 Prometheus metrics middleware
install_metrics_middleware(
    app,
    metrics=initialize_metrics(),
    middleware_factory=MetricsMiddleware,
    logger=logger,
)

app.add_middleware(
    GovernanceMiddleware,
    api_key_resolver=None,
    rate_limiter=None,
)

logger = structlog.get_logger(__name__)

# Primary module-level store instances
job_store: JobStore = build_job_store()
quarantine_store: QuarantineStore = build_quarantine_store()
pending_ingestion_store: PendingIngestionStore = build_pending_ingestion_store()
sqlite_pending_ingestion_store = (
    pending_ingestion_store
    if isinstance(pending_ingestion_store, SqlitePendingIngestionStore)
    else None
)

_ws_manager = get_pipeline_ws_manager()

# Primary FastAPI application instance
app: FastAPI = create_app()

__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_RDF_OUTPUT_DIR",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "MAX_INGESTION_RETRIES",
    "PROGRESS_REPORT_INTERVAL",
    "RELATIONSHIP_CONFIDENCE_OFFSET",
    "RETRY_BASE_SECONDS",
    "EntityListResponse",
    "ExtractAndIngestResponse",
    "ExtractRequest",
    "ExtractResponse",
    "ExtractionArtifacts",
    "ExtractionStatusResponse",
    "JobStore",
    "Layer3KnowledgeClient",
    "PendingIngestionRecord",
    "PendingIngestionStore",
    "PipelineJob",
    "PipelineStage",
    "ProvenanceResponse",
    "QuarantineRecord",
    "QuarantineStatusResponse",
    "QuarantineStore",
    "RelationshipsResponse",
    "SqlitePendingIngestionStore",
    "StampableEntity",
    "_SSE_LOGGABLE_STATUSES",
    "_SSE_LOG_LEVELS",
    "_SSE_LOG_MESSAGES",
    "_SSE_POLL_INTERVAL_SECONDS",
    "_SSE_PROGRESS_BOUNDARY_VALUES",
    "_SSE_PROGRESS_THRESHOLD_PERCENT",
    "_SSE_STATUS_PROGRESS_MAP",
    "_SSE_TERMINAL_STATUSES",
    "_S2S_INTERNAL_PATHS",
    "_TENANT_CONTEXT_EXEMPT_PATHS",
    "_app_start_time",
    "_attempt_ingestion",
    "_build_e2e_local_extraction_artifacts",
    "_compute_overall_status",
    "_current_environment",
    "_deserialize_artifacts",
    "_is_strict_runtime",
    "_job_event_generator",
    "_pending_ingestion_probe",
    "_pending_ingestion_retry_loop",
    "_pending_ingestion_retry_task",
    "_pipeline_response",
    "_process_pending_ingestions",
    "_quarantine_probe",
    "_quarantine_validation_failure",
    "_queue_for_retry",
    "_require_authenticated_tenant_id",
    "_serialize_artifacts",
    "_set_pipeline_job",
    "_stamp_entity",
    "_ws_manager",
    "app",
    "create_app",
    "datetime",
    "extract",
    "extract_and_ingest",
    "extract_batch",
    "extract_batchResult",
    "get_entity_extractor",
    "get_entity_provenance",
    "get_extraction_status",
    "get_metrics",
    "get_provenance",
    "get_quarantine_status",
    "get_relationship_extractor",
    "get_relationships",
    "health_checkResult",
    "job_store",
    "lifespan",
    "list_entities",
    "list_quarantine_jobs",
    "pending_ingestion_store",
    "prompt_template_hash",
    "prompt_template_version",
    "psutil",
    "quarantine_store",
    "run_extract_and_ingest",
    "run_extraction",
    "sqlite_pending_ingestion_store",
    "stream_job_events",
]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
