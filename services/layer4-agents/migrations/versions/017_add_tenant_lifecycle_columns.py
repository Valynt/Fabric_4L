"""Add tenant lifecycle audit columns.

Revision ID: 017
Revises: 016
Create Date: 2026-04-25

Adds status_changed_at, status_reason, and status_changed_by columns to the
tenants table to support the enhanced lifecycle state machine with full audit
trail (Phase 1, Task 1.4).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    """Add lifecycle audit columns to tenants table."""
    op.add_column(
        "tenants",
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of the last status transition",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "status_reason",
            sa.Text(),
            nullable=True,
            comment="Human-readable reason for the last status change",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "status_changed_by",
            sa.String(255),
            nullable=True,
            comment="User ID or service name that triggered the last status change",
        ),
    )


def downgrade():
    """Remove lifecycle audit columns from tenants table."""
    op.drop_column("tenants", "status_changed_by")
    op.drop_column("tenants", "status_reason")
    op.drop_column("tenants", "status_changed_at")
