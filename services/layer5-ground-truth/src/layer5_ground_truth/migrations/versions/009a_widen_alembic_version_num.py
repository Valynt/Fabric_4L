"""Widen alembic_version.version_num to support long revision ids.

Revision ID: 009a
Revises: 009
Create Date: 2026-06-13

The default Alembic alembic_version.version_num column is varchar(32).
Migration 010_harden_validation_event_immutability uses a 42-character
revision id, which exceeds that width and causes a StringDataRightTruncation
error on PostgreSQL. This migration widens the column before 010 runs.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers
revision: str = "009a_widen_alembic_version_num"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(64)")


def downgrade() -> None:
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(32)")
