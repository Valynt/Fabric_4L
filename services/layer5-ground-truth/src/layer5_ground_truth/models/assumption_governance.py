import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text

from .truth_object import UUID, Base


class LifecycleState(str, PyEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    PUBLISHED = "published"


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AssumptionRecord(Base):
    __tablename__ = "assumption_records"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    impact_value = Column(Float, nullable=False, default=0.0)
    lifecycle_state = Column(String(32), nullable=False, default=LifecycleState.DRAFT.value)
    is_approved_for_use = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class FormulaDefinition(Base):
    __tablename__ = "formula_definitions"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    assumption_id = Column(UUID, ForeignKey("assumption_records.id", ondelete="CASCADE"), nullable=False)
    expression = Column(Text, nullable=False)
    lifecycle_state = Column(String(32), nullable=False, default=LifecycleState.DRAFT.value)


class BenchmarkDataset(Base):
    __tablename__ = "benchmark_datasets"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    dataset_uri = Column(String(1024), nullable=False)
    lifecycle_state = Column(String(32), nullable=False, default=LifecycleState.DRAFT.value)


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    min_impact_threshold = Column(Float, nullable=False, default=0.0)
    required_reviewer_role = Column(String(128), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    lifecycle_state = Column(String(32), nullable=False, default=LifecycleState.PUBLISHED.value)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    assumption_id = Column(UUID, ForeignKey("assumption_records.id", ondelete="CASCADE"), nullable=False)
    policy_rule_id = Column(UUID, ForeignKey("policy_rules.id", ondelete="SET NULL"), nullable=True)
    requested_by = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default=ApprovalStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    approval_request_id = Column(UUID, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_role = Column(String(128), nullable=False)
    decision = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

Index("ix_approval_requests_assumption_id", ApprovalRequest.assumption_id)
