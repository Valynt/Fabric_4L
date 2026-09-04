"""Add durable runtime memory and checkpoint tables for the Agent Runtime.

Creates three tables backing the Postgres ``MemoryPort`` / ``CheckpointPort``
adapters (Phase 6 task #3):

  runtime_thread_states      — thread-state snapshots keyed (tenant_id, thread_id)
  runtime_long_term_memory   — append-only long-term memory pool (case-folded search)
  runtime_checkpoints        — runtime checkpoints keyed
                               (tenant_id, run_id, thread_id, checkpoint_id)

All tables carry tenant_id with strict RLS policies matching the Layer 4
convention established in migrations 007, 028, and 031. JSON payload columns
use ``postgresql.JSONB`` for the production schema (the ORM models use generic
``JSON`` so they work against SQLite in unit tests).

Revision ID: 048_add_runtime_memory_checkpoint_tables
Revises: 047_add_scorecard_git_completeness
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "048_add_runtime_memory_checkpoint_tables"
down_revision: Union[str, None] = "047_add_scorecard_git_completeness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables created by this migration — no FK dependencies between them.
_TABLES_IN_ORDER = [
    "runtime_thread_states",
    "runtime_long_term_memory",
    "runtime_checkpoints",
]

_TABLES_IN_REVERSE = list(reversed(_TABLES_IN_ORDER))


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. runtime_thread_states — latest-write-wins thread state
    # ------------------------------------------------------------------ #
    op.create_table(
        "runtime_thread_states",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "thread_id", name="uq_runtime_thread_states_tenant_thread"),
    )
    op.create_index("ix_runtime_thread_states_tenant_id", "runtime_thread_states", ["tenant_id"])
    op.create_index("ix_runtime_thread_states_thread_id", "runtime_thread_states", ["thread_id"])

    # ------------------------------------------------------------------ #
    # 2. runtime_long_term_memory — append-only long-term memory pool
    # ------------------------------------------------------------------ #
    op.create_table(
        "runtime_long_term_memory",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("record", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_runtime_long_term_memory_tenant_id", "runtime_long_term_memory", ["tenant_id"]
    )

    # ------------------------------------------------------------------ #
    # 3. runtime_checkpoints — durable CheckpointPort snapshots
    # ------------------------------------------------------------------ #
    op.create_table(
        "runtime_checkpoints",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("checkpoint_id", sa.String(255), nullable=False),
        sa.Column("run_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("state_hash", sa.String(255), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "run_id", "thread_id", "checkpoint_id",
            name="uq_runtime_checkpoints_composite_key",
        ),
    )
    op.create_index("ix_runtime_checkpoints_tenant_id", "runtime_checkpoints", ["tenant_id"])
    op.create_index("ix_runtime_checkpoints_run_id", "runtime_checkpoints", ["run_id"])

    # ------------------------------------------------------------------ #
    # RLS — strict tenant isolation matching migration 028/031 pattern
    # ------------------------------------------------------------------ #
    for table in _TABLES_IN_ORDER:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
            """
        )

        op.execute(
            f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '')
            """
        )


def downgrade() -> None:
    # Drop RLS policies first, then tables in reverse creation order.
    for table in _TABLES_IN_REVERSE:
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")

    op.drop_index("ix_runtime_checkpoints_run_id", table_name="runtime_checkpoints")
    op.drop_index("ix_runtime_checkpoints_tenant_id", table_name="runtime_checkpoints")
    op.drop_table("runtime_checkpoints")

    op.drop_index("ix_runtime_long_term_memory_tenant_id", table_name="runtime_long_term_memory")
    op.drop_table("runtime_long_term_memory")

    op.drop_index("ix_runtime_thread_states_thread_id", table_name="runtime_thread_states")
    op.drop_index("ix_runtime_thread_states_tenant_id", table_name="runtime_thread_states")
    op.drop_table("runtime_thread_states")
