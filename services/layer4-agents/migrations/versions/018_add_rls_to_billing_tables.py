"""Add RLS policies to billing tables.

Revision ID: 018
Revises: 017
Create Date: 2026-04-25

Billing tables available by revision 017 (billing_customers,
billing_subscriptions, billing_webhook_events, and billing_usage_events) need
canonical RLS policies. Invoice, invoice-item, and charge tables are created
later by revision 024 and normalized by revision 025.
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

MIGRATION_REVIEW_REQUIRED = (
    "Security migration intentionally replaces pre-existing billing RLS policies "
    "with canonical tenant-safe definitions during deterministic upgrades."
)

# Billing tables that have tenant_id but no RLS policies yet
RLS_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
    "billing_usage_events",
]


def upgrade() -> None:
    """Enable RLS and create tenant isolation policies on billing tables."""
    for table in RLS_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Earlier billing migrations created policies on subsets of these tables.
        # Replace them explicitly so a fresh upgrade remains deterministic.
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")

        # Public access requires an exact tenant match. NULL-owned rows are never
        # globally visible through the tenant isolation policy.
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

        # Admin bypass policy for system-level operations
        # Allows admins to manage NULL tenant_id rows (system-level records)
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (
                    current_setting('app.tenant_id', true) = ''
                    OR tenant_id IS NULL
                )
        """)


def downgrade() -> None:
    """Remove RLS policies and disable RLS on billing tables."""
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
