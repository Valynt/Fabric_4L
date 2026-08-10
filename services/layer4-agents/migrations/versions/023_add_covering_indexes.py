"""Add covering indexes for common query patterns (P1-5).

Revision ID: 023
Revises: 022
Create Date: 2026-05-03

This migration adds covering indexes for frequently executed queries to eliminate
heap lookups and improve performance. Per database architecture review P1-5.

Covering indexes added for:
- accounts: (tenant_id, provider, sync_status) - account listing and filtering
- accounts: (tenant_id, owner_id, created_at) - user's accounts by creation date
- users: (tenant_id, email) - user lookup by email
- users: (tenant_id, role, created_at) - user listing by role
- audit_events: (tenant_id, resource_type, resource_id, timestamp) - entity audit trail
- feature_flags: (tenant_id, flag_key, enabled) - feature flag lookup

These indexes include all columns commonly returned in SELECT statements, allowing
PostgreSQL to satisfy queries from the index alone without heap access.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add covering indexes for common query patterns."""
    
    # accounts table - tenant-scoped account listing
    op.execute("""
        CREATE INDEX idx_accounts_tenant_provider_status_covering
        ON accounts (tenant_id, provider, sync_status)
        INCLUDE (name, owner_id, created_at, updated_at)
    """)
    
    # accounts table - user's accounts ordered by creation
    op.execute("""
        CREATE INDEX idx_accounts_tenant_owner_created_covering
        ON accounts (tenant_id, owner_id, created_at DESC)
        INCLUDE (name, provider, sync_status, last_synced_at)
    """)
    
    # users table - user lookup by email (tenant-scoped)
    op.execute("""
        CREATE INDEX idx_users_tenant_email_covering
        ON users (tenant_id, email)
        INCLUDE (display_name, role, created_at, last_login_at)
    """)
    
    # users table - user listing by role
    op.execute("""
        CREATE INDEX idx_users_tenant_role_created_covering
        ON users (tenant_id, role, created_at DESC)
        INCLUDE (display_name, email, last_login_at, status)
    """)
    
    # audit_events table - entity audit trail
    op.execute("""
        CREATE INDEX idx_audit_events_tenant_entity_created_covering
        ON audit_events (tenant_id, resource_type, resource_id, timestamp DESC)
        INCLUDE (action, user_id, details, outcome)
    """)
    
    # feature_flags table - feature flag lookup
    op.execute("""
        CREATE INDEX idx_feature_flags_tenant_name_enabled_covering
        ON feature_flags (tenant_id, flag_key, enabled)
        INCLUDE (description, updated_by, created_at, updated_at)
    """)
    


def downgrade() -> None:
    """Remove covering indexes."""
    
    op.drop_index('idx_accounts_tenant_provider_status_covering', table_name='accounts')
    op.drop_index('idx_accounts_tenant_owner_created_covering', table_name='accounts')
    op.drop_index('idx_users_tenant_email_covering', table_name='users')
    op.drop_index('idx_users_tenant_role_created_covering', table_name='users')
    op.drop_index('idx_audit_events_tenant_entity_created_covering', table_name='audit_events')
    op.drop_index('idx_feature_flags_tenant_name_enabled_covering', table_name='feature_flags')
