"""Ensure truth_objects.tenant_id exists and is required.

Revision ID: 008
Revises: 007
Create Date: 2026-05-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKFILL_TENANT_UUID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    """Add tenant_id with safe backfill strategy for existing rows when needed."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("truth_objects")}

    if "tenant_id" not in columns:
        op.add_column(
            "truth_objects",
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text(f"'{BACKFILL_TENANT_UUID}'::uuid"),
            ),
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE truth_objects
                SET tenant_id = :fallback::uuid
                WHERE tenant_id IS NULL
                """
            ).bindparams(fallback=BACKFILL_TENANT_UUID)
        )
        op.alter_column("truth_objects", "tenant_id", nullable=False)

    op.execute("CREATE INDEX IF NOT EXISTS ix_truth_objects_tenant_id ON truth_objects (tenant_id)")
    op.alter_column("truth_objects", "tenant_id", server_default=None)


def downgrade() -> None:
    """Re-allow nullable tenant_id while preserving data."""
    op.alter_column("truth_objects", "tenant_id", nullable=True)
