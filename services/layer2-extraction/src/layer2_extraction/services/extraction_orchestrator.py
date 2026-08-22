"""Extraction pipeline orchestrator and artifact models for Layer 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog
from value_fabric.shared.audit import AuditAction, emit_audit_event

from layer2_extraction.domain.chunking import Chunk, create_chunks
from layer2_extraction.domain.deduplication import Deduplicator
from layer2_extraction.domain.models import (
    ChallengeEntity,
    ExtractionResult,
    FinancialMetricEntity,
    GoalEntity,
    InitiativeEntity,
    KPIEntity,
    ProvenanceMetadata,
    RelationshipEntity,
    SystemEntity,
)
from layer2_extraction.domain.semantic_alignment import SemanticAligner
from layer2_extraction.domain.validation import (
    SchemaValidator,
    validate_extraction_result,
    validate_relationship_for_persistence,
)
from layer2_extraction.extraction.llm_extractor import LLMExtractor
from layer2_extraction.generation.rdf_generator import generate_rdf
from layer2_extraction.integration.job_store import JobStore
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.quarantine_store import (
    QuarantineRecord,
    QuarantineStore,
)
from layer2_extraction.observability.websocket import WebSocketManager

logger = structlog.get_logger(__name__)


class StampableEntity(Protocol):
    """Protocol for entities that can receive provenance metadata."""

    tenant_id: str
    provenance: ProvenanceMetadata | None


def _stamp_entity(
    entity: StampableEntity,
    tenant_id: str,
    source_url: str,
    source_hash: str,
    model_version: str,
    prompt_template_version: str,
    extraction_timestamp: datetime,
) -> None:
    """Stamp tenant and provenance metadata in-place on an entity."""
    entity.tenant_id = tenant_id
    if getattr(entity, "provenance", None) is None:
        entity.provenance = ProvenanceMetadata(
            source_url=source_url,
            source_hash=source_hash,
            model_version=model_version,
            prompt_template_version=prompt_template_version,
            extraction_timestamp=extraction_timestamp,
        )


@dataclass
class ExtractionArtifacts:
    """Domain artifacts produced across extraction stages."""

    chunks: list[Chunk] = field(default_factory=list)
    entities: list[Any] = field(default_factory=list)
    relationships: list[RelationshipEntity] = field(default_factory=list)
    rdf_triples: str = ""
    errors: list[str] = field(default_factory=list)
    quality_score: float = 0.0


def serialize_artifacts(artifacts: ExtractionArtifacts) -> dict[str, Any]:
    """Serialize ExtractionArtifacts to JSON-compatible dict."""
    return {
        "entities": [e.model_dump(mode="json") for e in artifacts.entities],
        "relationships": [r.model_dump(mode="json") for r in artifacts.relationships],
        "rdf_triples": artifacts.rdf_triples,
        "errors": artifacts.errors,
        "quality_score": artifacts.quality_score,
    }


def deserialize_artifacts(data: dict[str, Any]) -> ExtractionArtifacts:
    """Deserialize ExtractionArtifacts from a dict."""
    raw_entities = data.get("entities", [])
    entities: list[Any] = []
    entity_classes = [
        GoalEntity,
        InitiativeEntity,
        ChallengeEntity,
        KPIEntity,
        FinancialMetricEntity,
        SystemEntity,
    ]
    for raw in raw_entities:
        for cls in entity_classes:
            try:
                entities.append(cls.model_validate(raw))
                break
            except Exception:
                continue

    raw_relationships = data.get("relationships", [])
    relationships = [RelationshipEntity.model_validate(r) for r in raw_relationships]

    return ExtractionArtifacts(
        chunks=[],
        entities=entities,
        relationships=relationships,
        rdf_triples=data.get("rdf_triples", ""),
        errors=data.get("errors", []),
        quality_score=data.get("quality_score", 0.0),
    )


def build_e2e_local_extraction_artifacts(
    *,
    text: str,
    tenant_id: str,
    source_url: str,
    source_hash: str,
    model_version: str,
    prompt_template_version: str,
    extraction_timestamp: datetime,
) -> ExtractionArtifacts:
    """Construct complete deterministic domain entities/relationships for tests."""
    g1 = GoalEntity(
        id=str(uuid4()),
        name="Deterministic Local Extraction Goal",
        description="Deterministic local extraction artifact for test environments",
        timeframe="FY2026",
        source_url=source_url,
    )
    init1 = InitiativeEntity(
        id=str(uuid4()),
        name="Deterministic Ingestion Automation",
        description="Automated pipeline ingestion initiative",
        status="active",
        source_url=source_url,
    )
    chal1 = ChallengeEntity(
        id=str(uuid4()),
        name="Integration Latency Constraint",
        description="Downstream pipeline latency bottlenecks",
        severity="medium",
        source_url=source_url,
    )
    kpi1 = KPIEntity(
        id=str(uuid4()),
        name="Pipeline Throughput KPI",
        current_value=99.5,
        target_value=99.9,
        unit="percent",
        source_url=source_url,
    )
    fin1 = FinancialMetricEntity(
        id=str(uuid4()),
        name="Operational Cost Savings",
        value=150000.0,
        unit="USD",
        source_url=source_url,
    )
    sys1 = SystemEntity(
        id=str(uuid4()),
        name="Layer3 Graph Store",
        system_type="KnowledgeGraph",
        source_url=source_url,
    )

    entities: list[Any] = [g1, init1, chal1, kpi1, fin1, sys1]
    for entity in entities:
        _stamp_entity(
            entity,
            tenant_id=tenant_id,
            source_url=source_url,
            source_hash=source_hash,
            model_version=model_version,
            prompt_template_version=prompt_template_version,
            extraction_timestamp=extraction_timestamp,
        )

    r1 = RelationshipEntity(
        id=str(uuid4()),
        tenant_id=tenant_id,
        source_id=init1.id,
        source_type="Initiative",
        target_id=g1.id,
        target_type="Goal",
        relationship_type="SUPPORTS",
        confidence=0.95,
        source_url=source_url,
        provenance=ProvenanceMetadata(
            source_url=source_url,
            source_hash=source_hash,
            model_version=model_version,
            prompt_template_version=prompt_template_version,
            extraction_timestamp=extraction_timestamp,
        ),
    )
    r2 = RelationshipEntity(
        id=str(uuid4()),
        tenant_id=tenant_id,
        source_id=chal1.id,
        source_type="Challenge",
        target_id=g1.id,
        target_type="Goal",
        relationship_type="IMPACTS",
        confidence=0.9,
        source_url=source_url,
        provenance=ProvenanceMetadata(
            source_url=source_url,
            source_hash=source_hash,
            model_version=model_version,
            prompt_template_version=prompt_template_version,
            extraction_timestamp=extraction_timestamp,
        ),
    )
    relationships = [r1, r2]

    rdf_triples = generate_rdf(entities, relationships, tenant_id=tenant_id)
    chunks = create_chunks(text, max_chunk_size=1000, overlap=100)

    return ExtractionArtifacts(
        chunks=chunks,
        entities=entities,
        relationships=relationships,
        rdf_triples=rdf_triples,
        errors=[],
        quality_score=0.98,
    )


class ExtractionPipelineOrchestrator:
    """Orchestrates 6-stage extraction and optional ingestion into Layer 3."""

    def __init__(
        self,
        *,
        job_store: JobStore,
        pending_ingestion_store: PendingIngestionStore,
        quarantine_store: QuarantineStore,
        ws_manager: WebSocketManager,
        l3_client: Layer3KnowledgeClient,
        quarantine_validation_failure_fn: Callable[..., Awaitable[QuarantineRecord]],
        attempt_ingestion_fn: Callable[..., Awaitable[bool]],
        set_pipeline_job_fn: Callable[..., Awaitable[None]],
    ) -> None:
        self.job_store = job_store
        self.pending_ingestion_store = pending_ingestion_store
        self.quarantine_store = quarantine_store
        self.ws_manager = ws_manager
        self.l3_client = l3_client
        self.quarantine_validation_failure_fn = quarantine_validation_failure_fn
        self.attempt_ingestion_fn = attempt_ingestion_fn
        self.set_pipeline_job_fn = set_pipeline_job_fn

    async def run_extraction(
        self,
        job_id: str,
        text: str,
        source_url: str,
        source_hash: str,
        tenant_id: str,
        *,
        model_version: str = "gpt-4o",
        schema_version: str = "1.0.0",
        prompt_template_version: str = "v1.0",
        prompt_template_hash: str | None = None,
        use_deterministic_local_extraction: bool = False,
    ) -> ExtractionArtifacts:
        """Run the full 6-stage extraction pipeline."""
        artifacts = ExtractionArtifacts()
        extraction_timestamp = datetime.now(UTC)

        try:
            logger.info(
                "Starting extraction pipeline",
                tenant_id=tenant_id,
                job_id=job_id,
                source_url=source_url,
            )

            # Stage 1: Chunking
            await self.set_pipeline_job_fn(job_id, extraction_status="in_progress")
            await self.ws_manager.broadcast_progress(
                job_id,
                {"step": "chunking", "progress": 0.1, "chunks": 0},
            )
            chunks = create_chunks(text, max_chunk_size=1000, overlap=100)
            artifacts.chunks = chunks

            # Stage 2: Entity & Relationship Extraction
            await self.ws_manager.broadcast_progress(
                job_id,
                {"step": "extracting", "progress": 0.3, "chunks": len(chunks)},
            )
            all_entities: list[Any] = []
            all_relationships: list[RelationshipEntity] = []

            if use_deterministic_local_extraction:
                e2e_local = build_e2e_local_extraction_artifacts(
                    text=text,
                    tenant_id=tenant_id,
                    source_url=source_url,
                    source_hash=source_hash,
                    model_version=model_version,
                    prompt_template_version=prompt_template_version,
                    extraction_timestamp=extraction_timestamp,
                )
                artifacts.chunks = e2e_local.chunks
                artifacts.entities = e2e_local.entities
                artifacts.relationships = e2e_local.relationships
                artifacts.rdf_triples = e2e_local.rdf_triples
                artifacts.errors = e2e_local.errors
                artifacts.quality_score = e2e_local.quality_score
            else:
                extractor = LLMExtractor()
                for i, chunk in enumerate(chunks):
                    try:
                        chunk_res = await extractor.extract_from_chunk(
                            chunk.content,
                            tenant_id=tenant_id,
                            source_url=source_url,
                            source_hash=source_hash,
                            model_version=model_version,
                            prompt_template_version=prompt_template_version,
                        )
                        chunk_entities = (
                            chunk_res.goals
                            + chunk_res.initiatives
                            + chunk_res.challenges
                            + chunk_res.kpis
                            + chunk_res.financial_metrics
                            + chunk_res.systems
                        )
                        for entity in chunk_entities:
                            _stamp_entity(
                                entity,
                                tenant_id=tenant_id,
                                source_url=source_url,
                                source_hash=source_hash,
                                model_version=model_version,
                                prompt_template_version=prompt_template_version,
                                extraction_timestamp=extraction_timestamp,
                            )
                        for rel in chunk_res.relationships:
                            rel.tenant_id = tenant_id
                            if rel.provenance is None:
                                rel.provenance = ProvenanceMetadata(
                                    source_url=source_url,
                                    source_hash=source_hash,
                                    model_version=model_version,
                                    prompt_template_version=prompt_template_version,
                                    extraction_timestamp=extraction_timestamp,
                                )
                        all_entities.extend(chunk_entities)
                        all_relationships.extend(chunk_res.relationships)
                    except Exception as chunk_exc:
                        err_msg = f"Extraction failed for chunk {i}: {chunk_exc}"
                        logger.warning(err_msg, job_id=job_id, tenant_id=tenant_id)
                        artifacts.errors.append(err_msg)

                # Stage 3: Semantic Alignment
                await self.ws_manager.broadcast_progress(
                    job_id,
                    {
                        "step": "aligning",
                        "progress": 0.5,
                        "entities": len(all_entities),
                    },
                )
                aligner = SemanticAligner()
                aligned_entities = await aligner.align_entities(all_entities)

                # Stage 4: Deduplication
                await self.ws_manager.broadcast_progress(
                    job_id,
                    {
                        "step": "deduplicating",
                        "progress": 0.65,
                        "entities": len(aligned_entities),
                    },
                )
                deduplicator = Deduplicator()
                unique_entities, unique_relationships = deduplicator.deduplicate(
                    aligned_entities, all_relationships
                )

                # Stage 5: Validation
                await self.ws_manager.broadcast_progress(
                    job_id,
                    {
                        "step": "validating",
                        "progress": 0.75,
                        "entities": len(unique_entities),
                    },
                )
                validator = SchemaValidator()
                ext_result = ExtractionResult(
                    tenant_id=tenant_id,
                    goals=[e for e in unique_entities if isinstance(e, GoalEntity)],
                    initiatives=[
                        e for e in unique_entities if isinstance(e, InitiativeEntity)
                    ],
                    challenges=[
                        e for e in unique_entities if isinstance(e, ChallengeEntity)
                    ],
                    kpis=[e for e in unique_entities if isinstance(e, KPIEntity)],
                    financial_metrics=[
                        e
                        for e in unique_entities
                        if isinstance(e, FinancialMetricEntity)
                    ],
                    systems=[e for e in unique_entities if isinstance(e, SystemEntity)],
                    relationships=unique_relationships,
                )
                validation_result = validator.validate(ext_result)
                artifacts.quality_score = validation_result.quality_score

                if not validation_result.is_valid:
                    artifacts.errors.extend(validation_result.errors)
                    await self.quarantine_validation_failure_fn(
                        tenant_id=tenant_id,
                        job_id=job_id,
                        source_url=source_url,
                        source_hash=source_hash,
                        payload=text,
                        errors=validation_result.errors,
                        model_version=model_version,
                        schema_version=schema_version,
                        prompt_template_version=prompt_template_version,
                        prompt_template_hash=prompt_template_hash,
                    )
                    await self.ws_manager.broadcast_progress(
                        job_id,
                        {
                            "step": "quarantined",
                            "progress": 1.0,
                            "errors": validation_result.errors,
                        },
                    )
                    return artifacts

                # Stage 6: RDF Generation
                rdf_triples = generate_rdf(
                    unique_entities, unique_relationships, tenant_id=tenant_id
                )

                artifacts.entities = unique_entities
                artifacts.relationships = unique_relationships
                artifacts.rdf_triples = rdf_triples

            # Mark extraction completed
            await self.set_pipeline_job_fn(
                job_id,
                extraction_status="completed",
                entities_extracted=len(artifacts.entities),
                relationships_extracted=len(artifacts.relationships),
                quality_score=artifacts.quality_score,
            )

            try:
                emit_audit_event(
                    AuditAction.EXTRACTION_COMPLETED,
                    tenant_id=UUID(tenant_id) if tenant_id else None,
                    resource_type="ExtractionJob",
                    resource_id=job_id,
                    outcome="success",
                    details={
                        "entities_extracted": len(artifacts.entities),
                        "relationships_extracted": len(artifacts.relationships),
                        "quality_score": artifacts.quality_score,
                    },
                )
            except Exception:
                pass

            return artifacts

        except Exception as exc:
            err_msg = f"Extraction pipeline unhandled error: {exc}"
            logger.exception(
                "Extraction unhandled exception",
                job_id=job_id,
                tenant_id=tenant_id,
                error=str(exc),
            )
            artifacts.errors.append(err_msg)
            completed_at = datetime.now(UTC)
            await self.set_pipeline_job_fn(
                job_id,
                extraction_status="failed",
                last_error=err_msg,
                completed_at=completed_at,
            )
            await self.ws_manager.broadcast_progress(
                job_id,
                {"step": "failed", "progress": 1.0, "error": err_msg},
            )
            return artifacts

    async def run_extract_and_ingest(
        self,
        job_id: str,
        text: str,
        source_url: str,
        source_hash: str,
        tenant_id: str,
        *,
        model_version: str = "gpt-4o",
        schema_version: str = "1.0.0",
        prompt_template_version: str = "v1.0",
        prompt_template_hash: str | None = None,
        use_deterministic_local_extraction: bool = False,
    ) -> ExtractionArtifacts:
        """Run full extraction pipeline followed by immediate Layer 3 ingestion."""
        artifacts = await self.run_extraction(
            job_id=job_id,
            text=text,
            source_url=source_url,
            source_hash=source_hash,
            tenant_id=tenant_id,
            model_version=model_version,
            schema_version=schema_version,
            prompt_template_version=prompt_template_version,
            prompt_template_hash=prompt_template_hash,
            use_deterministic_local_extraction=use_deterministic_local_extraction,
        )

        job = await self.job_store.get(job_id)
        if job and job.extraction_status == "quarantined":
            logger.warning(
                "Skipping ingestion for quarantined extraction job",
                job_id=job_id,
                tenant_id=tenant_id,
            )
            return artifacts

        if job and job.extraction_status != "completed":
            logger.warning(
                "Extraction did not complete successfully; skipping immediate ingestion",
                job_id=job_id,
                tenant_id=tenant_id,
                extraction_status=job.extraction_status,
            )
            return artifacts

        await self.attempt_ingestion_fn(
            tenant_id=tenant_id,
            job_id=job_id,
            source_url=source_url,
            artifacts=artifacts,
            retry_count=0,
        )

        return artifacts
