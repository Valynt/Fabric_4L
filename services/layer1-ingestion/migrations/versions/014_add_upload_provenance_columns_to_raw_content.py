"""Add upload provenance columns to raw_content.

Revision ID: 014
Revises: 013
Create Date: 2026-05-23
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("raw_content", sa.Column("source_type", sa.String(length=50), nullable=True))
    op.add_column("raw_content", sa.Column("source_origin", sa.String(length=255), nullable=True))
    op.add_column(
        "raw_content", sa.Column("source_connector_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "raw_content", sa.Column("source_checksum_sha256", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "raw_content", sa.Column("source_account_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("raw_content", sa.Column("storage_binary_path", sa.Text(), nullable=True))
    op.create_index(
        "ix_raw_content_source_account_id", "raw_content", ["source_account_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_raw_content_source_account_id", table_name="raw_content")
    op.drop_column("raw_content", "storage_binary_path")
    op.drop_column("raw_content", "source_account_id")
    op.drop_column("raw_content", "source_checksum_sha256")
    op.drop_column("raw_content", "source_connector_id")
    op.drop_column("raw_content", "source_origin")
    op.drop_column("raw_content", "source_type")
