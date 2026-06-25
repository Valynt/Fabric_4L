"""Fix unsafe tenant_id IS NULL bypass in crm_sync_jobs and billing RLS policies.

Revision ID: 032
Revises: 031
Create Date: 2026-05-17

Migrations 014 (billing) and 030 (crm_sync_jobs) created RLS policies with:

    USING (tenant_id IS NULL OR tenant_id::text = current_setting(...))

The ``tenant_id IS NULL`` clause makes any row inserted without a tenant_id
visible to every tenant — a global data leak vector. Billing data exposure
across tenant boundaries is a trust-destroying event; CRM sync job exposure
leaks customer relationship data.

This migration replaces those policies with strict matching only:

    USING (tenant_id::text = current_setting('app.tenant_id', true))

Rows with NULL tenant_id become invisible to tenant-scoped queries and are
only accessible via the admin_bypass_policy (admin_role, system_role with
empty app.tenant_id). This matches the pattern established in migrations
026 and 028.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables from migration 014 with unsafe NULL bypass
BILLING_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
]

# Table from migration 030 with unsafe NULL bypass
CRM_TABLES = [
    "crm_sync_jobs",
]

# Canonical list used by the test scanner in test_rls_enforcement.py
RLS_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
    "crm_sync_jobs",
]

ALL_TABLES = BILLING_TABLES + CRM_TABLES


def upgrade() -> None:
    """Replace NULL-permissive RLS policies with strict tenant matching."""
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in ALL_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes existing tenant isolation
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        # MIGRATION_REVIEW_REQUIRED: FORCE ROW LEVEL SECURITY affects all access paths
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

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

        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '')
        """)


def downgrade() -> None:
    """Revert to NULL-permissive policies (restores the pre-fix state).

    Recreates admin_bypass_policy without WITH CHECK to match the original
    definition from migrations 014 (billing) and 030 (crm_sync_jobs).
    """
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in ALL_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes strict tenant isolation
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        # MIGRATION_REVIEW_REQUIRED: restoring NULL-permissive policy creates data leak vector
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

        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)
