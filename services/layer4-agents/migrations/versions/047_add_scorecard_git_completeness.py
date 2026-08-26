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
    distinguished from a timed-out, truncated or failed one.

    The ``scorecards`` table is owned by the ORM ``ScorecardDB`` model and is
    created at runtime by ``Base.metadata.create_all``, not by any revision in
    this chain. A fresh database (e.g. the migration-only CI/e2e flow, or any
    deployment where the table has not yet been materialised at runtime) has no
    ``scorecards`` table at all. In that case skip the ALTER — ``create_all``
    creates the full table (including these columns) from the model. When the
    table already exists (a runtime-created schema being migrated), add the
    columns so existing deployed rows gain the metadata.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("scorecards"):
        return
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("scorecards"):
        return
    op.drop_column("scorecards", "git_warnings")
    op.drop_column("scorecards", "git_metric_completeness")
