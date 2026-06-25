"""Fix NULL-permissive RLS policies introduced after migration 026.

Revision ID: 033
Revises: 032
Create Date: 2026-05-17

SECURITY FIX: Three migration groups created tables with the unsafe pattern:

    USING (tenant_id IS NULL OR tenant_id::text = current_setting(...))

This allows any row inserted without a tenant_id to be visible to ALL tenants.
Migration 026 fixed the original 007/013 tables; migration 028 fixed the 027
batch. This migration closes the remaining gaps:

  - Billing tables (025): billing_charges, billing_customers,
    billing_invoice_items, billing_invoices, billing_subscriptions,
    billing_usage_events, billing_webhook_events
  - Company knowledge tables (029): company_knowledge_profiles, icp_profiles,
    knowledge_sources, value_extraction_records
  - CRM sync jobs (030): crm_sync_jobs

The fix replaces the USING clause with strict matching only:

    USING (tenant_id::text = current_setting('app.tenant_id', true))

Rows with NULL tenant_id become invisible to tenant-scoped queries and are
only accessible via the existing admin_bypass_policy (admin_role, system_role
with empty app.tenant_id setting).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Billing tables from migration 025 — NULL-leaky policy never superseded.
BILLING_TABLES = [
    "billing_charges",
    "billing_customers",
    "billing_invoice_items",
    "billing_invoices",
    "billing_subscriptions",
    "billing_usage_events",
    "billing_webhook_events",
]

# Company knowledge tables from migration 029 — created after 028 ran.
COMPANY_KNOWLEDGE_TABLES = [
    "company_knowledge_profiles",
    "icp_profiles",
    "knowledge_sources",
    "value_extraction_records",
]

# CRM sync jobs from migration 030.
CRM_TABLES = [
    "crm_sync_jobs",
]

# Canonical list used by the RLS enforcement test scanner.
# Must be a literal list (not an expression) so the regex-based scanner in
# tests/security/test_rls_enforcement.py can parse it.
RLS_TABLES = [
    "billing_charges",
    "billing_customers",
    "billing_invoice_items",
    "billing_invoices",
    "billing_subscriptions",
    "billing_usage_events",
    "billing_webhook_events",
    "company_knowledge_profiles",
    "icp_profiles",
    "knowledge_sources",
    "value_extraction_records",
    "crm_sync_jobs",
]

ALL_TABLES = BILLING_TABLES + COMPANY_KNOWLEDGE_TABLES + CRM_TABLES


def upgrade() -> None:
    """Replace NULL-permissive tenant_isolation_policy with strict matching.

    Also creates admin_bypass_policy for the four billing tables that 032 did
    not cover (billing_charges, billing_invoice_items, billing_invoices,
    billing_usage_events). Company-knowledge and CRM tables already have
    admin_bypass_policy from migrations 028 and 032 respectively.
    """
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    # Tables that need admin_bypass_policy created — not covered by 028 or 032.
    _NEEDS_ADMIN_BYPASS = {
        "billing_charges",
        "billing_invoice_items",
        "billing_invoices",
        "billing_usage_events",
    }

    for table in ALL_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes existing tenant isolation
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )
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
        if table in _NEEDS_ADMIN_BYPASS:
            op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
            op.execute(f"""
                CREATE POLICY admin_bypass_policy ON {table}
                    FOR ALL
                    TO admin_role, system_role
                    USING (current_setting('app.tenant_id', true) = '')
                    WITH CHECK (current_setting('app.tenant_id', true) = '')
            """)


def downgrade() -> None:
    """Remove policies created by 033's upgrade.

    Drops tenant_isolation_policy (and admin_bypass_policy where 033 created
    it) on the 8 tables exclusively owned by this migration. Does NOT
    re-apply NULL-permissive policies: the tables that 028 and 032 hardened
    remain at their hardened state after this downgrade, which is correct —
    those migrations are still marked applied in alembic_version.

    Tables owned by 032 (billing_customers, billing_subscriptions,
    billing_webhook_events, crm_sync_jobs) are not touched.
    """
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    _033_ONLY_TABLES = [
        t for t in ALL_TABLES
        if t not in {
            "billing_customers",
            "billing_subscriptions",
            "billing_webhook_events",
            "crm_sync_jobs",
        }
    ]
    _NEEDS_ADMIN_BYPASS = {
        "billing_charges",
        "billing_invoice_items",
        "billing_invoices",
        "billing_usage_events",
    }
    for table in _033_ONLY_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes tenant isolation enforcement
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        if table in _NEEDS_ADMIN_BYPASS:
            op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
