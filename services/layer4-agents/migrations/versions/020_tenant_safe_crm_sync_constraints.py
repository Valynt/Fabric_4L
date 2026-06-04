"""Make CRM account and sync status tenant-safe.

Revision ID: 020
Revises: 019
Create Date: 2026-04-28

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # account_sync_status: add tenant_id and tenant+provider uniqueness
    op.add_column(
        "account_sync_status",
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
    )
    op.create_index(
        "ix_sync_status_tenant_provider",
        "account_sync_status",
        ["tenant_id", "provider", "status"],
        unique=False,
    )

    # MIGRATION_REVIEW_REQUIRED: DROP CONSTRAINT is destructive — removes unique enforcement
    # Community Edition fallback: IF EXISTS prevents failure on CE where constraint may not exist
    op.execute(
        "ALTER TABLE account_sync_status "
        "DROP CONSTRAINT IF EXISTS account_sync_status_provider_key"
    )
    op.execute(
        "ALTER TABLE account_sync_status "
        "ADD CONSTRAINT uix_sync_status_tenant_provider UNIQUE (tenant_id, provider)"
    )

    # MIGRATION_REVIEW_REQUIRED: DROP CONSTRAINT removes legacy unique index
    op.execute(
        "ALTER TABLE accounts "
        "DROP CONSTRAINT IF EXISTS uix_account_provider_record"
    )
    op.execute(
        "ALTER TABLE accounts "
        "ADD CONSTRAINT uix_account_tenant_provider_record UNIQUE (tenant_id, provider, provider_record_id)"
    )


def downgrade() -> None:
    # MIGRATION_REVIEW_REQUIRED: DROP CONSTRAINT is destructive — removes tenant-scoped uniqueness
    # Community Edition fallback: IF EXISTS prevents failure on CE
    op.execute(
        "ALTER TABLE accounts "
        "DROP CONSTRAINT IF EXISTS uix_account_tenant_provider_record"
    )
    op.execute(
        "ALTER TABLE accounts "
        "ADD CONSTRAINT uix_account_provider_record UNIQUE (provider, provider_record_id)"
    )

    op.execute(
        "ALTER TABLE account_sync_status "
        "DROP CONSTRAINT IF EXISTS uix_sync_status_tenant_provider"
    )
    op.execute(
        "ALTER TABLE account_sync_status "
        "ADD CONSTRAINT account_sync_status_provider_key UNIQUE (provider)"
    )

    op.drop_index("ix_sync_status_tenant_provider", table_name="account_sync_status")
    op.drop_column("account_sync_status", "tenant_id")
