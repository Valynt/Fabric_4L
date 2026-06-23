"""Fix RLS policies to use tenant_id instead of organization_id.

Revision ID: 017
Revises: 016
Create Date: 2026-06-02

Migration 004 created RLS policies referencing organization_id.
Migration 006 renamed organization_id to tenant_id but did not update the RLS policies.
This migration drops the broken policies and recreates them using the correct tenant_id column.

Also verifies and aligns crawl_decisions policies (already using tenant_id from 013).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tenant-scoped tables that should have RLS policies
RLS_TABLES = [
    "scraping_targets",
    "scraping_jobs",
    "raw_content",
    "extracted_data",
    "compliance_logs",
    "proxy_pools",
    "job_stage_details",
    "job_errors",
    "crawl_decisions",
]


def upgrade() -> None:
    """Drop broken organization_id-based policies and recreate with tenant_id."""
    # Ensure roles exist (idempotent)
    op.execute("DO $$ BEGIN CREATE ROLE admin_role; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE ROLE system_role; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")

    for table in RLS_TABLES:
        # Drop old policies if they exist (idempotent)
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        # Enable RLS (idempotent if already enabled)
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Create tenant isolation policy using tenant_id
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
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)


def downgrade() -> None:
    """Revert RLS policies to organization_id (restores pre-fix broken state)."""
    for table in RLS_TABLES:
        # Drop tenant_id-based policies
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        # Recreate organization_id-based policies (matches migration 004)
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                TO PUBLIC
                USING (
                    organization_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    organization_id::text = current_setting('app.tenant_id', true)
                )
        """)

        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)
