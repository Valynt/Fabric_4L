"""Fix billing RLS policies to use consistent app.tenant_id setting.

Revision ID: 025
Revises: 024
Create Date: 2026-04-24

SECURITY FIX: Migration 016 created RLS policies on billing_invoices,
billing_invoice_items, and billing_charges using 'app.current_tenant'
instead of 'app.tenant_id'. The rest of the codebase (get_db_from_context,
migrations 007, 013, 014, 015) all use 'app.tenant_id'. This mismatch
means the RLS policies on these three tables NEVER match, effectively
making them invisible to tenant-scoped queries while appearing to have
RLS protection.

Additionally, the bypass mechanism used 'app.bypass_rls' which doesn't
exist anywhere in the codebase. The standard pattern uses admin_role and
system_role with empty tenant_id check.

This migration:
1. Drops the broken policies from migration 016
2. Recreates them using the canonical 'app.tenant_id' pattern
3. Adds FORCE ROW LEVEL SECURITY (missing from 016)
4. Uses the standard admin_bypass_policy pattern

Also adds missing RLS policies for billing_customers, billing_subscriptions,
and billing_webhook_events where migration 014 used the unsafe
'tenant_id IS NULL' pattern that leaks rows without tenant_id to all tenants.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MIGRATION_REVIEW_REQUIRED = (
    "Security migration intentionally drops broken or unsafe billing RLS "
    "policies during upgrade before recreating tenant-safe replacements."
)


# Tables from migration 016 with broken policies
BROKEN_POLICY_TABLES = [
    "billing_invoices",
    "billing_invoice_items",
    "billing_charges",
]

# Tables from migration 014 with unsafe NULL pattern
UNSAFE_NULL_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_usage_events",
    "billing_webhook_events",
]

# Canonical list for gate test scanner (union of both sets above).
# NOTE: Must be a literal list (not expression) so the regex-based
# test scanner in test_rls_enforcement.py can parse it.
RLS_TABLES = [
    "billing_invoices",
    "billing_invoice_items",
    "billing_charges",
    "billing_customers",
    "billing_subscriptions",
    "billing_usage_events",
    "billing_webhook_events",
]


def upgrade() -> None:
    """Fix billing RLS policies to use canonical app.tenant_id."""

    # ================================================================
    # Part 1: Fix migration 016 tables (wrong setting name)
    # ================================================================

    # Drop the broken policies that reference app.current_tenant
    for table in BROKEN_POLICY_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}"
        )

    # Add FORCE ROW LEVEL SECURITY (missing from 016)
    for table in BROKEN_POLICY_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # Create correct policies using app.tenant_id
    for table in BROKEN_POLICY_TABLES:
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

    # Create admin bypass policies (standard pattern)
    for table in BROKEN_POLICY_TABLES:
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)

    # ================================================================
    # Part 2: Fix migration 014 tables (unsafe NULL pattern)
    # ================================================================

    # Drop the unsafe policies that allow tenant_id IS NULL to match all
    for table in UNSAFE_NULL_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )

    # Recreate with strict matching (no NULL bypass)
    # NULL tenant_id rows are only visible to admin/system roles
    for table in UNSAFE_NULL_TABLES:
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


def downgrade() -> None:
    """Revert to the broken/unsafe policies from migrations 014 and 016."""

    # ================================================================
    # Revert Part 1: Restore broken 016 policies
    # ================================================================
    for table in BROKEN_POLICY_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )
        op.execute(
            f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}"
        )

    for table in BROKEN_POLICY_TABLES:
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR OR
                   current_setting('app.bypass_rls', true)::BOOLEAN = true)
        """)

    # ================================================================
    # Revert Part 2: Restore unsafe 014 policies
    # ================================================================
    for table in UNSAFE_NULL_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )

    for table in UNSAFE_NULL_TABLES:
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
