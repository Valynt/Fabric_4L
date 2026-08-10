"""Add Row-Level Security (RLS) policies for tenant isolation (P0-07).

Revision ID: 007
Revises: 006
Create Date: 2026-04-13
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that have tenant_id and need RLS policies
RLS_TABLES = [
    "accounts",
    "account_notes",
    "crm_sync_states",
    "feature_flags",
    "audit_events",
    "oidc_sessions",
    "model_registry",
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
    # Restricted to explicit admin roles only - NEVER use PUBLIC
    for table in RLS_TABLES:
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)


def downgrade() -> None:
    """Remove RLS policies and disable RLS.

    Order matters:
    1. Revoke bypass grants from admin/system roles.
    2. Drop per-table policies (tenant_isolation_policy, admin_bypass_policy).
    3. NO FORCE ROW LEVEL SECURITY — must precede DISABLE to avoid Postgres
       errors on tables where FORCE was set explicitly.
    4. DISABLE ROW LEVEL SECURITY.
    """
    # Revoke bypass privilege from admin roles first (defense in depth)
    for table in RLS_TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM admin_role, system_role")

    # Drop policies before disabling RLS
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

    # Un-force before disabling — required order on all supported Postgres versions
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
