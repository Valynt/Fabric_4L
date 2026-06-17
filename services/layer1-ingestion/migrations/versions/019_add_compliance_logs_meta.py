"""Add missing compliance_logs.meta column.

Revision ID: 019
Revises: 018
Create Date: 2026-06-16

The SQLAlchemy model declares ``ComplianceLog.meta`` and the compliance task
persists structured metadata through that field. Migration 003 created
``compliance_logs`` before the model gained the column, so fresh local E2E
databases fail during the compliance stage when the ORM writes ``meta``.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the model-backed metadata column when absent."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    compliance_columns = [c["name"] for c in inspector.get_columns("compliance_logs")]

    if "meta" not in compliance_columns:
        op.add_column(
            "compliance_logs",
            sa.Column(
                "meta",
                JSONB,
                nullable=True,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    """Remove the metadata column if this migration is rolled back."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    compliance_columns = [c["name"] for c in inspector.get_columns("compliance_logs")]

    if "meta" in compliance_columns:
        op.drop_column("compliance_logs", "meta")
