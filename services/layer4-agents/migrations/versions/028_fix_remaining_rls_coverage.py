"""Apply strict RLS policies to remaining tenant-scoped Layer 4 tables.

Revision ID: 028
Revises: 027
Create Date: 2026-05-08
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = [
    "business_case_records",
    "company_knowledge_profiles",
    "icp_profiles",
    "knowledge_sources",
    "saved_business_case_scenarios",
    "value_extraction_records",
    "workspace_tab_data",
]


def upgrade() -> None:
    """Enforce strict tenant matching with privileged admin/system bypass only."""
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # MIGRATION_REVIEW_REQUIRED: FORCE ROW LEVEL SECURITY affects table owner access
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes existing tenant isolation
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

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
    """Remove policies added by this hardening migration."""
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in RLS_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes tenant isolation enforcement
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
        # MIGRATION_REVIEW_REQUIRED: NO FORCE ROW LEVEL SECURITY relaxes security for table owners
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
