"""Extraction artifact models and deterministic local extraction fixtures."""

from dataclasses import dataclass
from typing import Protocol, TypeVar
from uuid import NAMESPACE_URL, uuid5

from layer2_extraction.extraction.entity_id import compute_deterministic_id
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
