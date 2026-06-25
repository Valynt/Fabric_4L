from __future__ import annotations

"""SQLAlchemy ORM models for Fabric Harness persistence.

Six tables back the harness stores:
  harness_runs                    ← HarnessRun domain model
  harness_human_gates             ← HumanGate domain model
  harness_checkpoints             ← HarnessCheckpoint domain model
  harness_tool_contracts          ← ToolContract domain model
  harness_trace_events            ← HarnessTraceEvent domain model
  harness_claim_validation_results← ClaimValidationResult domain model

All tables carry tenant_id for Row-Level Security.
JSONB columns store dict/list payloads (state_payload, tool_calls, metadata).
Primary keys are String IDs matching the harness domain model ID format.
"""


import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

# ORM models use generic JSON so they work with both Postgres and SQLite (tests).
# The Alembic migration (031_add_harness_tables.py) uses postgresql.JSONB explicitly
# so the Postgres schema gets the proper JSONB type with indexing support.
_JsonType = JSON

# Base is resolved at import time. In the full service context we use the
# canonical layer4_agents.database.Base so harness tables are included in Alembic autogenerate.
# In standalone harness tests (SQLite, no full service stack) we fall back to a
# local DeclarativeBase so the module remains importable without the service deps.
try:
    from layer4_agents.database import Base  # full service context
except ImportError:
    from sqlalchemy.orm import DeclarativeBase  # type: ignore[assignment]

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        """Fallback base for standalone harness tests."""
        pass


class HarnessRunRow(Base):
    """Persistent record for a HarnessRun lifecycle."""

    __tablename__ = "harness_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_state: Mapped[str] = mapped_column(String(32), nullable=False)
    value_pack_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_harness_runs_tenant_status", "tenant_id", "status"),
        Index("ix_harness_runs_tenant_state", "tenant_id", "current_state"),
        Index("ix_harness_runs_trace_id", "trace_id"),
    )


class HumanGateRow(Base):
    """Persistent record for a HumanGate approval gate."""

    __tablename__ = "harness_human_gates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("harness_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    gate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decision_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_harness_human_gates_run_tenant", "run_id", "tenant_id"),
        Index("ix_harness_human_gates_tenant_status", "tenant_id", "status"),
    )


class HarnessCheckpointRow(Base):
    """Persistent record for a deterministic HarnessCheckpoint snapshot."""

    __tablename__ = "harness_checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("harness_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    state_name: Mapped[str] = mapped_column(String(32), nullable=False)
    state_payload: Mapped[dict] = mapped_column(_JsonType, nullable=False, default=dict)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_calls: Mapped[list] = mapped_column(_JsonType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_harness_checkpoints_run_tenant", "run_id", "tenant_id"),
        Index("ix_harness_checkpoints_tenant_state", "tenant_id", "state_name"),
        Index("ix_harness_checkpoints_input_hash", "input_hash"),
    )


class ToolContractRow(Base):
    """Persistent record for a ToolContract definition."""

    __tablename__ = "harness_tool_contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    layer: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    input_schema_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    output_schema_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    side_effect_class: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    requires_tenant_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_account_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_policy_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_id", name="uq_harness_tool_contracts_tenant_tool"),
        Index("ix_harness_tool_contracts_tenant_layer", "tenant_id", "layer"),
        Index("ix_harness_tool_contracts_tenant_risk", "tenant_id", "risk_level"),
    )


class HarnessTraceEventRow(Base):
    """Persistent record for a structured HarnessTraceEvent."""

    __tablename__ = "harness_trace_events"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"evt_{uuid.uuid4().hex[:16]}",
    )
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("harness_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value_pack_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    human_gate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="transition")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", _JsonType, nullable=False, default=dict,
        comment="Structured event metadata (column named 'metadata' in DB)",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_harness_trace_events_run_tenant", "run_id", "tenant_id"),
        Index("ix_harness_trace_events_tenant_type", "tenant_id", "event_type"),
        Index("ix_harness_trace_events_trace_id", "trace_id"),
    )


class ClaimValidationResultRow(Base):
    """Persistent record for a ClaimValidationResult produced during a harness run.

    Linked to harness_runs via run_id so the GET /validation endpoint can
    retrieve all results for a given run without re-running validation.
    """

    __tablename__ = "harness_claim_validation_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("harness_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Tenant identifier for RLS isolation"
    )
    claim_id: Mapped[str] = mapped_column(String(255), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_refs: Mapped[list] = mapped_column(_JsonType, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    validator: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_harness_cvr_run_tenant", "run_id", "tenant_id"),
        Index("ix_harness_cvr_tenant_state", "tenant_id", "validation_state"),
        Index("ix_harness_cvr_claim_id", "claim_id"),
    )
