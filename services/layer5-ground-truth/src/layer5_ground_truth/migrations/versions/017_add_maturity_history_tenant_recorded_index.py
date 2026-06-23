"""Add maturity_history tenant_id + recorded_at composite index.

Adds a missing composite index on (tenant_id, recorded_at) for the
maturity_history table to support tenant-scoped history queries.

Revision ID: 017
Revises: 016
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "ix_maturity_history_tenant_recorded",
        "maturity_history",
        ["tenant_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maturity_history_tenant_recorded",
        table_name="maturity_history",
    )
