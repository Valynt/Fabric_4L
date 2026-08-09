"""Extraction execution and Layer 3 ingestion orchestration."""

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import structlog
from value_fabric.shared.audit import AuditAction, emit_audit_event
from value_fabric.shared.error_handling.exceptions import AuthorizationError

from layer2_extraction.alignment import SemanticAligner
from layer2_extraction.api.extraction_artifacts import (
    ExtractionArtifacts,
    _build_e2e_local_extraction_artifacts,
)
from layer2_extraction.api.extraction_config import (
    validated_extraction_config as _validated_extraction_config,
)
from layer2_extraction.api.main import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_RDF_OUTPUT_DIR,
    DEFAULT_SIMILARITY_THRESHOLD,
    PROGRESS_REPORT_INTERVAL,
    RELATIONSHIP_CONFIDENCE_OFFSET,
    _current_environment,
    _get_validated_openai_key,
    _is_strict_runtime,
    get_entity_extractor,
    get_relationship_extractor,
    prompt_template_hash,
    prompt_template_version,
)
from layer2_extraction.api.pipeline_status import compute_overall_status, pipeline_response_payload
from layer2_extraction.api.retry_queue import (
    ExtractionArtifactsPayload,
    deserialize_artifacts,
    next_retry_at,
    pending_retry_state,
    pipeline_job_kwargs_for_pending_record,
    serialize_artifacts,
)
from layer2_extraction.api.schemas import ExtractionStatusResponse
from layer2_extraction.api.websocket import PipelineStage, get_pipeline_ws_manager
from layer2_extraction.extraction.chunker import chunk_markdown
from layer2_extraction.extraction.deduplicator import deduplicate_entities
from layer2_extraction.extraction.llm_extractor import LLMExtractionError
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
    UseCase,
    ValueDriver,
)
from layer2_extraction.output.provenance import ExtractionStep, get_provenance_tracker
from layer2_extraction.output.rdf_generator import generate_rdf
from layer2_extraction.validation import EntailmentValidator, ValidationSeverity
from layer2_extraction.validation.artifact_validator import (
    ArtifactValidationError,
    validate_extraction_result,
    validate_for_persistence,
    validate_relationship_for_persistence,
)

logger = structlog.get_logger(__name__)
_ws_manager = get_pipeline_ws_manager()


# Global job store (Redis-backed if configured, otherwise in-memory)
job_store: JobStore = build_job_store()
RETRY_POLL_SECONDS = int(os.getenv("INGESTION_RETRY_POLL_SECONDS", "30"))
RETRY_BASE_SECONDS = int(os.getenv("INGESTION_RETRY_BASE_SECONDS", "60"))
MAX_INGESTION_RETRIES = int(os.getenv("INGESTION_MAX_RETRIES", "5"))
_UNSET = object()

try:
    pending_ingestion_store: PendingIngestionStore = build_pending_ingestion_store()
except Exception as exc:
    if _is_strict_runtime():
        logger.error(
            "Layer 2 pending-ingestion store is required in %s: %s", _current_environment(), exc
        )
        raise RuntimeError(
            f"Layer 2 pending-ingestion store is required in {_current_environment()}: {exc}"
        ) from exc
    logger.warning(
        "Failed to initialize configured pending-ingestion store, falling back to SQLite: %s",
        exc,
    )
    pending_ingestion_store = SqlitePendingIngestionStore(
        os.getenv("PENDING_INGESTION_SQLITE_PATH", "./data/pending_ingestion.db")
    )


quarantine_store = build_quarantine_store()


def _compute_overall_status(extraction_status: str, ingestion_status: str) -> str:
    return compute_overall_status(extraction_status, ingestion_status)


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


def _pipeline_response(job: PipelineJob) -> ExtractionStatusResponse:
    return ExtractionStatusResponse(**pipeline_response_payload(job))


def _serialize_artifacts(artifacts: ExtractionArtifacts) -> tuple[str, str]:
    return serialize_artifacts(
        ExtractionArtifactsPayload(
            result=artifacts.result,
            relationships=artifacts.relationships,
        )
    )


def _deserialize_artifacts(result_json: str, relationships_json: str) -> ExtractionArtifacts:
    artifacts = deserialize_artifacts(result_json, relationships_json)
    return ExtractionArtifacts(result=artifacts.result, relationships=artifacts.relationships)


async def _queue_for_retry(
    job_id: str,
    source_url: str,
    artifacts: ExtractionArtifacts,
    last_error: str,
    retry_count: int,
) -> None:
    next_retry_dt = next_retry_at(
        now=datetime.now(UTC),
        retry_base_seconds=RETRY_BASE_SECONDS,
        retry_count=retry_count,
        fromtimestamp=datetime.fromtimestamp,
    )
    result_json, relationships_json = _serialize_artifacts(artifacts)

    await pending_ingestion_store.enqueue(
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


async def _attempt_ingestion(job_id: str, source_url: str, artifacts: ExtractionArtifacts) -> bool:
    client = Layer3KnowledgeClient()
    try:
        job = await job_store.get(job_id)
        current_retry = job.retry_count if job else 0
        await _set_pipeline_job(job_id, ingestion_status="running", next_retry_at=None)

        # Broadcast ingestion start
        await _ws_manager.broadcast_ingestion_status(
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
                completed_at=datetime.now(UTC),
            )

            # Get updated job for retry count
            updated_job = await job_store.get(job_id)
            final_retry = updated_job.retry_count if updated_job else 0

            # Broadcast ingestion success
            await _ws_manager.broadcast_ingestion_status(
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
            await _ws_manager.broadcast_pipeline_complete(
                job_id=job_id,
                status="completed",
                entities_extracted=job.entities_extracted,
                relationships_extracted=job.relationships_extracted,
                entities_loaded=response.entities_loaded,
                relationships_loaded=response.relationships_loaded,
            )

            await pending_ingestion_store.complete(job_id)
            return True

        job = await job_store.get(job_id)
        retry_count = (job.retry_count + 1) if job else 1

        # Broadcast ingestion failure with retry
        await _ws_manager.broadcast_ingestion_status(
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
    now = datetime.now(UTC)
    records: list[PendingIngestionRecord] = await pending_ingestion_store.get_due(now)
    for record in records:
        if not await job_store.exists(record.job_id):
            await job_store.set(
                PipelineJob(
                    **pipeline_job_kwargs_for_pending_record(
                        record,
                        created_at=datetime.now(UTC),
                    )
                )
            )

        artifacts = _deserialize_artifacts(record.extraction_result_json, record.relationships_json)
        client = Layer3KnowledgeClient()
        try:
            healthy = await client.health_check()
        finally:
            await client.close()

        if not healthy:
            retry_count = record.retry_count + 1
            if retry_count >= record.max_retries:
                await pending_ingestion_store.complete(record.job_id)
                await _set_pipeline_job(
                    record.job_id,
                    ingestion_status="failed",
                    retry_count=retry_count,
                    last_error="Layer 3 unavailable after max retries",
                    next_retry_at=None,
                    completed_at=datetime.now(UTC),
                )
            else:
                retry_state = pending_retry_state(
                    now=datetime.now(UTC),
                    current_retry_count=record.retry_count,
                    retry_base_seconds=RETRY_BASE_SECONDS,
                    fromtimestamp=datetime.fromtimestamp,
                )
                await pending_ingestion_store.reschedule(
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
            metadata = await pending_ingestion_store.get_retry_metadata(record.job_id)
            if metadata:
                job = await job_store.get(record.job_id)
                current_retry = job.retry_count if job else 0
                await _set_pipeline_job(
                    record.job_id,
                    retry_count=metadata.get("retry_count", current_retry),
                    last_error=metadata.get("last_error"),
                    next_retry_at=(
                        datetime.fromisoformat(metadata["next_retry_at"])
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


# Vault health check error message (shared across layers)
_VAULT_UNREACHABLE_ERROR = "Vault unreachable — cannot start in production without secrets backend"


# Background task for extraction


async def _quarantine_validation_failure(
    *,
    tenant_id: str,
    job_id: str,
    source_url: str,
    source_hash: str,
    payload: str,
    errors: list[str],
    model_version: str,
    schema_version: str,
    prompt_template_version: str,
    prompt_template_hash: str | None = None,
    reason: str = "validation_error",
) -> QuarantineRecord:
    """Quarantine a validation failure with explicit version metadata.

    Args:
        tenant_id: Required tenant identifier (no fallbacks)
        job_id: Extraction job identifier
        source_url: Source document URL
        source_hash: Content hash for provenance
        payload: Failed payload
        errors: Validation error messages
        model_version: LLM model version (required, no fallback)
        schema_version: Schema version (required, no fallback)
        reason: Quarantine reason
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for quarantine records")
    if not model_version:
        raise ValueError("model_version is required for quarantine records")
    if not schema_version:
        raise ValueError("schema_version is required for quarantine records")

    record = QuarantineRecord(
        quarantine_id=str(uuid4()),
        job_id=job_id,
        tenant_id=tenant_id,
        source_url=source_url,
        source_hash=source_hash,
        model_version=model_version,
        schema_version=schema_version,
        prompt_template_version=prompt_template_version,
        prompt_template_hash=prompt_template_hash,
        payload_json=payload,
        validation_errors=errors,
        reason=reason,
    )
    await quarantine_store.put(record)
    await _set_pipeline_job(
        job_id,
        extraction_status="quarantined",
        last_error="; ".join(errors),
        completed_at=datetime.now(UTC),
    )
    try:
        from uuid import UUID as _UUID

        emit_audit_event(
            AuditAction.EXTRACTION_QUARANTINED,
            tenant_id=_UUID(tenant_id) if tenant_id else None,
            resource_type="ExtractionJob",
            resource_id=job_id,
            outcome="failure",
            details={
                "reason": reason,
                "source_url": source_url,
                "source_hash": source_hash,
                "model_version": model_version,
                "schema_version": schema_version,
                "prompt_template_version": prompt_template_version,
                "validation_errors": errors,
            },
        )
    except Exception:
        # Audit emission must never break the quarantine flow
        pass
    return record


def _require_authenticated_tenant_id(tenant_id: Any, *, operation: str) -> str:
    """Require authenticated tenant context and fail closed when missing."""
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


async def run_extraction(
    job_id: str,
    source_url: str,
    content: str,
    config: dict,
    mark_pipeline_complete: bool = True,
):
    """Background extraction task.

    Executes the full 6-stage extraction pipeline:
    1. Chunk input
    2. Extract entities
    3. Extract relationships
    4. Deduplicate
    5. Validate
    6. Generate RDF
    """
    tracker = get_provenance_tracker()

    # Calculate content hash for provenance
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Start provenance tracking
    activity = tracker.start_activity(activity_id=job_id, url=source_url, content_hash=content_hash)

    tenant_id = _require_authenticated_tenant_id(
        config.get("tenant_id"), operation="extraction execution"
    )

    if not await job_store.exists(job_id):
        # P1-3: MANDATORY VALIDATION GATE before job store persistence
        # PipelineJob is validated via tenant_id check in run_extraction
        await job_store.set(
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
            )
        )

    await _set_pipeline_job(job_id, extraction_status="running")

    config = _validated_extraction_config(config, tenant_id=tenant_id)
    model_version = config["model_version"]
    schema_version = config["schema_version"]
    prompt_version = config["prompt_version"]

    # S2-8: Validate prompt_version against PromptRegistry on startup
    from layer2_extraction.extraction.prompt_registry import get_prompt_registry

    registry = get_prompt_registry()
    registered = registry.get_version(str(prompt_version))
    if registered is None:
        logger.warning(
            "prompt_version %s not found in PromptRegistry — proceeding with unvalidated version",
            prompt_version,
        )

    telemetry_context = {
        "tenant_id": tenant_id,
        "ingestion_id": str(config.get("ingestion_id", "")),
        "model_version": str(model_version),
        "schema_version": str(schema_version),
        "value_pack_id": str(config.get("value_pack_id", "default")),
        "prompt_version": str(prompt_version),
    }
    metrics = get_metrics()

    # Broadcast pipeline start
    await _ws_manager.broadcast_stage_start(
        job_id=job_id, stage=PipelineStage.CHUNKING, stage_number=1, total_stages=6
    )

    try:
        # Stage 1: Chunking
        step1 = ExtractionStep(step_name="chunking", started_at=datetime.now(UTC))

        chunk_size = config.get("chunk_size", DEFAULT_CHUNK_SIZE)
        chunk_overlap = config.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)

        chunks = chunk_markdown(
            content, source_url=source_url, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        step1.completed_at = datetime.now(UTC)
        activity.add_step(step1)

        # Broadcast chunking complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.CHUNKING,
            stage_number=1,
            total_stages=6,
            result_summary={"chunks_created": len(chunks)},
        )

        if telemetry_context["model_version"] == "e2e-local-extraction-model":
            artifacts = _build_e2e_local_extraction_artifacts(
                job_id=job_id,
                source_url=source_url,
                content_hash=content_hash,
                telemetry_context=telemetry_context,
                chunks_processed=len(chunks),
            )
            result = artifacts.result
            all_relationships = artifacts.relationships
            validate_extraction_result(result)
            for rel in all_relationships:
                validate_relationship_for_persistence(rel)

            rdf_content = generate_rdf(result, all_relationships)
            output_dir = os.getenv("RDF_OUTPUT_DIR", DEFAULT_RDF_OUTPUT_DIR)
            os.makedirs(output_dir, exist_ok=True)
            rdf_path = f"{output_dir}/{job_id}.ttl"
            with open(rdf_path, "w") as f:
                f.write(rdf_content)

            activity.output_entities = [e.id for e in result.get_all_entities()]
            activity.output_relationships = [r.id for r in all_relationships]
            activity.complete(rdf_output_path=rdf_path)

            await _set_pipeline_job(
                job_id,
                extraction_status="completed",
                entities_extracted=len(activity.output_entities),
                relationships_extracted=len(activity.output_relationships),
                completed_at=datetime.now(UTC) if mark_pipeline_complete else None,
            )
            if metrics:
                metrics.record_extraction_outcome(
                    status="success",
                    tenant_id=telemetry_context["tenant_id"],
                    ingestion_id=telemetry_context["ingestion_id"],
                    extraction_job_id=job_id,
                    model_version=telemetry_context["model_version"],
                    schema_version=telemetry_context["schema_version"],
                    value_pack_id=telemetry_context["value_pack_id"],
                )
            logger.info(
                "Deterministic local extraction completed",
                extra={**telemetry_context, "extraction_job_id": job_id},
            )
            if mark_pipeline_complete:
                await _ws_manager.broadcast_pipeline_complete(
                    job_id=job_id,
                    status="completed",
                    entities_extracted=len(activity.output_entities),
                    relationships_extracted=len(activity.output_relationships),
                    rdf_path=rdf_path,
                )
            return artifacts

        # Stage 2 & 3: Entity and Relationship Extraction
        await _ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.ENTITY_EXTRACTION,
            stage_number=2,
            total_stages=6,
            metadata={"total_chunks": len(chunks)},
        )

        step2 = ExtractionStep(step_name="entity_extraction", started_at=datetime.now(UTC))

        all_entities: dict[str, list[Any]] = {
            "capabilities": [],
            "use_cases": [],
            "personas": [],
            "value_drivers": [],
            "features": [],
        }
        all_relationships = []

        confidence_threshold = config.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)

        for i, chunk in enumerate(chunks):
            # Broadcast progress at intervals
            if i % max(1, len(chunks) // PROGRESS_REPORT_INTERVAL) == 0 or i == len(chunks) - 1:
                await _ws_manager.broadcast_stage_progress(
                    job_id=job_id,
                    stage=PipelineStage.ENTITY_EXTRACTION,
                    stage_number=2,
                    total_stages=6,
                    items_processed=i + 1,
                    items_total=len(chunks),
                    stage_percent=int((i + 1) / len(chunks) * 100),
                )

            # Extract entities from chunk
            entities = await get_entity_extractor().extract_entities(
                text=chunk.content,
                source_url=source_url,
                extraction_job_id=job_id,
                confidence_threshold=confidence_threshold,
                telemetry_context=telemetry_context,
            )

            # Collect entities
            for entity_type, entity_list in entities.items():
                all_entities[entity_type].extend(entity_list)

            # Extract relationships
            relationships = await get_relationship_extractor().extract_relationships(
                text=chunk.content,
                entities=entities,
                source_url=source_url,
                extraction_job_id=job_id,
                confidence_threshold=confidence_threshold - RELATIONSHIP_CONFIDENCE_OFFSET,
                telemetry_context=telemetry_context,
            )
            all_relationships.extend(relationships)

        step2.completed_at = datetime.now(UTC)
        total_entities = sum(len(v) for v in all_entities.values())
        step2.entities_extracted = total_entities
        activity.add_step(step2)

        # Broadcast entity extraction complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.ENTITY_EXTRACTION,
            stage_number=2,
            total_stages=6,
            result_summary={
                "entities_extracted": total_entities,
                "relationships_found": len(all_relationships),
                "chunks_processed": len(chunks),
            },
        )

        # Stage 3: Semantic Alignment
        await _ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.SEMANTIC_ALIGNMENT,
            stage_number=3,
            total_stages=6,
            metadata={"entity_types": list(all_entities.keys())},
        )
        step_align = ExtractionStep(step_name="semantic_alignment", started_at=datetime.now(UTC))

        aligner = SemanticAligner(
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD, api_key=_get_validated_openai_key()
        )

        # Align each entity type
        aligned_entities = {}
        for entity_type, entity_list in all_entities.items():
            if entity_list:
                aligned_list, _ = await aligner.align_entities(entity_list)
                aligned_entities[entity_type] = aligned_list
            else:
                aligned_entities[entity_type] = []

        all_entities = aligned_entities

        step_align.completed_at = datetime.now(UTC)
        activity.add_step(step_align)

        # Broadcast alignment complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id, stage=PipelineStage.SEMANTIC_ALIGNMENT, stage_number=3, total_stages=6
        )

        # Stage 4: Deduplication
        await _ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.DEDUPLICATION,
            stage_number=4,
            total_stages=6,
            metadata={"entities_before": total_entities},
        )
        step3 = ExtractionStep(step_name="deduplication", started_at=datetime.now(UTC))

        deduplicated = await deduplicate_entities(
            all_entities,
            api_key=_get_validated_openai_key(),
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
            relationships=all_relationships,
            enable_coreference=True,
        )

        step3.completed_at = datetime.now(UTC)
        activity.add_step(step3)

        entities_after = sum(len(v) for v in deduplicated.values())

        # Broadcast deduplication complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.DEDUPLICATION,
            stage_number=4,
            total_stages=6,
            result_summary={
                "entities_before": total_entities,
                "entities_after": entities_after,
                "duplicates_removed": total_entities - entities_after,
            },
        )

        # Stage 5: Validation (EntailmentValidator with 6 validation rules)
        await _ws_manager.broadcast_stage_start(
            job_id=job_id, stage=PipelineStage.VALIDATION, stage_number=5, total_stages=6
        )
        step4 = ExtractionStep(step_name="validation", started_at=datetime.now(UTC))

        # Create extraction result
        result = ExtractionResult(
            job_id=job_id,
            source_url=source_url,
            capabilities=cast(list[Capability], deduplicated.get("capabilities", [])),
            use_cases=cast(list[UseCase], deduplicated.get("use_cases", [])),
            personas=cast(list[Persona], deduplicated.get("personas", [])),
            value_drivers=cast(list[ValueDriver], deduplicated.get("value_drivers", [])),
            features=deduplicated.get("features", []),
            chunks_processed=len(chunks),
            tenant_id=telemetry_context["tenant_id"],
            schema_version=telemetry_context["schema_version"],
            prompt_version=telemetry_context["prompt_version"],
            prompt_template_version=str(prompt_template_version),
            prompt_template_hash=str(prompt_template_hash) if prompt_template_hash else None,
            model_version=telemetry_context["model_version"],
            security_metadata=(
                get_entity_extractor().get_security_signals()
                + get_relationship_extractor().get_security_signals()
            ),
        )

        # MANDATORY VALIDATION GATE: Validate result before any persistence
        validate_extraction_result(result)

        # Run entailment validation
        validator = EntailmentValidator()
        validation_results = validator.validate(result, all_relationships)

        # Check for validation errors
        errors = [
            r for r in validation_results if r.severity == ValidationSeverity.ERROR and not r.passed
        ]
        warnings = [
            r
            for r in validation_results
            if r.severity == ValidationSeverity.WARNING and not r.passed
        ]

        if errors:
            error_messages = [f"[ERROR] {e.rule_id}: {e.message}" for e in errors]
            result.errors.extend(error_messages)
            await _quarantine_validation_failure(
                tenant_id=telemetry_context["tenant_id"],
                job_id=job_id,
                source_url=source_url,
                source_hash=content_hash,
                payload=result.model_dump_json(),
                errors=error_messages,
                model_version=telemetry_context["model_version"],
                schema_version=telemetry_context["schema_version"],
                prompt_template_version=str(prompt_template_version),
                prompt_template_hash=str(prompt_template_hash) if prompt_template_hash else None,
                reason="entailment_validation_failed",
            )
            return None
        if warnings:
            # Log warnings but continue
            result.errors.extend([f"[WARNING] {w.rule_id}: {w.message}" for w in warnings])

        step4.completed_at = datetime.now(UTC)
        step4.entities_extracted = len(validation_results)  # Track validation results count
        activity.add_step(step4)

        # Broadcast validation complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.VALIDATION,
            stage_number=5,
            total_stages=6,
            result_summary={
                "passed": len([r for r in validation_results if r.passed]),
                "failed": len([r for r in validation_results if not r.passed]),
                "errors": len(errors),
                "warnings": len(warnings),
            },
        )

        # Stage 6: RDF Generation
        await _ws_manager.broadcast_stage_start(
            job_id=job_id, stage=PipelineStage.RDF_GENERATION, stage_number=6, total_stages=6
        )
        step5 = ExtractionStep(step_name="rdf_generation", started_at=datetime.now(UTC))

        rdf_content = generate_rdf(result, all_relationships)

        # MANDATORY VALIDATION GATE: Validate all relationships before persistence
        for rel in all_relationships:
            validate_relationship_for_persistence(rel)

        # Broadcast RDF generation complete
        await _ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.RDF_GENERATION,
            stage_number=6,
            total_stages=6,
            result_summary={
                "rdf_size_bytes": len(rdf_content.encode("utf-8")),
                "entities_in_rdf": entities_after,
                "relationships_in_rdf": len(all_relationships),
            },
        )

        # Save RDF to file (in production, this would go to S3/MinIO)
        output_dir = os.getenv("RDF_OUTPUT_DIR", DEFAULT_RDF_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        rdf_path = f"{output_dir}/{job_id}.ttl"

        with open(rdf_path, "w") as f:
            f.write(rdf_content)

        step5.completed_at = datetime.now(UTC)
        activity.add_step(step5)

        # Complete activity
        activity.output_entities = [e.id for e in result.get_all_entities()]
        activity.output_relationships = [r.id for r in all_relationships]
        activity.complete(rdf_output_path=rdf_path)

        await _set_pipeline_job(
            job_id,
            extraction_status="completed",
            entities_extracted=len(activity.output_entities),
            relationships_extracted=len(activity.output_relationships),
            completed_at=datetime.now(UTC) if mark_pipeline_complete else None,
        )
        if metrics:
            metrics.record_extraction_outcome(
                status="success",
                tenant_id=telemetry_context["tenant_id"],
                ingestion_id=telemetry_context["ingestion_id"],
                extraction_job_id=job_id,
                model_version=telemetry_context["model_version"],
                schema_version=telemetry_context["schema_version"],
                value_pack_id=telemetry_context["value_pack_id"],
            )
        logger.info(
            "Extraction completed", extra={**telemetry_context, "extraction_job_id": job_id}
        )

        # Broadcast extraction-only completion (if not going to ingestion)
        if mark_pipeline_complete:
            await _ws_manager.broadcast_pipeline_complete(
                job_id=job_id,
                status="completed",
                entities_extracted=len(activity.output_entities),
                relationships_extracted=len(activity.output_relationships),
                rdf_path=rdf_path,
            )

        return ExtractionArtifacts(result=result, relationships=all_relationships)

    except Exception as e:
        logger.error(
            "Extraction failed",
            exc_info=e,
            extra={"job_id": job_id, "tenant_id": telemetry_context.get("tenant_id")},
        )
        error_msg = "Extraction failed due to internal error"
        if isinstance(e, LLMExtractionError):
            await _quarantine_validation_failure(
                tenant_id=telemetry_context["tenant_id"],
                job_id=job_id,
                source_url=source_url,
                source_hash=content_hash,
                payload=content[:4000],
                errors=[error_msg],
                model_version=telemetry_context["model_version"],
                schema_version=telemetry_context["schema_version"],
                prompt_template_version=str(prompt_template_version),
                prompt_template_hash=str(prompt_template_hash) if prompt_template_hash else None,
                reason="llm_schema_validation_failed",
            )
        activity.fail(error_msg)
        await _set_pipeline_job(
            job_id,
            extraction_status="failed",
            last_error=error_msg,
            completed_at=datetime.now(UTC),
        )
        if metrics:
            metrics.record_extraction_outcome(
                status="failure",
                tenant_id=telemetry_context["tenant_id"],
                ingestion_id=telemetry_context["ingestion_id"],
                extraction_job_id=job_id,
                model_version=telemetry_context["model_version"],
                schema_version=telemetry_context["schema_version"],
                value_pack_id=telemetry_context["value_pack_id"],
            )
            metrics.record_retry(
                tenant_id=telemetry_context["tenant_id"],
                ingestion_id=telemetry_context["ingestion_id"],
                extraction_job_id=job_id,
                model_version=telemetry_context["model_version"],
                schema_version=telemetry_context["schema_version"],
                value_pack_id=telemetry_context["value_pack_id"],
                endpoint="run_extraction",
            )
        logger.error("Extraction failed", extra={**telemetry_context, "extraction_job_id": job_id})

        # Broadcast extraction failure
        await _ws_manager.broadcast_error(
            job_id=job_id,
            stage=PipelineStage.RDF_GENERATION,  # Default to last stage
            error=error_msg,
            recoverable=False,
        )

        # Broadcast pipeline completion as failed
        await _ws_manager.broadcast_pipeline_complete(
            job_id=job_id,
            status="failed",
            entities_extracted=0,
            relationships_extracted=0,
            errors=[error_msg],
        )

        raise


async def run_extract_and_ingest(
    job_id: str,
    source_url: str,
    content: str,
    config: dict,
) -> None:
    """Run extraction and ingestion in one background pipeline."""
    try:
        artifacts = await run_extraction(
            job_id,
            source_url,
            content,
            config,
            mark_pipeline_complete=False,
        )
    except Exception:
        logger.exception("Extraction pipeline failed for job %s", job_id)
        return

    if not artifacts:
        return

    try:
        validate_for_persistence(artifacts)
    except ArtifactValidationError:
        _artifact_payload = json.dumps(
            {
                "result": artifacts.result.model_dump(mode="json"),
                "relationships": [r.model_dump(mode="json") for r in artifacts.relationships],
            }
        )
        await _quarantine_validation_failure(
            tenant_id=str(config.get("tenant_id", "")),
            job_id=job_id,
            source_url=source_url,
            source_hash=hashlib.sha256(content.encode()).hexdigest(),
            payload=_artifact_payload,
            errors=["extraction_failed"],
            model_version=str(config.get("model_version") or os.getenv("EXTRACTION_MODEL") or ""),
            schema_version=str(config.get("schema_version") or ""),
            prompt_template_version=str(config.get("prompt_template_version") or ""),
            reason="persistence_validation_failed",
        )
        return

    client = Layer3KnowledgeClient()
    try:
        healthy = await client.health_check()
    finally:
        await client.close()

    if not healthy:
        job = await job_store.get(job_id)
        retry_count = (job.retry_count + 1) if job else 1

        # Broadcast ingestion queued for retry
        await _ws_manager.broadcast_ingestion_status(
            job_id=job_id,
            status="queued",
            retry_count=retry_count,
            max_retries=MAX_INGESTION_RETRIES,
            error="Layer 3 unavailable - queued for retry",
        )

        await _queue_for_retry(
            job_id=job_id,
            source_url=source_url,
            artifacts=artifacts,
            last_error="Layer 3 unavailable",
            retry_count=retry_count,
        )
        return

    await _attempt_ingestion(job_id, source_url, artifacts)
