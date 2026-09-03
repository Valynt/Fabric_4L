"""SQLAlchemy ORM models for the Layer 4 Agent Runtime persistence layer.

Three tables back the durable runtime ports introduced in Phase 6 task #3:

  runtime_thread_states      <- MemoryPort thread state (latest write wins)
  runtime_long_term_memory   <- MemoryPort long-term retrieval pool
  runtime_checkpoints        <- CheckpointPort durable snapshots

All tables carry ``tenant_id`` for Row-Level Security (see migration 048).
``tenant_id`` is ``String(255)`` with no FK to ``tenants.id``, matching the
harness convention and supporting arbitrary tenant identifiers used across the
runtime ports and their tests.

Dict/list payload columns use the generic :class:`sqlalchemy.JSON` type so the
models work against both PostgreSQL and SQLite (unit tests). The Alembic
migration (``048_add_runtime_memory_checkpoint_tables.py``) types those columns
as ``postgresql.JSONB`` for the production schema, mirroring migration 031.

``runtime_checkpoints.created_at`` is persisted as the original ISO-8601
*string* from the :class:`~layer4_agents.runtime.models.Checkpoint` model so a
``load`` reconstructs the exact value with no timezone reformatting. Save-order
semantics are carried by the surrogate integer ``seq`` column (autoincrement),
which ``list``/``load`` order by instead of the string timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# Base is resolved at import time. In the full service context we use the
# canonical layer4_agents.database.Base so runtime tables are included in
# Alembic autogenerate and ``init_db()`` create_all. In standalone SQLite tests
# without the full service stack we fall back to a local DeclarativeBase
# (mirrors harness/db_models.py).
try:
    from layer4_agents.database import Base  # full service context
except ImportError:
    from sqlalchemy.orm import DeclarativeBase  # type: ignore[assignment]

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        """Fallback base for standalone SQLite tests."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RuntimeThreadStateRow(Base):
    """One row per ``(tenant_id, thread_id)`` thread-state snapshot."""

    __tablename__ = "runtime_thread_states"
    __table_args__ = {"extend_existing": True}

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow, onupdate=_utcnow, nullable=False
    )


class RuntimeLongTermMemoryRow(Base):
    """One row per long-term memory record; ``content`` is the search haystack."""

    __tablename__ = "runtime_long_term_memory"
    __table_args__ = {"extend_existing": True}

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    record: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class RuntimeCheckpointRow(Base):
    """One row per runtime checkpoint, keyed by ``(tenant_id, run_id, thread_id, checkpoint_id)``."""

    __tablename__ = "runtime_checkpoints"
    __table_args__ = {"extend_existing": True}

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # ``metadata`` is reserved by the SQLAlchemy Declarative API, so the Python
    # attribute is ``metadata_json`` while the DB column stays ``metadata``.
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
