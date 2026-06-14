"""Add Row-Level Security (RLS) policies for tenant isolation (P0-07).

Revision ID: 002
Revises: 20240101_0000_a1b2c3d4e5f6_initial_ground_truth_schema
Create Date: 2026-04-13

Layer 5 uses tenant_id for multi-tenancy.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that have tenant_id and need RLS policies
RLS_TABLES = [
    "truth_objects",
    "truth_sources",
    "validation_events",
    "maturity_history",
]


def upgrade() -> None:
    """Enable RLS and create policies for tenant isolation."""
    # Ensure required roles exist for admin bypass policies
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin_role') THEN CREATE ROLE admin_role NOLOGIN; END IF; END $$")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'system_role') THEN CREATE ROLE system_role NOLOGIN; END IF; END $$")

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
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
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
    """Remove RLS policies and disable RLS."""
    # Revoke bypass privilege from admin roles first (defense in depth)
    for table in RLS_TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM admin_role, system_role")

    # Drop policies
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

    # Disable RLS
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
