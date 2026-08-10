"""Align persisted tables with columns required by runtime ORM models.

Revision ID: 046_align_runtime_schema_columns
Revises: 045_harden_late_tenant_tables
Create Date: 2026-07-31
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "046_align_runtime_schema_columns"
down_revision: Union[str, None] = "045_harden_late_tenant_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add columns already consumed by the live Layer 4 runtime."""
    op.add_column(
        "accounts",
        sa.Column("employees", sa.Integer(), nullable=True),
    )
    op.add_column(
        "harness_human_gates",
        sa.Column("action_class", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Remove runtime-alignment columns in dependency-safe reverse order."""
    op.drop_column("harness_human_gates", "action_class")
    op.drop_column("accounts", "employees")
