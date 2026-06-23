from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON, TypeDecorator

"""SQLAlchemy ORM models for the L2.5 Signal Refinery.

Design notes:
- UUID primary keys throughout
- tenant_id on every table — enforced by RLS policy
- evidence and provenance stored as JSONB (PostgreSQL) / JSON (SQLite)
- soft-delete via deleted_at
- source_refs and related_signal_ids stored as JSON arrays
"""


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Cross-platform UUID type
# ---------------------------------------------------------------------------


class UUID(TypeDecorator):
    """UUID stored as native UUID on PostgreSQL, String(36) on SQLite."""

    impl = String
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(length=36)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name != "postgresql" else value
        return str(uuid.UUID(str(value))) if dialect.name != "postgresql" else uuid.UUID(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# ---------------------------------------------------------------------------
# ValueSignal table
# ---------------------------------------------------------------------------


class ValueSignalRow(Base):
    """Persistent store for ValueSignal objects.

    evidence and provenance are stored as JSON blobs — they are read/written
    as complete objects and never queried column-by-column.
    """

    __tablename__ = "value_signals"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(), nullable=False, index=True)
    account_id = Column(UUID(), nullable=False, index=True)

    type = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)

    confidence = Column(Float, nullable=False)
    trust_score = Column(Float, nullable=False, default=0.0)
    lifecycle_state = Column(String(32), nullable=False, default="draft")

    # JSON blobs
    evidence = Column(JSON, nullable=False, default=list)
    provenance = Column(JSON, nullable=False)
    source_refs = Column(JSON, nullable=False, default=list)

    # Optional enrichments
    opportunity_id = Column(UUID(), nullable=True)
    value_driver_id = Column(UUID(), nullable=True)
    stakeholder_id = Column(UUID(), nullable=True)
    persona = Column(String(256), nullable=True)
    industry = Column(String(128), nullable=True)
    impact_area = Column(String(32), nullable=True)
    estimated_value = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    time_horizon = Column(String(128), nullable=True)
    validation_notes = Column(Text, nullable=True)
    reviewer_id = Column(UUID(), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    supersedes_signal_id = Column(UUID(), nullable=True)
    related_signal_ids = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_value_signals_tenant_account", "tenant_id", "account_id"),
        Index("ix_value_signals_tenant_type", "tenant_id", "type"),
        Index("ix_value_signals_tenant_lifecycle", "tenant_id", "lifecycle_state"),
    )
