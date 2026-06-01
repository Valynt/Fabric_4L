"""Merge post-010 branches into single history.

Revision ID: 015
Revises: 010b, 014_add_value_realization_ledger, 014_add_approval_level_quorum_metadata
Create Date: 2026-05-27
"""

from alembic import op

revision = "015"
down_revision = ("010b", "014_add_value_realization_ledger", "014_add_approval_level_quorum_metadata")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All parent branches already applied their schema changes.
    # This is a structural merge to restore a single Alembic head.
    pass


def downgrade() -> None:
    pass
