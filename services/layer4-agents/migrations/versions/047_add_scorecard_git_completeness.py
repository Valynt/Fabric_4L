"""Add git completeness metadata columns to scorecards.

Revision ID: 047_add_scorecard_git_completeness
Revises: 046_align_runtime_schema_columns
Create Date: 2026-08-25
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "047_add_scorecard_git_completeness"
down_revision: Union[str, None] = "046_align_runtime_schema_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist per-metric git collection status so an exact figure can be
    distinguished from a timed-out, truncated or failed one."""
    op.add_column(
        "scorecards",
        sa.Column("git_metric_completeness", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scorecards",
        sa.Column("git_warnings", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop completeness metadata columns in dependency-safe reverse order."""
    op.drop_column("scorecards", "git_warnings")
    op.drop_column("scorecards", "git_metric_completeness")
