"""Add missing Row-Level Security (RLS) policies for tenant isolation.

Revision ID: 013
Revises: 012_add_tenant_isolation_tier_history
Create Date: 2026-04-23

This migration adds RLS policies to tables created after migration 007
that have tenant_id columns and need tenant isolation.

Affected tables:
- account_sync_status
- api_keys
- integrations
- model_promotion_log
- tenant_isolation_tier_history
- users
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that need RLS policies (have tenant_id but missing from migration 007)
RLS_TABLES = [
    "account_sync_status",
    "api_keys",
    "integrations",
    "model_promotion_log",
    "tenant_isolation_tier_history",
    "users",
]


def upgrade() -> None:
    """Enable RLS and create policies for tenant isolation."""
    # Enable RLS on each table
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # Create tenant isolation policy for each table
    # Uses current_setting('app.tenant_id') set by SET LOCAL
    for table in RLS_TABLES:
        # Tenant users can only see their own rows
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id IS NULL OR
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id IS NULL OR
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
        """)

    # Create bypass policy for admin/system operations
    for table in RLS_TABLES:
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)


def downgrade() -> None:
    """Remove RLS policies and disable RLS."""
    # MIGRATION_REVIEW_REQUIRED: REVOKE is destructive — removes all privileges from admin/system roles
    # Community Edition fallback: skip if running on PostgreSQL CE (pre-9.5 or RLS unavailable)
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security' AND setting = 'on'") is not None
    if not _has_rls:
        return  # CE fallback: RLS not available, skip policy operations
    for table in RLS_TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM admin_role, system_role")

    # MIGRATION_REVIEW_REQUIRED: DROP POLICY permanently removes tenant isolation enforcement
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

    # MIGRATION_REVIEW_REQUIRED: DISABLE ROW LEVEL SECURITY removes all tenant isolation
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
