"""Pipeline runner for Layer 2 extraction workflows.

Executes local deterministic and multi-stage LLM extraction pipelines, semantic
alignment, entity deduplication, validation, RDF generation, and error quarantining.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar, cast
from uuid import NAMESPACE_URL, uuid4, uuid5

import structlog
from value_fabric.shared.error_handling.exceptions import AuthorizationError

from layer2_extraction.alignment import SemanticAligner
from layer2_extraction.api.extraction_config import (
    validated_extraction_config as _validated_extraction_config,
)
from layer2_extraction.api.extractor_factory import LazyExtractorFactory, validated_openai_key
from layer2_extraction.api.websocket import PipelineStage, get_pipeline_ws_manager
from layer2_extraction.extraction.chunker import chunk_markdown
from layer2_extraction.extraction.deduplicator import deduplicate_entities
from layer2_extraction.extraction.entity_id import compute_deterministic_id
from layer2_extraction.extraction.llm_extractor import (
    EntityExtractor,
    LLMExtractionError,
    RelationshipExtractor,
)
from layer2_extraction.extraction.prompt_loader import (
    ENTITY_PROMPT_TEMPLATE_VERSION,
    RELATIONSHIP_PROMPT_TEMPLATE_VERSION,
)
from layer2_extraction.integration.job_store import JobStore, PipelineJob, build_job_store
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.quarantine_store import (
    QuarantineRecord,
    QuarantineStore,
    build_quarantine_store,
)
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
from layer2_extraction.validation import EntailmentValidator, ValidationSeverity
from layer2_extraction.validation.artifact_validator import (
    ArtifactValidationError,
    validate_extraction_result,
    validate_for_persistence,
    validate_relationship_for_persistence,
)

logger = structlog.get_logger(__name__)

# Module-level prompt template metadata (referenced throughout extraction pipeline)
prompt_template_version = f"{ENTITY_PROMPT_TEMPLATE_VERSION}+{RELATIONSHIP_PROMPT_TEMPLATE_VERSION}"
prompt_template_hash: str | None = None

# Extraction configuration constants
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
RELATIONSHIP_CONFIDENCE_OFFSET = 0.05  # Slightly lower threshold for relationships
DEFAULT_SIMILARITY_THRESHOLD = 0.85
PROGRESS_REPORT_INTERVAL = 10  # Report progress every N chunks
DEFAULT_RDF_OUTPUT_DIR = "/tmp/rdf"  # nosec B108


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


def _get_active_ws_manager():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "_ws_manager"):
        return main_mod._ws_manager
    return get_pipeline_ws_manager()


def _get_active_metrics():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "get_metrics"):
        return main_mod.get_metrics()
    return get_metrics()


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


def _get_active_is_strict_runtime():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "_is_strict_runtime"):
        return main_mod._is_strict_runtime
    from layer2_extraction.api.app_factory import _is_strict_runtime

    return _is_strict_runtime


def _get_validated_openai_key() -> str | None:
    return validated_openai_key(is_strict_runtime=_get_active_is_strict_runtime(), logger=logger)


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


@dataclass
class ExtractionArtifacts:
    """Outputs from extraction pipeline used by ingestion step."""

    result: ExtractionResult
    relationships: list[Relationship]


class StampableEntity(Protocol):
    id: str
    tenant_id: str | None
    extraction_job_id: str | None
    schema_version: str
    prompt_version_id: str
    model_version: str
    deterministic_id: str | None


StampableEntityT = TypeVar("StampableEntityT", bound=StampableEntity)


def _stamp_entity(
    entity: StampableEntityT,
    *,
    entity_type: str,
    tenant_id: str,
    source_hash: str,
    source_url: str,
    extraction_job_id: str,
    telemetry_context: dict[str, str],
) -> StampableEntityT:
    entity.tenant_id = tenant_id
    entity.extraction_job_id = extraction_job_id
    entity.schema_version = telemetry_context["schema_version"]
    entity.prompt_version_id = telemetry_context["prompt_version"]
    entity.model_version = telemetry_context["model_version"]
    if hasattr(entity, "source_refs"):
        entity.source_refs = [source_url]
    deterministic_id = compute_deterministic_id(
        tenant_id=tenant_id,
        source_hash=source_hash,
        entity_type=entity_type,
        entity=entity,
        extraction_version="e2e-local-v1",
    )
    entity.id = deterministic_id
    entity.deterministic_id = deterministic_id
    return entity


def _build_e2e_local_extraction_artifacts(
    *,
    job_id: str,
    source_url: str,
    content_hash: str,
    telemetry_context: dict[str, str],
    chunks_processed: int,
) -> ExtractionArtifacts:
    """Build deterministic local E2E extraction artifacts without an LLM call."""
    tenant_id = telemetry_context["tenant_id"]
    capability = _stamp_entity(
        Capability(
            name="Evidence-backed ROI business case generation",
            description=(
                "Generates standardized, evidence-backed ROI business cases "
                "from discovery notes, account context, and benchmark inputs."
            ),
            technical_features=[
                "Discovery intake normalization",
                "Benchmark-grounded ROI modeling",
                "Finance-ready value proof generation",
            ],
            confidence=0.96,
        ),
        entity_type="capability",
        tenant_id=tenant_id,
        source_hash=content_hash,
        source_url=source_url,
        extraction_job_id=job_id,
        telemetry_context=telemetry_context,
    )
    use_case = _stamp_entity(
        UseCase(
            name="Late-stage SaaS opportunity value engineering",
            description=(
                "Standardizes AE and SE discovery handoffs, builds a reusable "
                "business case, and connects value claims to evidence."
            ),
            industry_context=["Software as a Service", "B2B revenue operations"],
            required_capabilities=[capability.id],
            workflow_steps=[
                "Capture discovery intake",
                "Map buyer pain to value drivers",
                "Generate ROI assumptions",
                "Attach evidence for finance review",
            ],
            kpis=["SE hours per opportunity", "late-stage win rate", "sales cycle days"],
            confidence=0.95,
        ),
        entity_type="usecase",
        tenant_id=tenant_id,
        source_hash=content_hash,
        source_url=source_url,
        extraction_job_id=job_id,
        telemetry_context=telemetry_context,
    )
    persona = _stamp_entity(
        Persona(
            role_type=RoleType.ECONOMIC_BUYER,
            seniority_level=SeniorityLevel.C_SUITE,
            title="Chief Financial Officer",
            department="Finance",
            pain_points=[
                "ROI assumptions are inconsistent",
                "Procurement challenges value claims",
            ],
            success_metrics=["validated ROI", "payback period", "business case quality"],
            confidence=0.93,
        ),
        entity_type="persona",
        tenant_id=tenant_id,
        source_hash=content_hash,
        source_url=source_url,
        extraction_job_id=job_id,
        telemetry_context=telemetry_context,
    )
    value_driver = _stamp_entity(
        ValueDriver(
            category=ValueCategory.COST_REDUCTION,
            name="SE hours per opportunity reduction",
            description=(
                "Reduces sales engineering effort by reusing structured discovery "
                "context and automatically generating finance-ready business cases."
            ),
            metrics=["se_hours_per_opportunity", "sales_engineering_cost"],
            formula_string="se_hours_per_opp * opps_per_year * hourly_se_cost * se_time_reduction",
            unit="USD/year",
            time_to_value="90 days",
            confidence=0.94,
        ),
        entity_type="valuedriver",
        tenant_id=tenant_id,
        source_hash=content_hash,
        source_url=source_url,
        extraction_job_id=job_id,
        telemetry_context=telemetry_context,
    )
    relationship_id = str(
        uuid5(NAMESPACE_URL, f"{tenant_id}|{content_hash}|{capability.id}|enables|{use_case.id}")
    )
    relationship = Relationship(
        id=relationship_id,
        source_id=capability.id,
        raw_predicate="enables",
        canonical_predicate=PredicateType.ENABLES,
        target_id=use_case.id,
        confidence=0.95,
        evidence_text="The extracted capability enables standardized value engineering for late-stage opportunities.",
        source_url=source_url,
        extraction_job_id=job_id,
        tenant_id=tenant_id,
        deterministic_id=relationship_id,
        schema_version=telemetry_context["schema_version"],
        prompt_version_id=telemetry_context["prompt_version"],
        model_version=telemetry_context["model_version"],
    )
    result = ExtractionResult(
        job_id=job_id,
        source_url=source_url,
        capabilities=[capability],
        use_cases=[use_case],
        personas=[persona],
        value_drivers=[value_driver],
        chunks_processed=chunks_processed,
        tenant_id=tenant_id,
        schema_version=telemetry_context["schema_version"],
        prompt_version=telemetry_context["prompt_version"],
        prompt_template_version=telemetry_context["prompt_version"],
        model_version=telemetry_context["model_version"],
    )
    return ExtractionArtifacts(result=result, relationships=[relationship])


async def run_extraction(
    job_id: str,
    source_url: str,
    content: str,
    config: dict,
    mark_pipeline_complete: bool = True,
) -> ExtractionArtifacts | None:
    """Background extraction task.

    Executes the full 6-stage extraction pipeline:
    1. Chunk input
    2. Extract entities
    3. Extract relationships
    4. Deduplicate
    5. Validate
    6. Generate RDF
    """
    from layer2_extraction.api.ingestion_runner import _set_pipeline_job
    from layer2_extraction.api.routes_extract import _require_authenticated_tenant_id

    job_store = _get_active_job_store()
    ws_manager = _get_active_ws_manager()
    metrics = _get_active_metrics()
    dt_cls = _get_active_datetime()

    tracker = get_provenance_tracker()
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    activity = tracker.start_activity(activity_id=job_id, url=source_url, content_hash=content_hash)

    tenant_id = _require_authenticated_tenant_id(
        config.get("tenant_id"), operation="extraction execution"
    )

    if not await job_store.exists(job_id):
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
    else:
        existing_job = await job_store.get(job_id, tenant_id=tenant_id)
        if existing_job is None:
            raise AuthorizationError(
                message="Request failed",
                details={
                    "code": "tenant_context_mismatch",
                    "message": "Extraction job tenant does not match the authenticated tenant context.",
                },
            )

    await _set_pipeline_job(job_id, extraction_status="running")

    config = _validated_extraction_config(config, tenant_id=tenant_id)
    model_version = config["model_version"]
    schema_version = config["schema_version"]
    prompt_version = config["prompt_version"]

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

    await ws_manager.broadcast_stage_start(
        job_id=job_id, stage=PipelineStage.CHUNKING, stage_number=1, total_stages=6
    )

    try:
        # Stage 1: Chunking
        step1 = ExtractionStep(step_name="chunking", started_at=dt_cls.now(UTC))

        chunk_size = config.get("chunk_size", DEFAULT_CHUNK_SIZE)
        chunk_overlap = config.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)

        chunks = chunk_markdown(
            content, source_url=source_url, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        step1.completed_at = dt_cls.now(UTC)
        activity.add_step(step1)

        await ws_manager.broadcast_stage_complete(
            job_id=job_id,
            stage=PipelineStage.CHUNKING,
            stage_number=1,
            total_stages=6,
            result_summary={"chunks_created": len(chunks)},
        )

        if telemetry_context["model_version"] == "e2e-local-extraction-model":
            build_fn = _build_e2e_local_extraction_artifacts
            main_mod = sys.modules.get("layer2_extraction.api.main")
            if main_mod and hasattr(main_mod, "_build_e2e_local_extraction_artifacts"):
                build_fn = main_mod._build_e2e_local_extraction_artifacts
            artifacts = build_fn(
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
                completed_at=dt_cls.now(UTC) if mark_pipeline_complete else None,
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
                await ws_manager.broadcast_pipeline_complete(
                    job_id=job_id,
                    status="completed",
                    entities_extracted=len(activity.output_entities),
                    relationships_extracted=len(activity.output_relationships),
                    rdf_path=rdf_path,
                )
            return artifacts

        # Stage 2 & 3: Entity and Relationship Extraction
        await ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.ENTITY_EXTRACTION,
            stage_number=2,
            total_stages=6,
            metadata={"total_chunks": len(chunks)},
        )

        step2 = ExtractionStep(step_name="entity_extraction", started_at=dt_cls.now(UTC))

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
            if i % max(1, len(chunks) // PROGRESS_REPORT_INTERVAL) == 0 or i == len(chunks) - 1:
                await ws_manager.broadcast_stage_progress(
                    job_id=job_id,
                    stage=PipelineStage.ENTITY_EXTRACTION,
                    stage_number=2,
                    total_stages=6,
                    items_processed=i + 1,
                    items_total=len(chunks),
                    stage_percent=int((i + 1) / len(chunks) * 100),
                )

            entities = await get_entity_extractor().extract_entities(
                text=chunk.content,
                source_url=source_url,
                extraction_job_id=job_id,
                confidence_threshold=confidence_threshold,
                telemetry_context=telemetry_context,
            )

            for entity_type, entity_list in entities.items():
                all_entities[entity_type].extend(entity_list)

            relationships = await get_relationship_extractor().extract_relationships(
                text=chunk.content,
                entities=entities,
                source_url=source_url,
                extraction_job_id=job_id,
                confidence_threshold=confidence_threshold - RELATIONSHIP_CONFIDENCE_OFFSET,
                telemetry_context=telemetry_context,
            )
            all_relationships.extend(relationships)

        step2.completed_at = dt_cls.now(UTC)
        total_entities = sum(len(v) for v in all_entities.values())
        step2.entities_extracted = total_entities
        activity.add_step(step2)

        await ws_manager.broadcast_stage_complete(
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
        await ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.SEMANTIC_ALIGNMENT,
            stage_number=3,
            total_stages=6,
            metadata={"entity_types": list(all_entities.keys())},
        )
        step_align = ExtractionStep(step_name="semantic_alignment", started_at=dt_cls.now(UTC))

        aligner = SemanticAligner(
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD, api_key=_get_validated_openai_key()
        )

        aligned_entities = {}
        for entity_type, entity_list in all_entities.items():
            if entity_list:
                aligned_list, _ = await aligner.align_entities(entity_list)
                aligned_entities[entity_type] = aligned_list
            else:
                aligned_entities[entity_type] = []

        all_entities = aligned_entities

        step_align.completed_at = dt_cls.now(UTC)
        activity.add_step(step_align)

        await ws_manager.broadcast_stage_complete(
            job_id=job_id, stage=PipelineStage.SEMANTIC_ALIGNMENT, stage_number=3, total_stages=6
        )

        # Stage 4: Deduplication
        await ws_manager.broadcast_stage_start(
            job_id=job_id,
            stage=PipelineStage.DEDUPLICATION,
            stage_number=4,
            total_stages=6,
            metadata={"entities_before": total_entities},
        )
        step3 = ExtractionStep(step_name="deduplication", started_at=dt_cls.now(UTC))

        deduplicated = await deduplicate_entities(
            all_entities,
            api_key=_get_validated_openai_key(),
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
            relationships=all_relationships,
            enable_coreference=True,
        )

        step3.completed_at = dt_cls.now(UTC)
        activity.add_step(step3)

        entities_after = sum(len(v) for v in deduplicated.values())

        await ws_manager.broadcast_stage_complete(
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
        await ws_manager.broadcast_stage_start(
            job_id=job_id, stage=PipelineStage.VALIDATION, stage_number=5, total_stages=6
        )
        step4 = ExtractionStep(step_name="validation", started_at=dt_cls.now(UTC))

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

        validate_extraction_result(result)

        validator = EntailmentValidator()
        validation_results = validator.validate(result, all_relationships)

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
            result.errors.extend([f"[WARNING] {w.rule_id}: {w.message}" for w in warnings])

        step4.completed_at = dt_cls.now(UTC)
        step4.entities_extracted = len(validation_results)
        activity.add_step(step4)

        await ws_manager.broadcast_stage_complete(
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
        await ws_manager.broadcast_stage_start(
            job_id=job_id, stage=PipelineStage.RDF_GENERATION, stage_number=6, total_stages=6
        )
        step5 = ExtractionStep(step_name="rdf_generation", started_at=dt_cls.now(UTC))

        rdf_content = generate_rdf(result, all_relationships)

        for rel in all_relationships:
            validate_relationship_for_persistence(rel)

        await ws_manager.broadcast_stage_complete(
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

        output_dir = os.getenv("RDF_OUTPUT_DIR", DEFAULT_RDF_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        rdf_path = f"{output_dir}/{job_id}.ttl"

        with open(rdf_path, "w") as f:
            f.write(rdf_content)

        step5.completed_at = dt_cls.now(UTC)
        activity.add_step(step5)

        activity.output_entities = [e.id for e in result.get_all_entities()]
        activity.output_relationships = [r.id for r in all_relationships]
        activity.complete(rdf_output_path=rdf_path)

        await _set_pipeline_job(
            job_id,
            extraction_status="completed",
            entities_extracted=len(activity.output_entities),
            relationships_extracted=len(activity.output_relationships),
            completed_at=dt_cls.now(UTC) if mark_pipeline_complete else None,
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

        if mark_pipeline_complete:
            await ws_manager.broadcast_pipeline_complete(
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
            completed_at=dt_cls.now(UTC),
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

        await ws_manager.broadcast_error(
            job_id=job_id,
            stage=PipelineStage.RDF_GENERATION,
            error=error_msg,
            recoverable=False,
        )

        await ws_manager.broadcast_pipeline_complete(
            job_id=job_id,
            status="failed",
            entities_extracted=0,
            relationships_extracted=0,
            errors=[error_msg],
        )

        raise


async def run_extraction_deterministic_local(
    job_id: str,
    source_url: str,
    content: str,
    config: dict,
    mark_pipeline_complete: bool = True,
) -> ExtractionArtifacts | None:
    """Run extraction with the local deterministic model."""
    cfg = dict(config)
    cfg["model_version"] = "e2e-local-extraction-model"
    return await run_extraction(
        job_id=job_id,
        source_url=source_url,
        content=content,
        config=cfg,
        mark_pipeline_complete=mark_pipeline_complete,
    )


async def run_extract_and_ingest(
    job_id: str,
    source_url: str,
    content: str,
    config: dict,
) -> None:
    """Run extraction and ingestion in one background pipeline."""
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "run_extract_and_ingest")
        and main_mod.run_extract_and_ingest is not run_extract_and_ingest
    ):
        return await main_mod.run_extract_and_ingest(job_id, source_url, content, config)

    run_extraction_fn = run_extraction
    if main_mod and hasattr(main_mod, "run_extraction"):
        run_extraction_fn = main_mod.run_extraction

    try:
        artifacts = await run_extraction_fn(
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

    client_cls = _get_active_layer3_client_class()
    client = client_cls()
    try:
        healthy = await client.health_check()
    finally:
        await client.close()

    from layer2_extraction.api.ingestion_runner import (
        MAX_INGESTION_RETRIES,
        _attempt_ingestion,
        _queue_for_retry,
    )

    job_store = _get_active_job_store()
    ws_mgr = _get_active_ws_manager()

    if not healthy:
        job = await job_store.get(job_id)
        retry_count = (job.retry_count + 1) if job else 1

        await ws_mgr.broadcast_ingestion_status(
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


async def _quarantine_validation_failure(
    tenant_id: str,
    job_id: str,
    source_url: str,
    source_hash: str,
    payload: str,
    errors: list[str],
    model_version: str = "",
    schema_version: str = "",
    prompt_template_version: str = "",
    reason: str = "persistence_validation_failed",
) -> None:
    """Record an artifact validation failure to quarantine store, respecting test monkeypatching."""
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "_quarantine_validation_failure")
        and main_mod._quarantine_validation_failure is not _quarantine_validation_failure
    ):
        return await main_mod._quarantine_validation_failure(
            tenant_id=tenant_id,
            job_id=job_id,
            source_url=source_url,
            source_hash=source_hash,
            payload=payload,
            errors=errors,
            model_version=model_version,
            schema_version=schema_version,
            prompt_template_version=prompt_template_version,
            reason=reason,
        )

    quarantine_store = _get_active_quarantine_store()
    record = QuarantineRecord(
        quarantine_id=f"q-{uuid4().hex[:12]}",
        job_id=job_id,
        tenant_id=tenant_id,
        source_url=source_url,
        source_hash=source_hash,
        model_version=model_version,
        schema_version=schema_version,
        prompt_template_version=prompt_template_version,
        prompt_template_hash=None,
        payload_json=payload,
        validation_errors=errors,
        reason=reason,
    )
    await quarantine_store.put(record)


__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_RDF_OUTPUT_DIR",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "ExtractionArtifacts",
    "PROGRESS_REPORT_INTERVAL",
    "RELATIONSHIP_CONFIDENCE_OFFSET",
    "StampableEntity",
    "_build_e2e_local_extraction_artifacts",
    "_extractor_factory",
    "_quarantine_validation_failure",
    "_stamp_entity",
    "get_entity_extractor",
    "get_relationship_extractor",
    "prompt_template_hash",
    "prompt_template_version",
    "run_extract_and_ingest",
    "run_extraction",
    "run_extraction_deterministic_local",
]
