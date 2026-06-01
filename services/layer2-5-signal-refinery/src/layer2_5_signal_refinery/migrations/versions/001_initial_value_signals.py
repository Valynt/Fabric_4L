from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

"""Initial value_signals table with RLS policies.

Revision ID: 001
Revises: —
Create Date: 2026-05-14
"""

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "value_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("trust_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("evidence", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("provenance", sa.JSON, nullable=False),
        sa.Column("source_refs", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("opportunity_id", sa.String(36), nullable=True),
        sa.Column("value_driver_id", sa.String(36), nullable=True),
        sa.Column("stakeholder_id", sa.String(36), nullable=True),
        sa.Column("persona", sa.String(256), nullable=True),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("impact_area", sa.String(32), nullable=True),
        sa.Column("estimated_value", sa.Float, nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("time_horizon", sa.String(128), nullable=True),
        sa.Column("validation_notes", sa.Text, nullable=True),
        sa.Column("reviewer_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_signal_id", sa.String(36), nullable=True),
        sa.Column("related_signal_ids", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_value_signals_tenant_account", "value_signals", ["tenant_id", "account_id"])
    op.create_index("ix_value_signals_tenant_type", "value_signals", ["tenant_id", "type"])
    op.create_index("ix_value_signals_tenant_lifecycle", "value_signals", ["lifecycle_state", "tenant_id"])

    # PostgreSQL RLS — skipped on SQLite (used in tests)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE value_signals ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE value_signals FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY tenant_isolation_policy ON value_signals
                FOR ALL TO PUBLIC
                USING (tenant_id::text = current_setting('app.tenant_id', true))
                WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON value_signals")
    op.drop_table("value_signals")
