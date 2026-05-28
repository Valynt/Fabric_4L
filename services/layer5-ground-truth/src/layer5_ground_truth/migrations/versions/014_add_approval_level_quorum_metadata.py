"""Add ordered approval level and quorum metadata for approval workflows.

Revision ID: 014_add_approval_level_quorum_metadata
Revises: 013_add_assumption_registry
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014_add_approval_level_quorum_metadata"
down_revision = "013_add_assumption_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_workflows", sa.Column("level_definitions", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("approval_workflows", sa.Column("default_level_quorum", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("approval_workflows", sa.Column("escalation_mode", sa.String(length=32), nullable=False, server_default="manual"))
    op.execute("UPDATE approval_workflows SET default_level_quorum = 1 WHERE default_level_quorum IS NULL")
    op.execute("UPDATE approval_workflows SET escalation_mode = 'manual' WHERE escalation_mode IS NULL")


def downgrade() -> None:
    op.drop_column("approval_workflows", "escalation_mode")
    op.drop_column("approval_workflows", "default_level_quorum")
    op.drop_column("approval_workflows", "level_definitions")
