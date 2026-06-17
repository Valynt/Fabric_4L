"""Add revoked_at and creator_user_id to api_keys.

Adds columns needed for production-grade API key lifecycle:
- revoked_at: immutable revocation timestamp (supersedes enabled=False over time)
- creator_user_id: non-nullable going forward; nullable initially for backfill.

Backfills revoked_at from existing enabled=False rows.

Revision ID: 042_add_api_key_revoked_at_creator
Revises: 041_add_business_case_records_tenant_indexes
Create Date: 2026-06-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "042_add_api_key_revoked_at_creator"
down_revision = "041_add_business_case_records_tenant_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the key was revoked; immutable after set.",
        ),
    )
    op.add_column(
        "api_keys",
        sa.Column(
            "creator_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who created the key. Enforced NOT NULL at API layer.",
        ),
    )

    # Backfill revoked_at for keys already disabled via the legacy enabled flag.
    op.execute(
        """
        UPDATE api_keys
        SET revoked_at = NOW()
        WHERE enabled = FALSE AND revoked_at IS NULL
        """
    )

    op.create_index("ix_api_keys_tenant_revoked", "api_keys", ["tenant_id", "revoked_at"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_tenant_revoked", table_name="api_keys")
    op.drop_column("api_keys", "creator_user_id")
    op.drop_column("api_keys", "revoked_at")
