"""Value Evidence Graph relational models."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .truth_object import Base, JSONBCompat, UUID
from .value_evidence_graph_enums import (
    ApprovalStatus,
    AssumptionType,
    ClaimStatus,
    ClaimType,
    Confidence,
    EvidenceType,
    ImpactLevel,
    ScenarioType,
)


class ValueClaim(Base):
    """Core differentiated object: an evidence-backed, uncertainty-aware value claim."""

    __tablename__ = "value_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, index=True)

    statement: Mapped[str]
    claim_type: Mapped[ClaimType]

    value_unit: Mapped[str]
    conservative_value: Mapped[Decimal]
    expected_value: Mapped[Decimal]
    aggressive_value: Mapped[Decimal]
    confidence: Mapped[Confidence]
    weakest_assumption_id: Mapped[Optional[uuid.UUID]]

    status: Mapped[ClaimStatus]
    maturity_level: Mapped[int]
    version: Mapped[int] = mapped_column(default=1)

    created_by_user_id: Mapped[Optional[str]]
    created_by_workflow_id: Mapped[Optional[str]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    scenario_id: Mapped[Optional[uuid.UUID]]
    truth_object_id: Mapped[Optional[uuid.UUID]]


class Scenario(Base):
    """A set of assumption overrides applied to a formula."""

    __tablename__ = "value_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    case_id: Mapped[Optional[uuid.UUID]]

    name: Mapped[str]
    scenario_type: Mapped[ScenarioType]

    formula_id: Mapped[uuid.UUID]
    assumption_overrides: Mapped[dict] = mapped_column(JSONBCompat, default=dict)
    outputs: Mapped[dict] = mapped_column(JSONBCompat, default=dict)
    sensitivity_ranking: Mapped[list] = mapped_column(JSONBCompat, default=list)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class Assumption(Base):
    """Fact, assumption, or benchmark-backed input to a value model."""

    __tablename__ = "value_assumptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)

    statement: Mapped[str]
    assumption_type: Mapped[AssumptionType]
    value: Mapped[dict] = mapped_column(JSONBCompat, default=dict)

    confidence: Mapped[Confidence]
    evidence_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)
    source_signal_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)

    impact_level: Mapped[ImpactLevel]
    approval_status: Mapped[ApprovalStatus]

    benchmark_dataset_id: Mapped[Optional[uuid.UUID]]
    benchmark_metric: Mapped[Optional[str]]
    benchmark_percentile: Mapped[Optional[int]]


class EvidenceLink(Base):
    """Typed evidence attached to claims, assumptions, objections, or stakeholders."""

    __tablename__ = "value_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]

    target_type: Mapped[str]
    target_id: Mapped[uuid.UUID]

    evidence_type: Mapped[EvidenceType]
    source_id: Mapped[uuid.UUID]
    source_url: Mapped[Optional[str]]
    excerpt: Mapped[Optional[str]]
    relevance_score: Mapped[float]
    captured_at: Mapped[datetime]


class BusinessProblem(Base):
    """A business problem supported by signals and mapped to value drivers."""

    __tablename__ = "business_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[Optional[uuid.UUID]]

    statement: Mapped[str]
    problem_type: Mapped[str]

    signal_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)
    driver_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)


class Stakeholder(Base):
    """Buying persona with decision criteria, preferred proof, and beliefs."""

    __tablename__ = "value_stakeholders"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[uuid.UUID]

    name: Mapped[str]
    role: Mapped[str]
    influence_level: Mapped[str]
    decision_criteria: Mapped[list] = mapped_column(JSONBCompat, default=list)
    preferred_proof_types: Mapped[list] = mapped_column(JSONBCompat, default=list)
    pain_points: Mapped[list] = mapped_column(JSONBCompat, default=list)
    goals: Mapped[list] = mapped_column(JSONBCompat, default=list)


class Objection(Base):
    """Structured challenge to a value claim."""

    __tablename__ = "value_objections"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    claim_id: Mapped[uuid.UUID]

    statement: Mapped[str]
    objection_type: Mapped[str]
    severity: Mapped[str]

    raised_by_stakeholder_id: Mapped[Optional[uuid.UUID]]
    raised_at: Mapped[datetime]
    status: Mapped[str]

    counter_evidence_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)
    resolution_note: Mapped[Optional[str]]


class RealizationEvent(Base):
    """Predicted → committed → realized value chain for a claim."""

    __tablename__ = "value_realization_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    claim_id: Mapped[uuid.UUID]

    event_type: Mapped[str]
    value: Mapped[Decimal]
    value_unit: Mapped[str]

    reason: Mapped[Optional[str]]
    benchmark_ids: Mapped[Optional[list]] = mapped_column(JSONBCompat, nullable=True)

    recorded_at: Mapped[datetime]
    recorded_by: Mapped[Optional[str]]


class ValueCase(Base):
    """Container for a set of claims, narratives, scenarios, and stakeholders."""

    __tablename__ = "value_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[uuid.UUID]
    opportunity_id: Mapped[Optional[uuid.UUID]]
    business_case_record_id: Mapped[Optional[uuid.UUID]]

    title: Mapped[str]
    status: Mapped[str]
    claim_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)
    stakeholder_ids: Mapped[list] = mapped_column(JSONBCompat, default=list)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
