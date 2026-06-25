"""ValueOS benchmark and VMRT contract models.

These models mirror the JSON Schema contracts under ``contracts/jsonschema`` and
enforce cross-field invariants that JSON Schema cannot express cleanly.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Industry = Literal["technology", "financial_services", "healthcare", "manufacturing", "retail"]
LifecycleStage = Literal[
    "prospect", "onboarding", "expansion", "renewal", "justify_commit", "realize_expand"
]
ValueType = Literal[
    "cost_reduction", "cost_savings", "revenue_growth", "revenue_uplift", "risk_mitigation"
]


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValueOSMetricTaxonomy(StrictContractModel):
    value_pillar: str = Field(min_length=1)
    functional_domain: str = Field(min_length=1)
    category: str = Field(min_length=1)
    lifecycle_stage: LifecycleStage
    value_type: ValueType


class ValueOSMetricSegmentation(StrictContractModel):
    industry: Industry
    company_size_band: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    maturity_band: str | None = None
    revenue_band: str | None = None


class ValueOSMetricDistribution(StrictContractModel):
    p10: Decimal
    p25: Decimal
    p50: Decimal
    p75: Decimal
    p90: Decimal
    mean: Decimal
    sample_size: int = Field(ge=1)
    std_dev: Decimal | None = Field(default=None, ge=0)
    shape: Literal[
        "normal", "lognormal", "skewed_left", "skewed_right", "bimodal", "unknown"
    ] = "unknown"

    @model_validator(mode="after")
    def validate_percentile_order(self) -> "ValueOSMetricDistribution":
        if not self.p10 <= self.p25 <= self.p50 <= self.p75 <= self.p90:
            raise ValueError("VALUEOS_METRIC_DISTRIBUTION_ORDER_INVALID")
        return self


class ValueOSMetricSource(StrictContractModel):
    source_name: str = Field(min_length=1)
    source_type: Literal[
        "public_benchmark",
        "licensed_research",
        "regulatory_filing",
        "academic_study",
        "proprietary_survey",
        "customer_outcome",
    ]
    publication_year: int = Field(ge=1990)
    license_class: Literal["public", "internal", "licensed_restricted", "partner_anonymized"]
    ingested_at: datetime
    confidence_score: Decimal = Field(ge=0, le=1)
    url: str | None = None
    extraction_method: str | None = None
    caveats: list[str] = Field(default_factory=list)


class ValueOSMetricGovernance(StrictContractModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    vintage: str = Field(pattern=r"^\d{4}(?:Q[1-4])?$")
    status: Literal["draft", "active", "deprecated", "rejected"]
    owner: str = Field(min_length=1)
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    stale_after: date | None = None
    deprecation_reason: str | None = None


class ValueOSBenchmarkMetric(StrictContractModel):
    metric_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    taxonomy: ValueOSMetricTaxonomy
    segmentation: ValueOSMetricSegmentation
    distribution: ValueOSMetricDistribution
    provenance: list[ValueOSMetricSource] = Field(min_length=1)
    governance: ValueOSMetricGovernance


class VMRTAmount(StrictContractModel):
    value: Decimal
    unit: str = Field(min_length=1)


class VMRTPain(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    persona_owner: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "critical"]


class VMRTCapability(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    pain_ids: list[str] = Field(min_length=1)


class VMRTOutcome(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    capability_ids: list[str] = Field(min_length=1)


class VMRTKPI(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1)
    outcome_ids: list[str] = Field(min_length=1)
    baseline: VMRTAmount
    target: VMRTAmount
    timeframe: str = Field(min_length=1)
    benchmark_metric_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class VMRTSensitivityBounds(StrictContractModel):
    low: Decimal
    high: Decimal

    @model_validator(mode="after")
    def validate_bounds(self) -> "VMRTSensitivityBounds":
        if self.low > self.high:
            raise ValueError("VMRT_SENSITIVITY_BOUNDS_INVALID")
        return self


class VMRTFinancialImpact(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    kpi_ids: list[str] = Field(min_length=1)
    formula: str = Field(min_length=1)
    inputs: dict[str, int | float | str | bool] = Field(default_factory=dict)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    time_horizon: str = Field(min_length=1)
    sensitivity_bounds: VMRTSensitivityBounds


class VMRTReasoning(StrictContractModel):
    natural_language_chain: list[str] = Field(min_length=6, max_length=12)


class VMRTAssumption(StrictContractModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    assumption_type: Literal["benchmark", "customer_input", "expert_estimate", "model_inference"]
    confidence: Decimal = Field(ge=0, le=1)
    approval_state: Literal["pending", "approved", "rejected", "not_required"]
    source: str | None = None


class VMRTQualityScores(StrictContractModel):
    logical_coherence: Decimal = Field(ge=0, le=5)
    benchmark_alignment: Decimal = Field(ge=0, le=5)
    financial_rigor: Decimal = Field(ge=0, le=5)
    story_clarity: Decimal = Field(ge=0, le=5)
    overall: Decimal = Field(ge=0, le=5)
    reviewer: str | None = None
    reviewed_at: datetime | None = None


class ValueModelingReasoningTrace(StrictContractModel):
    trace_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    industry: Industry
    persona: str = Field(min_length=1)
    value_type: ValueType
    lifecycle_stage: LifecycleStage
    product_category: str = Field(min_length=1)
    scope: Literal["tenant", "global_system"]
    pains: list[VMRTPain] = Field(min_length=2, max_length=4)
    capabilities: list[VMRTCapability] = Field(min_length=2, max_length=4)
    outcomes: list[VMRTOutcome] = Field(min_length=2, max_length=3)
    kpis: list[VMRTKPI] = Field(min_length=2, max_length=4)
    financial_impacts: list[VMRTFinancialImpact] = Field(min_length=2, max_length=4)
    reasoning: VMRTReasoning
    assumptions: list[VMRTAssumption] = Field(default_factory=list)
    quality_scores: VMRTQualityScores

    @model_validator(mode="after")
    def validate_trace_graph(self) -> "ValueModelingReasoningTrace":
        pain_ids = _unique_ids("pain", [pain.id for pain in self.pains])
        capability_ids = _unique_ids("capability", [capability.id for capability in self.capabilities])
        outcome_ids = _unique_ids("outcome", [outcome.id for outcome in self.outcomes])
        kpi_ids = _unique_ids("kpi", [kpi.id for kpi in self.kpis])
        _unique_ids("financial_impact", [impact.id for impact in self.financial_impacts])

        for capability in self.capabilities:
            _require_known_refs(
                source=f"capability:{capability.id}",
                target_type="pain",
                refs=capability.pain_ids,
                allowed=pain_ids,
            )

        for outcome in self.outcomes:
            _require_known_refs(
                source=f"outcome:{outcome.id}",
                target_type="capability",
                refs=outcome.capability_ids,
                allowed=capability_ids,
            )

        for kpi in self.kpis:
            _require_known_refs(
                source=f"kpi:{kpi.id}",
                target_type="outcome",
                refs=kpi.outcome_ids,
                allowed=outcome_ids,
            )

        for impact in self.financial_impacts:
            _require_known_refs(
                source=f"financial_impact:{impact.id}",
                target_type="kpi",
                refs=impact.kpi_ids,
                allowed=kpi_ids,
            )
            if not _impact_traces_to_pain(impact, self.kpis, self.outcomes, self.capabilities):
                raise ValueError(f"VMRT_IMPACT_CHAIN_INCOMPLETE:{impact.id}")

        return self


def _unique_ids(entity_type: str, ids: list[str]) -> set[str]:
    unique_ids = set(ids)
    if len(unique_ids) != len(ids):
        raise ValueError(f"VMRT_DUPLICATE_{entity_type.upper()}_ID")
    return unique_ids


def _require_known_refs(
    *, source: str, target_type: str, refs: list[str], allowed: set[str]
) -> None:
    missing = sorted(set(refs) - allowed)
    if missing:
        raise ValueError(f"VMRT_UNKNOWN_{target_type.upper()}_REF:{source}:{','.join(missing)}")


def _impact_traces_to_pain(
    impact: VMRTFinancialImpact,
    kpis: list[VMRTKPI],
    outcomes: list[VMRTOutcome],
    capabilities: list[VMRTCapability],
) -> bool:
    kpis_by_id = {kpi.id: kpi for kpi in kpis}
    outcomes_by_id = {outcome.id: outcome for outcome in outcomes}
    capabilities_by_id = {capability.id: capability for capability in capabilities}

    for kpi_id in impact.kpi_ids:
        for outcome_id in kpis_by_id[kpi_id].outcome_ids:
            outcome = outcomes_by_id[outcome_id]
            for capability_id in outcome.capability_ids:
                capability = capabilities_by_id[capability_id]
                if capability.pain_ids:
                    return True
    return False


def validate_valueos_benchmark_metric(payload: dict[str, Any]) -> ValueOSBenchmarkMetric:
    """Validate a benchmark metric payload against ValueOS runtime invariants."""
    return ValueOSBenchmarkMetric.model_validate(payload)


def validate_vmrt_trace(payload: dict[str, Any]) -> ValueModelingReasoningTrace:
    """Validate a VMRT trace payload against runtime linkage invariants."""
    return ValueModelingReasoningTrace.model_validate(payload)

