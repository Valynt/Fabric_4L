# ruff: noqa: F401, E402
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
)

"""FastAPI application for Layer 2: Extraction Pipeline.

Provides REST API endpoints for:
- Extracting entities from content
- Batch extraction jobs
- Ontology queries
- Extraction status and results

P1-29: OpenTelemetry tracing integration for observability.
"""

import asyncio
import hashlib
import importlib
import json
import os
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar, cast
from uuid import NAMESPACE_URL, uuid4, uuid5

import structlog

# Third-party imports for health check
try:
    psutil = importlib.import_module("psutil")
except ImportError:
    psutil = None  # Health check will work without system metrics

from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request
from fastapi.responses import Response, StreamingResponse

# Load secrets from Infisical if available (optional in dev, required in prod)
from value_fabric.shared.environment import (
    get_service_environment,
    is_production_like_environment,
)
from value_fabric.shared.secrets import load_infisical_secrets
from value_fabric.shared.security.config import is_strict_environment
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from layer2_extraction.api.deps import RequestContext, require_authenticated
from layer2_extraction.logging_config import configure_structured_logging

# Configure structured logging BEFORE any operations that might log
try:
    configure_structured_logging()
except Exception:
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)

logger = structlog.get_logger(__name__)

from value_fabric.shared.identity.middleware import GovernanceMiddleware

try:
    load_infisical_secrets()
except Exception as exc:
    _secret_env = get_service_environment("layer2")
    logger.warning("Failed to load Infisical secrets (dev mode): %s", exc)
    if is_production_like_environment(_secret_env):
        raise RuntimeError("Failed to load Infisical secrets in production-like Layer 2 runtime")

from value_fabric.shared.fastapi_framework import (
    EnforcementControlConfig,
    EnforcementMode,
    EnforcementRolloutConfig,
    HealthChecksConfig,
)
from value_fabric.shared.fastapi_framework.health import (
    CallableProbe,
    ProbeResult,
    RedisHealthProbe,
)

from layer2_extraction.alignment import SemanticAligner
from layer2_extraction.api import s2s_auth
from layer2_extraction.api.extraction_config import (
    build_idempotency_key as _build_idempotency_key,
)
from layer2_extraction.api.extraction_config import (
    validated_extraction_config as _validated_extraction_config,
)
from layer2_extraction.api.extractor_factory import LazyExtractorFactory, validated_openai_key
from layer2_extraction.api.pipeline_status import (
    compute_overall_status,
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
from layer2_extraction.api.routes import health as health_routes
from layer2_extraction.api.routes.signal_lifecycle import router as signal_lifecycle_router
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
from layer2_extraction.api.websocket import PipelineStage, get_pipeline_ws_manager
from layer2_extraction.extraction.chunker import chunk_markdown
from layer2_extraction.extraction.deduplicator import deduplicate_entities
from layer2_extraction.extraction.llm_extractor import (
    EntityExtractor,
    LLMExtractionError,
    RelationshipExtractor,
)
from layer2_extraction.extraction.prompt_loader import (
    ENTITY_PROMPT_TEMPLATE_VERSION,
    RELATIONSHIP_PROMPT_TEMPLATE_VERSION,
)

# Module-level prompt template metadata (referenced throughout extraction pipeline)
prompt_template_version = f"{ENTITY_PROMPT_TEMPLATE_VERSION}+{RELATIONSHIP_PROMPT_TEMPLATE_VERSION}"
prompt_template_hash: str | None = None

from value_fabric.shared.audit import AuditAction, emit_audit_event

from layer2_extraction.extraction.entity_id import compute_deterministic_id
from layer2_extraction.integration.job_store import JobStore, PipelineJob, build_job_store
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.pending_ingestion_store import (
    PendingIngestionRecord,
    PendingIngestionStore,
    SqlitePendingIngestionStore,
    build_pending_ingestion_store,
)
from layer2_extraction.integration.quarantine_store import QuarantineRecord, build_quarantine_store
from layer2_extraction.metrics import get_metrics
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
_TENANT_CONTEXT_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/health/live",
        "/ready",
        "/readiness",
    }
)

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

app.add_middleware(
    GovernanceMiddleware,
    api_key_resolver=None,
    rate_limiter=None,
)
logger.info("GovernanceMiddleware installed", component="layer2-extraction")

# Strict-environment startup guard: fail fast if auth keys are missing.
if _is_strict_runtime() and not os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip():
    raise RuntimeError(
        "FABRIC_AUTH_PUBLIC_KEYS is required in strict environments for Layer 2 authentication."
    )

# Register canonical error envelope handlers from shared package
try:
    from value_fabric.shared.error_handling import register_exception_handlers

    register_exception_handlers(app)
except ImportError:
    # Fallback: shared package not available, handlers will be added elsewhere
    pass

app.include_router(signal_lifecycle_router)

# ── P1-017: Inbound S2S JWT guard for internal extraction routes ──────────────
# L1 Celery dispatch signs outbound requests with encode_service_jwt (sub=
# "layer1-ingestion", aud="layer2-extraction").  GovernanceMiddleware validates
# user-facing JWTs but does NOT enforce the service-specific sub/aud claims.
# This middleware enforces that when SERVICE_AUTH_SECRET is configured, these
# three internal routes may ONLY be called with a valid L1 S2S token.

_S2S_INTERNAL_PATHS = s2s_auth.S2S_INTERNAL_PATHS


@app.middleware("http")
async def _s2s_auth_guard(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Enforce inbound S2S JWT on internal extraction routes.

    In strict environments, the check is mandatory and fails closed.
    In explicit dev/test environments without SERVICE_AUTH_SECRET, the check is skipped.
    """
    return await s2s_auth.enforce_s2s_auth_guard(
        request,
        call_next,
        is_strict_runtime=_is_strict_runtime,
    )


# ── End P1-017 ────────────────────────────────────────────────────────────────

# Extraction configuration constants
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
RELATIONSHIP_CONFIDENCE_OFFSET = 0.05  # Slightly lower threshold for relationships
DEFAULT_SIMILARITY_THRESHOLD = 0.85
PROGRESS_REPORT_INTERVAL = 10  # Report progress every N chunks
DEFAULT_RDF_OUTPUT_DIR = "/tmp/rdf"  # nosec B108


def _get_validated_openai_key() -> str | None:
    """Return the OpenAI API key from the environment, or None if absent.

    Raises RuntimeError in strict environments when:
    - The key is missing entirely.
    - The key matches a known placeholder value.
    - The key does not start with the 'sk-' prefix expected by the OpenAI SDK.
    """
    return validated_openai_key(is_strict_runtime=_is_strict_runtime, logger=logger)


_extractor_factory = LazyExtractorFactory(
    entity_extractor_cls=EntityExtractor,
    relationship_extractor_cls=RelationshipExtractor,
    key_provider=_get_validated_openai_key,
    model_provider=lambda: os.getenv("LLM_MODEL", "gpt-4o"),
)


def get_entity_extractor():
    """Get or create the entity extractor (lazy initialization)."""
    return _extractor_factory.get_entity_extractor()


def get_relationship_extractor():
    """Get or create the relationship extractor (lazy initialization)."""
    return _extractor_factory.get_relationship_extractor()


# Import pipeline internals here to preserve the established main-module import surface.
from layer2_extraction.api.extraction_artifacts import ExtractionArtifacts
from layer2_extraction.api.extraction_pipeline import (
    MAX_INGESTION_RETRIES,
    RETRY_BASE_SECONDS,
    RETRY_POLL_SECONDS,
    _compute_overall_status,
    _pending_ingestion_retry_loop,
    _require_authenticated_tenant_id,
    job_store,
    pending_ingestion_store,
    quarantine_store,
)
from layer2_extraction.api.extraction_pipeline import (
    _attempt_ingestion as _attempt_ingestion_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _deserialize_artifacts as _deserialize_artifacts_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _process_pending_ingestions as _process_pending_ingestions_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _quarantine_validation_failure as _quarantine_validation_failure_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _queue_for_retry as _queue_for_retry_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _serialize_artifacts as _serialize_artifacts_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    _set_pipeline_job as _set_pipeline_job_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    run_extract_and_ingest as run_extract_and_ingest_impl,
)
from layer2_extraction.api.extraction_pipeline import (
    run_extraction as run_extraction_impl,
)


def _sync_pipeline_state() -> None:
    """Propagate established main-module overrides to the pipeline implementation."""
    from layer2_extraction.api import extraction_pipeline

    extraction_pipeline.job_store = job_store
    extraction_pipeline.pending_ingestion_store = pending_ingestion_store
    extraction_pipeline.quarantine_store = quarantine_store
    extraction_pipeline.datetime = datetime
    extraction_pipeline.Layer3KnowledgeClient = Layer3KnowledgeClient


async def _set_pipeline_job(*args, **kwargs):
    _sync_pipeline_state()
    return await _set_pipeline_job_impl(*args, **kwargs)


def _serialize_artifacts(*args, **kwargs):
    return _serialize_artifacts_impl(*args, **kwargs)


def _deserialize_artifacts(*args, **kwargs):
    return _deserialize_artifacts_impl(*args, **kwargs)


async def _queue_for_retry(*args, **kwargs):
    _sync_pipeline_state()
    return await _queue_for_retry_impl(*args, **kwargs)


async def _attempt_ingestion(*args, **kwargs):
    _sync_pipeline_state()
    return await _attempt_ingestion_impl(*args, **kwargs)


async def _process_pending_ingestions(*args, **kwargs):
    _sync_pipeline_state()
    return await _process_pending_ingestions_impl(*args, **kwargs)


async def _quarantine_validation_failure(*args, **kwargs):
    _sync_pipeline_state()
    return await _quarantine_validation_failure_impl(*args, **kwargs)


async def run_extraction(*args, **kwargs):
    _sync_pipeline_state()
    from layer2_extraction.api import extraction_pipeline

    extraction_pipeline._quarantine_validation_failure = _quarantine_validation_failure
    return await run_extraction_impl(*args, **kwargs)


async def run_extract_and_ingest(*args, **kwargs):
    _sync_pipeline_state()
    from layer2_extraction.api import extraction_pipeline

    extraction_pipeline.run_extraction = run_extraction
    extraction_pipeline._queue_for_retry = _queue_for_retry
    extraction_pipeline._quarantine_validation_failure = _quarantine_validation_failure
    return await run_extract_and_ingest_impl(*args, **kwargs)


from layer2_extraction.api.routes.extraction_api import (
    configure_health_dependencies,
)
from layer2_extraction.api.routes.extraction_api import (
    extract as extract,
)
from layer2_extraction.api.routes.extraction_api import (
    extract_and_ingest as extract_and_ingest,
)
from layer2_extraction.api.routes.extraction_api import (
    extract_batch as extract_batch,
)
from layer2_extraction.api.routes.extraction_api import (
    extract_batchResult as extract_batchResult,
)
from layer2_extraction.api.routes.extraction_api import (
    get_entity_provenance as get_entity_provenance,
)
from layer2_extraction.api.routes.extraction_api import (
    get_extraction_status as get_extraction_status,
)
from layer2_extraction.api.routes.extraction_api import (
    get_provenance as get_provenance,
)
from layer2_extraction.api.routes.extraction_api import (
    get_quarantine_status as get_quarantine_status,
)
from layer2_extraction.api.routes.extraction_api import (
    get_relationships as get_relationships,
)
from layer2_extraction.api.routes.extraction_api import (
    health_check as health_check,
)
from layer2_extraction.api.routes.extraction_api import (
    health_checkResult as health_checkResult,
)
from layer2_extraction.api.routes.extraction_api import (
    list_entities as list_entities,
)
from layer2_extraction.api.routes.extraction_api import (
    list_quarantine_jobs as list_quarantine_jobs,
)
from layer2_extraction.api.routes.extraction_api import (
    metrics_endpoint as metrics_endpoint,
)
from layer2_extraction.api.routes.extraction_api import (
    router as extraction_router,
)
from layer2_extraction.api.routes.streaming import (
    _SSE_TERMINAL_STATUSES,
    _job_event_generator,
)
from layer2_extraction.api.routes.streaming import (
    router as streaming_router,
)
from layer2_extraction.api.routes.streaming import (
    stream_job_events as stream_job_events,
)

# Health route dependencies are assigned without changing the public endpoints.
configure_health_dependencies(app_start_time=_app_start_time, psutil_module=psutil)
app.include_router(extraction_router)
app.include_router(streaming_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
