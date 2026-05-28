from __future__ import annotations

"""Add tenant isolation tier history table (Task 4.1).

Revision ID: 012
Revises: 011
Create Date: 2026-04-22

"""


from alembic import op
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tenant_isolation_tier_history table for audit trail."""
    # Create the history table
    op.create_table(
        "tenant_isolation_tier_history",
        Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        Column(
            "tenant_id",
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        Column(
            "from_tier",
            String(20),
            nullable=False,
        ),
        Column(
            "to_tier",
            String(20),
            nullable=False,
        ),
        Column(
            "changed_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column(
            "changed_by",
            UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
        Column(
            "reason",
            Text,
            nullable=True,
        ),
        Column(
            "change_source",
            String(30),
            nullable=False,
            server_default=text("'admin'"),
        ),
        Column(
            "request_id",
            String(100),
            nullable=True,
            index=True,
        ),
    )

    # Create composite index for tenant + changed_at queries
    op.create_index(
        "ix_tier_history_tenant_changed",
        "tenant_isolation_tier_history",
        ["tenant_id", "changed_at"],
    )

    # Create index for change source queries
    op.create_index(
        "ix_tier_history_source",
        "tenant_isolation_tier_history",
        ["change_source"],
    )

    # Add comment to table
    op.execute(
        text(
            "COMMENT ON TABLE tenant_isolation_tier_history IS "
            "'Audit history for tenant isolation tier changes (Task 4.1)'"
        )
    )


def downgrade() -> None:
    """Drop tenant_isolation_tier_history table."""
    op.drop_index("ix_tier_history_source", table_name="tenant_isolation_tier_history")
    op.drop_index("ix_tier_history_tenant_changed", table_name="tenant_isolation_tier_history")
    op.drop_table("tenant_isolation_tier_history")
