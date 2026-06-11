"""Fix pipeline schema drift: add missing columns, rename mismatched columns.

Revision ID: 018
Revises: 017
Create Date: 2026-06-02

Fixes two schema/model inconsistencies discovered during Layer 1 test
stabilization:

1. scraping_jobs.target_entity_id — defined in the SQLAlchemy model but
   never added via migration. Production code (api/main.py) reads and
   writes this field, so it must exist in the database.

2. job_stage_details.meta vs metadata — migration 003 created a column
   named ``metadata``, but the SQLAlchemy model declares ``meta``
   (``meta = Column(JSONB, default=dict)``). Production code accesses
   ``.meta`` on ``JobStageDetail`` instances, so the DB column must match.

Neither change drops data. The rename is a pure DDL operation.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema corrections."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    scraping_columns = [c["name"] for c in inspector.get_columns("scraping_jobs")]
    stage_columns = [c["name"] for c in inspector.get_columns("job_stage_details")]

    # 1. Add missing target_entity_id to scraping_jobs
    if "target_entity_id" not in scraping_columns:
        op.add_column(
            "scraping_jobs",
            sa.Column("target_entity_id", sa.String(255), nullable=True),
        )

    # 2. Rename job_stage_details.metadata -> meta to match the model
    if "metadata" in stage_columns and "meta" not in stage_columns:
        op.alter_column(
            "job_stage_details",
            "metadata",
            new_column_name="meta",
            existing_type=JSONB,
            existing_server_default=sa.text("'{}'::jsonb"),
        )


def downgrade() -> None:
    """Revert schema corrections."""
    # 1. Revert rename
    op.alter_column(
        "job_stage_details",
        "meta",
        new_column_name="metadata",
        existing_type=JSONB,
        existing_server_default=sa.text("'{}'::jsonb"),
    )

    # 2. Drop target_entity_id
    op.drop_column("scraping_jobs", "target_entity_id")
