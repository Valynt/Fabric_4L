from __future__ import annotations

"""
Canonical Artifact Contracts for Value Fabric Layer 4 Agents.

These Pydantic v2 models define the typed data contracts that flow between
agents. They are the authoritative source of truth for:

  1. What data each agent produces and consumes
  2. The canonical field names (resolving label/name/canonicalName drift)
  3. The Variable Registry schema (fixing the test triad)
  4. Provenance and confidence tracking on every entity

Design principles:
  - Python-first (Pydantic v2), not TypeScript — matches the FastAPI stack
  - Field aliases for backward compatibility with existing Neo4j property names
  - Incremental adoption: agents can produce partial artifacts and fill fields
    over time; only 'required' fields are enforced at validation boundaries
  - No circular imports: this module has zero internal dependencies
"""


import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EntitySource(str, Enum):
    """How an entity entered the system."""

    WEBSITE_EXTRACTED = "WEBSITE_EXTRACTED"
    USER_INPUT = "USER_INPUT"
    CRM_SYNCED = "CRM_SYNCED"
    BENCHMARK = "BENCHMARK"
    MEETING_TRANSCRIPT = "MEETING_TRANSCRIPT"
    INFERRED = "INFERRED"


# Confidence score thresholds (must match pack_variable_loader.py)
CONFIDENCE_HIGH_THRESHOLD = 0.85
CONFIDENCE_MEDIUM_THRESHOLD = 0.60


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"  # >= CONFIDENCE_HIGH_THRESHOLD
    MEDIUM = "MEDIUM"  # CONFIDENCE_MEDIUM_THRESHOLD – CONFIDENCE_HIGH_THRESHOLD
    LOW = "LOW"  # < CONFIDENCE_MEDIUM_THRESHOLD


class GateStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class VariableSource(str, Enum):
    PACK_DEFINED = "PACK_DEFINED"
    USER_PROVIDED = "USER_PROVIDED"
    CRM_FIELD = "CRM_FIELD"
    BENCHMARK = "BENCHMARK"
    INFERRED = "INFERRED"
    CALCULATED = "CALCULATED"


# ---------------------------------------------------------------------------
# Core Schema — EntityRef
# ---------------------------------------------------------------------------


class ConfidenceScore(BaseModel):
    """Confidence metadata attached to every extracted entity."""

    model_config = ConfigDict(populate_by_name=True)

    score: float = Field(ge=0.0, le=1.0, description="0.0–1.0 confidence score")
    level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    basis: str = Field(
        default="", description="Human-readable explanation of the score"
    )

    @field_validator("level", mode="before")
    @classmethod
    def derive_level(cls, v: Any, info: Any) -> ConfidenceLevel:
        # Allow explicit override; otherwise derive from score in model_post_init
        if isinstance(v, ConfidenceLevel):
            return v
        return v  # Will be set by model_post_init if needed

    def model_post_init(self, __context: Any) -> None:
        # Use shared thresholds (keep in sync with pack_variable_loader.py)
        if self.score >= CONFIDENCE_HIGH_THRESHOLD:
            object.__setattr__(self, "level", ConfidenceLevel.HIGH)
        elif self.score >= CONFIDENCE_MEDIUM_THRESHOLD:
            object.__setattr__(self, "level", ConfidenceLevel.MEDIUM)
        else:
            object.__setattr__(self, "level", ConfidenceLevel.LOW)


class ProvenanceRecord(BaseModel):
    """Tracks where an entity came from."""

    model_config = ConfigDict(populate_by_name=True)

    origin_url: str | None = Field(default=None, alias="source_url")
    extractor_version: str | None = Field(default=None, alias="extracted_by")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    llm_model: str | None = None
    session_id: str | None = None  # e.g. Recall.ai meeting session


class EntityRef(BaseModel):
    """
    Canonical entity reference — the single schema for all entity pointers.

    Replaces the ad-hoc mix of:
      - GraphNode: { name, entity_type }
      - Layer 3 API: { name, entity_type }
      - Frontend: { displayName, nodeType }

    Migration aliases allow reading from existing Neo4j properties:
      EntityRef(name="Acme Corp", entity_type="Company")  ← reads old fields
      entity.canonicalName  → "Acme Corp"                 ← canonical access
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # THE canonical name field — resolves label/name/displayName drift
    canonical_name: str = Field(
        alias="name",
        description="Normalized canonical name of the entity",
    )

    # THE canonical type field — resolves type/entity_type/nodeType drift
    entity_type: str = Field(
        description="Entity type from the Value Fabric ontology",
    )

    source: EntitySource = EntitySource.WEBSITE_EXTRACTED
    provenance: ProvenanceRecord | None = None
    confidence: ConfidenceScore | None = None

    # Backward-compatibility: expose canonicalName as a property
    @property
    def canonicalName(self) -> str:  # noqa: N802 — matches TypeScript contract name
        return self.canonical_name


# ---------------------------------------------------------------------------
# Artifact 1: ContextArtifact
# Owned by: ContextExtractionAgent
# ---------------------------------------------------------------------------


class ExtractionSource(BaseModel):
    url: str
    fetch_method: Literal["HTTPX", "STAGEHAND"] = "HTTPX"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status_code: int | None = None
    content_hash: str | None = None


class Stakeholder(BaseModel):
    entity_ref: EntityRef
    role: str = ""
    pain_points: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    influence_level: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class PainPoint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    affected_stakeholders: list[str] = Field(default_factory=list)  # EntityRef IDs
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: ConfidenceScore | None = None


class CustomerProfile(BaseModel):
    company: EntityRef
    industry: EntityRef | None = None
    segment: str | None = None
    employee_count: int | None = None
    annual_revenue_usd: Decimal | None = None
    geography: str | None = None
    tech_stack: list[EntityRef] = Field(default_factory=list)


class ContextArtifact(BaseModel):
    """
    Output of ContextExtractionAgent.
    Captures everything known about the customer before value modeling begins.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Artifact identity
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: Literal["ContextArtifact"] = "ContextArtifact"
    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["ContextExtractionAgent"] = "ContextExtractionAgent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Tenant context
    tenant_id: str
    workspace_id: str
    account_id: str | None = None

    # Core content
    customer_profile: CustomerProfile
    stakeholder_map: list[Stakeholder] = Field(default_factory=list)
    pain_points: list[PainPoint] = Field(default_factory=list)
    extraction_sources: list[ExtractionSource] = Field(default_factory=list)

    # Quality gate
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def is_ready_for_value_modeling(self) -> bool:
        """Gate: must have ≥3 pain points with evidence before proceeding."""
        evidenced = [p for p in self.pain_points if p.evidence_quotes]
        return len(evidenced) >= 3 and self.completeness_score >= 0.7


# ---------------------------------------------------------------------------
# Artifact 2: ValueModelArtifact
# Owned by: ValueModelAgent
# ---------------------------------------------------------------------------


class VariableRegistryEntry(BaseModel):
    """
    A single variable in the canonical Variable Registry.
    This is the Pydantic equivalent of the TypeScript VariableEntry interface.
    Bridges pack variables.json → Neo4j Variable Registry → agent state.
    """

    variable_id: str
    canonical_name: str = Field(alias="canonicalName")
    name: str  # Human-readable display name
    source: VariableSource = VariableSource.PACK_DEFINED
    data_type: str = "decimal"
    unit: str | None = None
    default_value: Any | None = None
    resolved_value: Any | None = None
    confidence: ConfidenceScore | None = None
    used_in_formulas: list[str] = Field(default_factory=list)
    used_in_packs: list[str] = Field(default_factory=list)
    provenance: ProvenanceRecord | None = None

    model_config = ConfigDict(populate_by_name=True)


class VariableRegistry(BaseModel):
    """
    The authoritative source of truth for all variables in a value model.
    Fixes: test_pack_variables_loadable, test_formula_variable_references_valid,
           test_manifest_variable_counts
    """

    variables: list[VariableRegistryEntry] = Field(default_factory=list)
    last_validated_at: datetime | None = None
    validation_errors: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0

    def get_by_canonical_name(self, name: str) -> VariableRegistryEntry | None:
        return next((v for v in self.variables if v.canonical_name == name), None)

    def get_unresolved_refs(self, formula_variable_refs: list[str]) -> list[str]:
        """Return variable names referenced in formulas but not in registry."""
        known = {v.canonical_name for v in self.variables}
        # Also check variable_id as fallback
        known |= {v.variable_id for v in self.variables}
        return [ref for ref in formula_variable_refs if ref not in known]


class CapabilityValueChain(BaseModel):
    capability: EntityRef
    use_cases: list[EntityRef] = Field(default_factory=list)
    outcomes: list[EntityRef] = Field(default_factory=list)
    value_drivers: list[EntityRef] = Field(default_factory=list)


class ValueDriverEntry(BaseModel):
    driver_ref: EntityRef
    impact_description: str = ""
    evidence_links: list[str] = Field(default_factory=list)  # URLs or ProofPoint IDs
    confidence: ConfidenceScore | None = None


class MetricValue(BaseModel):
    variable_id: str
    label: str
    value: Decimal | None = None
    unit: str = ""
    is_estimated: bool = True
    confidence: ConfidenceScore | None = None


class FinancialModel(BaseModel):
    total_value_usd: Decimal | None = None
    roi_percentage: Decimal | None = None
    payback_months: int | None = None
    metrics: list[MetricValue] = Field(default_factory=list)
    cost_components: list[MetricValue] = Field(default_factory=list)
    calculation_method: str = ""


class Assumption(BaseModel):
    assumption_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    variable_id: str | None = None
    confidence: ConfidenceScore | None = None
    evidence_source: str | None = None
    is_customer_validated: bool = False


class ScenarioAnalysis(BaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str  # e.g. "Conservative", "Base Case", "Optimistic"
    financial_model: FinancialModel
    key_assumptions: list[str] = Field(default_factory=list)  # Assumption IDs


class ValueModelArtifact(BaseModel):
    """
    Output of ValueModelAgent.
    The bridge between customer context and the financial narrative.
    Contains the authoritative Variable Registry.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Artifact identity
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: Literal["ValueModelArtifact"] = "ValueModelArtifact"
    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["ValueModelAgent"] = "ValueModelAgent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Lineage
    context_artifact_id: str  # ContextArtifact.artifact_id
    competitive_intel_artifact_id: str | None = (
        None  # CompetitiveIntelArtifact.artifact_id
    )
    pack_id: str | None = None

    # Tenant context
    tenant_id: str
    workspace_id: str

    # Core content
    capability_chains: list[CapabilityValueChain] = Field(default_factory=list)
    value_drivers: list[ValueDriverEntry] = Field(default_factory=list)
    financial_model: FinancialModel = Field(default_factory=FinancialModel)
    scenario_analyses: list[ScenarioAnalysis] = Field(default_factory=list)
    assumption_registry: list[Assumption] = Field(default_factory=list)

    # THE Variable Registry — authoritative source for test triad
    variable_registry: VariableRegistry = Field(default_factory=VariableRegistry)

    @property
    def is_ready_for_integrity_review(self) -> bool:
        """Gate: must have complete chains and a valid variable registry."""
        return (
            len(self.capability_chains) > 0
            and self.variable_registry.is_valid
            and self.financial_model.total_value_usd is not None
        )


# ---------------------------------------------------------------------------
# Artifact 3: IntegrityArtifact
# Owned by: IntegrityAgent
# ---------------------------------------------------------------------------


class AssumptionAuditEntry(BaseModel):
    assumption_id: str
    statement: str
    challenge: str  # The IntegrityAgent's challenge question
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "NEEDS_EVIDENCE", "FLAGGED"]
    confidence: ConfidenceScore | None = None
    suggested_fix: str | None = None


class EvidenceAssessment(BaseModel):
    claim: str
    evidence_sources: list[str] = Field(default_factory=list)
    evidence_quality: Literal["STRONG", "MODERATE", "WEAK", "MISSING"]
    notes: str = ""


class GateResult(BaseModel):
    gate_id: str
    gate_name: str
    status: GateStatus
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    message: str = ""
    blocking: bool = True  # If True, NarrativeAgent cannot proceed if FAILED


class IntegrityArtifact(BaseModel):
    """
    Output of IntegrityAgent.
    Independent challenge layer — audits ValueModelArtifact before narrative generation.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Artifact identity
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: Literal["IntegrityArtifact"] = "IntegrityArtifact"
    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["IntegrityAgent"] = "IntegrityAgent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Lineage
    value_model_artifact_id: str

    # Audit results
    assumption_audit: list[AssumptionAuditEntry] = Field(default_factory=list)
    evidence_assessment: list[EvidenceAssessment] = Field(default_factory=list)
    gate_results: list[GateResult] = Field(default_factory=list)

    # Overall verdict
    overall_confidence: ConfidenceScore | None = None
    defensibility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reviewer_notes: str = ""

    @property
    def all_critical_gates_passed(self) -> bool:
        return all(
            g.status == GateStatus.PASSED for g in self.gate_results if g.blocking
        )

    @property
    def is_ready_for_narrative(self) -> bool:
        return self.all_critical_gates_passed


# ---------------------------------------------------------------------------
# Artifact 4: NarrativeArtifact
# Owned by: NarrativeAgent
# ---------------------------------------------------------------------------


class ExecutiveSummary(BaseModel):
    headline: str = ""
    value_statement: str = ""
    top_three_outcomes: list[str] = Field(default_factory=list)
    recommended_next_step: str = ""


class StakeholderVersion(BaseModel):
    stakeholder_role: str
    persona_ref: EntityRef | None = None
    tailored_narrative: str = ""
    key_messages: list[str] = Field(default_factory=list)
    objection_responses: list[dict[str, str]] = Field(default_factory=list)


class RealizationMilestone(BaseModel):
    milestone_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    target_month: int  # Months from contract start
    value_unlocked_usd: Decimal | None = None
    success_criteria: list[str] = Field(default_factory=list)


class NarrativeArtifact(BaseModel):
    """
    Output of NarrativeAgent.
    The final, audience-ready business case. Read-only consumer of
    ValueModelArtifact and IntegrityArtifact — cannot modify the model.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Artifact identity
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: Literal["NarrativeArtifact"] = "NarrativeArtifact"
    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["NarrativeAgent"] = "NarrativeAgent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Lineage
    value_model_artifact_id: str
    integrity_artifact_id: str
    competitive_intel_artifact_id: str | None = (
        None  # CompetitiveIntelArtifact.artifact_id
    )

    # Core output
    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
    stakeholder_versions: list[StakeholderVersion] = Field(default_factory=list)
    realization_plan: list[RealizationMilestone] = Field(default_factory=list)
    expansion_opportunities: list[str] = Field(default_factory=list)

    # Export metadata
    generated_formats: list[Literal["PDF", "PPTX", "GOOGLE_SLIDES", "HTML"]] = Field(
        default_factory=list
    )
    last_exported_at: datetime | None = None


# ---------------------------------------------------------------------------
# Artifact 5: CompetitiveIntelArtifact
# Owned by: CompetitiveIntelAgent
#
# Design principle (from framework spec):
#   "Competitive intel in a value model is evidence about alternative choices
#    that changes the economic case."
#
# A competitive fact belongs in this artifact only if it affects:
#   - value magnitude   (economic differences)
#   - value timing      (time-to-value differences)
#   - value confidence  (proof quality, reference depth)
#   - value risk        (execution risk, vendor lock-in, compliance exposure)
# ---------------------------------------------------------------------------


class CompetitiveBaseline(str, Enum):
    """The four real competitors every value model must evaluate against."""

    STATUS_QUO = "STATUS_QUO"  # Doing nothing — cost of inaction
    INCUMBENT = "INCUMBENT"  # Existing vendor, spreadsheet, or workflow
    ALTERNATIVE_VENDOR = "ALTERNATIVE_VENDOR"  # Direct category competitor
    INTERNAL_BUILD = "INTERNAL_BUILD"  # DIY / tool assembly by the buyer


class EconomicDifferenceCategory(str, Enum):
    """
    The five dimensions that translate competitive facts into economic argument.
    Maps directly to the five model inputs from the framework spec.
    """

    CAPABILITY_TO_OUTCOME = "CAPABILITY_TO_OUTCOME"
    TIME_TO_VALUE = "TIME_TO_VALUE"
    COST_STRUCTURE = "COST_STRUCTURE"
    RISK_AND_CONFIDENCE = "RISK_AND_CONFIDENCE"
    VALUE_REALIZATION_CONFIDENCE = "VALUE_REALIZATION_CONFIDENCE"


class ProofSource(BaseModel):
    """
    A single piece of evidence supporting a competitive claim.
    Replaces free-text battlecard citations with structured, scoreable proof.
    """

    source_type: Literal[
        "CUSTOMER_REFERENCE",
        "ANALYST_REPORT",
        "WIN_LOSS_DATA",
        "PRODUCT_DOCUMENTATION",
        "MEETING_TRANSCRIPT",
        "BENCHMARK_STUDY",
        "INTERNAL_ESTIMATE",
    ]
    description: str
    url: str | None = None
    published_at: datetime | None = None
    credibility: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class EconomicDifference(BaseModel):
    """
    A single economic difference between Value Fabric and a competitive baseline.

    This is the atomic unit of competitive intelligence in the value model.
    It must be specific enough to affect an assumption, scenario, or confidence
    score in the ValueModelArtifact.
    """

    difference_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: EconomicDifferenceCategory

    # Human-readable description of the difference
    description: str = Field(
        ...,
        description=(
            "Concrete economic statement, e.g. 'Competitor X requires 6 months "
            "of professional services before go-live, delaying time-to-value by "
            "an estimated 180 days relative to Value Fabric.'"
        ),
    )

    # Quantified impact where possible
    impact_direction: Literal["FAVORS_US", "FAVORS_COMPETITOR", "NEUTRAL"] = "FAVORS_US"
    impact_magnitude: str = Field(
        default="",
        description=(
            "Quantified impact where available, e.g. '+$120K year-1 net savings', "
            "'–60 days time-to-value', '2x lower admin burden'."
        ),
    )

    # Which value model components this difference affects
    affects_assumptions: list[str] = Field(
        default_factory=list,
        description="Assumption IDs in ValueModelArtifact.assumption_registry that this difference modifies.",
    )
    affects_scenarios: list[str] = Field(
        default_factory=list,
        description="Scenario IDs in ValueModelArtifact.scenario_analyses that this difference applies to.",
    )

    # Evidence
    proof_sources: list[ProofSource] = Field(default_factory=list)
    confidence: ConfidenceScore | None = None

    # Flag for IntegrityAgent review
    is_unsupported_claim: bool = False
    integrity_flag: str | None = Field(
        default=None,
        description="Populated by IntegrityAgent if the claim lacks sufficient evidence.",
    )


class CompetitiveScenario(BaseModel):
    """
    A side-by-side financial scenario comparing Value Fabric against one baseline.
    Feeds directly into ValueModelArtifact.scenario_analyses.
    """

    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    baseline_type: CompetitiveBaseline
    competitor_name: str | None = None
    label: str  # e.g. "vs. Status Quo", "vs. Incumbent (Salesforce CPQ)"

    # Financial deltas relative to Value Fabric base case
    year1_net_value_delta_usd: Decimal | None = None
    payback_months_delta: int | None = None
    time_to_value_days_delta: int | None = None

    # Confidence in this scenario's assumptions
    scenario_confidence: ConfidenceScore | None = None
    key_assumptions: list[str] = Field(
        default_factory=list,
        description="Free-text assumptions underpinning this scenario.",
    )
    sensitivity_notes: str = Field(
        default="",
        description=(
            "Describe where the model still wins under conservative assumptions "
            "— the 'even if' argument."
        ),
    )


class CompetitiveIntelArtifact(BaseModel):
    """
    Output of CompetitiveIntelAgent.

    First-class input to the value model — not a sidebar battlecard.
    Competitive facts that do not affect value magnitude, timing, confidence,
    or risk are excluded by design.

    Lifecycle:
      1. CompetitiveIntelAgent populates this artifact from Knowledge Graph
         queries, ingested competitor content, and meeting transcripts.
      2. ValueModelAgent reads competitive_baselines to adjust assumptions
         and scenario analyses in ValueModelArtifact.
      3. IntegrityAgent audits is_unsupported_claim flags and scores
         overall competitive defensibility.
      4. NarrativeAgent uses competitive_scenarios to generate the
         'value superiority' framing in the executive readout.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Artifact identity
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: Literal["CompetitiveIntelArtifact"] = "CompetitiveIntelArtifact"
    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["CompetitiveIntelAgent"] = "CompetitiveIntelAgent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Lineage — links back to the context that triggered this analysis
    context_artifact_id: str
    tenant_id: str
    workspace_id: str

    # The four competitive baselines evaluated
    # Each entry covers one alternative option the buyer is considering
    competitive_baselines: list[CompetitiveBaseline] = Field(
        default_factory=list,
        description=(
            "Which of the four baselines were analyzed. A complete value model "
            "evaluates all four: STATUS_QUO, INCUMBENT, ALTERNATIVE_VENDOR, "
            "INTERNAL_BUILD."
        ),
    )

    # Structured economic differences per baseline
    economic_differences: list[EconomicDifference] = Field(default_factory=list)

    # Comparative financial scenarios
    competitive_scenarios: list[CompetitiveScenario] = Field(default_factory=list)

    # Unsupported claims flagged for rep review before executive delivery
    flagged_claims: list[str] = Field(
        default_factory=list,
        description="difference_ids of EconomicDifferences with is_unsupported_claim=True.",
    )

    # Overall competitive confidence score (weighted average across differences)
    overall_competitive_confidence: ConfidenceScore | None = None

    @property
    def is_complete(self) -> bool:
        """
        A complete competitive analysis covers all four baselines and has
        at least one economic difference per baseline.
        """
        baselines_covered = len(self.competitive_baselines) >= 2
        has_differences = len(self.economic_differences) >= 4
        return baselines_covered and has_differences

    @property
    def has_unsupported_claims(self) -> bool:
        return len(self.flagged_claims) > 0

    @property
    def supported_differences(self) -> list[EconomicDifference]:
        """Return only differences with at least one proof source."""
        return [d for d in self.economic_differences if d.proof_sources]

    @property
    def competitive_defensibility_score(self) -> float:
        """
        0.0–1.0 score representing how defensible the competitive argument is.
        Computed as: (supported differences / total differences) weighted by
        proof source credibility.
        """
        if not self.economic_differences:
            return 0.0
        total = len(self.economic_differences)
        supported = len(self.supported_differences)
        unsupported_penalty = len(self.flagged_claims) * 0.1
        base_score = supported / total
        return max(0.0, min(1.0, base_score - unsupported_penalty))
