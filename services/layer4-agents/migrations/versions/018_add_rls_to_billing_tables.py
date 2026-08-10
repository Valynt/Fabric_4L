"""Add RLS policies to billing tables.

Revision ID: 018
Revises: 017
Create Date: 2026-04-25

Billing tables (billing_customers, billing_subscriptions, billing_webhook_events,
billing_usage_events, billing_invoices, billing_invoice_items, billing_charges)
were added in migrations 009/015/016 with tenant_id columns but without RLS
policies.  This migration closes that gap (Phase 1, Task 1.6).
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

# Billing tables that have tenant_id but no RLS policies yet
RLS_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
    "billing_usage_events",
    "billing_invoices",
    "billing_invoice_items",
    "billing_charges",
]


def upgrade() -> None:
    """Enable RLS and create tenant isolation policies on billing tables."""
    for table in RLS_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Tenant isolation policy — matches the pattern from migration 007/013
        # SECURITY FIX: Removed tenant_id IS NULL check that caused global data leak
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
