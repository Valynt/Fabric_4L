"""Value Evidence Graph relational models."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Mapped, mapped_column

from .truth_object import UUID, Base, JSONBCompat
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
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID, index=True)

    statement: Mapped[str]
    claim_type: Mapped[ClaimType]

    value_unit: Mapped[str]
    conservative_value: Mapped[Decimal]
    expected_value: Mapped[Decimal]
    aggressive_value: Mapped[Decimal]
    confidence: Mapped[Confidence]
    weakest_assumption_id: Mapped[uuid.UUID | None]

    status: Mapped[ClaimStatus]
    maturity_level: Mapped[int]
    version: Mapped[int] = mapped_column(default=1)

    created_by_user_id: Mapped[str | None]
    created_by_workflow_id: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    scenario_id: Mapped[uuid.UUID | None]
    truth_object_id: Mapped[uuid.UUID | None]


class Scenario(Base):
    """A set of assumption overrides applied to a formula."""

    __tablename__ = "value_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    case_id: Mapped[uuid.UUID | None]

    name: Mapped[str]
    scenario_type: Mapped[ScenarioType]

    formula_id: Mapped[uuid.UUID]
    assumption_overrides: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default=dict)
    sensitivity_ranking: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ValueAssumption(Base):
    """Fact, assumption, or benchmark-backed input to a value model."""

    __tablename__ = "value_assumptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)

    statement: Mapped[str]
    assumption_type: Mapped[AssumptionType]
    value: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default=dict)

    confidence: Mapped[Confidence]
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    source_signal_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)

    impact_level: Mapped[ImpactLevel]
    approval_status: Mapped[ApprovalStatus]

    benchmark_dataset_id: Mapped[uuid.UUID | None]
    benchmark_metric: Mapped[str | None]
    benchmark_percentile: Mapped[int | None]


class EvidenceLink(Base):
    """Typed evidence attached to claims, assumptions, objections, or stakeholders."""

    __tablename__ = "value_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]

    target_type: Mapped[str]
    target_id: Mapped[uuid.UUID]

    evidence_type: Mapped[EvidenceType]
    source_id: Mapped[uuid.UUID]
    source_url: Mapped[str | None]
    excerpt: Mapped[str | None]
    relevance_score: Mapped[float]
    captured_at: Mapped[datetime]


class BusinessProblem(Base):
    """A business problem supported by signals and mapped to value drivers."""

    __tablename__ = "business_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[uuid.UUID | None]

    statement: Mapped[str]
    problem_type: Mapped[str]

    signal_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    driver_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)


class Stakeholder(Base):
    """Buying persona with decision criteria, preferred proof, and beliefs."""

    __tablename__ = "value_stakeholders"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[uuid.UUID]

    name: Mapped[str]
    role: Mapped[str]
    influence_level: Mapped[str]
    decision_criteria: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    preferred_proof_types: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    pain_points: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    goals: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)


class Objection(Base):
    """Structured challenge to a value claim."""

    __tablename__ = "value_objections"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    claim_id: Mapped[uuid.UUID]

    statement: Mapped[str]
    objection_type: Mapped[str]
    severity: Mapped[str]

    raised_by_stakeholder_id: Mapped[uuid.UUID | None]
    raised_at: Mapped[datetime]
    status: Mapped[str]

    counter_evidence_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    resolution_note: Mapped[str | None]


class RealizationEvent(Base):
    """Predicted → committed → realized value chain for a claim."""

    __tablename__ = "value_realization_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    claim_id: Mapped[uuid.UUID]

    event_type: Mapped[str]
    value: Mapped[Decimal]
    value_unit: Mapped[str]

    reason: Mapped[str | None]
    benchmark_ids: Mapped[list[Any] | None] = mapped_column(JSONBCompat, nullable=True)

    recorded_at: Mapped[datetime]
    recorded_by: Mapped[str | None]


class ValueCase(Base):
    """Container for a set of claims, narratives, scenarios, and stakeholders."""

    __tablename__ = "value_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]
    account_id: Mapped[uuid.UUID]
    opportunity_id: Mapped[uuid.UUID | None]
    business_case_record_id: Mapped[uuid.UUID | None]

    title: Mapped[str]
    status: Mapped[str]
    claim_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)
    stakeholder_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, default=list)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
