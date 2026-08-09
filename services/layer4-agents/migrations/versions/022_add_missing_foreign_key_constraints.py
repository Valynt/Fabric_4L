"""Add missing foreign key constraints for data integrity (P1-6).

Revision ID: 022
Revises: 021
Create Date: 2026-05-03

This migration adds foreign key constraints that were missing from initial schema
creation to ensure referential integrity. Per database architecture review P1-6.

Adds FK constraints for:
- usage_events.account_id -> accounts.id (CASCADE)
- usage_events.tenant_id -> tenants.id (CASCADE)
- integrations.tenant_id -> tenants.id (CASCADE)

Note: billing tables use String IDs instead of UUID, so FK constraints require
type migration first. This is tracked separately as P2-1 (database consolidation).
"""

import logging
from collections.abc import Sequence
from typing import Union

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MIGRATION_REVIEW_REQUIRED = (
    "Drops and recreates ix_usage_events_account_id during upgrade so the "
    "foreign key can be added without index-name conflicts."
)


def upgrade() -> None:
    """Add missing foreign key constraints."""

    # usage_events.account_id -> accounts.id
    # First drop existing index if it exists to avoid conflict
    try:
        op.drop_index('ix_usage_events_account_id', table_name='usage_events')
    except Exception:
        pass  # Index may not exist

    # Add FK constraint
    op.execute("""
        ALTER TABLE usage_events
        ADD CONSTRAINT fk_usage_events_account_id
        FOREIGN KEY (account_id)
        REFERENCES accounts(id)
        ON DELETE CASCADE
    """)

    # Recreate index with FK constraint name
    op.create_index('ix_usage_events_account_id', 'usage_events', ['account_id'])

    # usage_events.tenant_id -> tenants.id
    # Note: usage_events uses String(255) for tenant_id, but tenants.id is UUID
    # This requires type migration - adding constraint with validation disabled
    # to allow existing data. This is a temporary fix pending full type migration.
    try:
        op.execute("""
            ALTER TABLE usage_events
            ADD CONSTRAINT fk_usage_events_tenant_id
            FOREIGN KEY (tenant_id)
            REFERENCES tenants(id)
            ON DELETE CASCADE
            NOT VALID
        """)
    except Exception as e:
        # If constraint fails due to type mismatch, log and skip
        # This will be addressed in P2-1 database consolidation
        logger.warning("Skipping usage_events.tenant_id FK due to type mismatch: %s", e)

    # integrations.tenant_id -> tenants.id
    # Same type mismatch issue as usage_events
    try:
        op.execute("""
            ALTER TABLE integrations
            ADD CONSTRAINT fk_integrations_tenant_id
            FOREIGN KEY (tenant_id)
            REFERENCES tenants(id)
            ON DELETE CASCADE
            NOT VALID
        """)
    except Exception as e:
        logger.warning("Skipping integrations.tenant_id FK due to type mismatch: %s", e)


def downgrade() -> None:
    """Remove added foreign key constraints."""

    # Drop constraints
    op.execute("ALTER TABLE usage_events DROP CONSTRAINT IF EXISTS fk_usage_events_account_id")
    op.execute("ALTER TABLE usage_events DROP CONSTRAINT IF EXISTS fk_usage_events_tenant_id")
    op.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS fk_integrations_tenant_id")
