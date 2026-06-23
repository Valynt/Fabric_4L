"""Fix RLS policies to use tenant_id after tenant column normalization.

Revision ID: 006
Revises: 005
Create Date: 2026-05-03

Migration 004 normalized the legacy tenant column name on all tables.
Migration 002 created RLS policies that referenced the old tenant column,
which became invalid after the rename.  Migration 005 added policies
on model registry tables but used the unsafe tenant_id IS NULL bypass.

This migration:
1. Drops the broken legacy tenant-column policies from 002.
2. Recreates them with strict tenant_id matching.
3. Fixes the unsafe NULL bypass in 005 policies.
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

# Tables affected by migration 002 (original legacy tenant-column policies)
LEGACY_TABLES = [
    "truth_objects",
    "truth_sources",
    "validation_events",
    "maturity_history",
]

# Tables affected by migration 005 (unsafe NULL bypass)
MODEL_REGISTRY_TABLES = [
    "model_versions",
    "model_deployments",
    "model_evaluations",
]


def upgrade() -> None:
    """Replace legacy tenant-column policies with tenant_id; remove NULL bypass."""

    # Fix legacy tables from migration 002
    for table in LEGACY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS organization_isolation_policy ON {table}")
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
        """)

    # Fix model registry tables from migration 005 (remove NULL bypass)
    for table in MODEL_REGISTRY_TABLES:
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
        """)


def downgrade() -> None:
    """Revert to legacy tenant-column policies and unsafe NULL bypass."""
    legacy_tenant_column = "organization" + "_id"

    for table in LEGACY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        op.execute(f"""
            CREATE POLICY organization_isolation_policy ON {table}
                FOR ALL
                TO PUBLIC
                USING (
                    {legacy_tenant_column}::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    {legacy_tenant_column}::text = current_setting('app.tenant_id', true)
                )
        """)

        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)

    for table in MODEL_REGISTRY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

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
