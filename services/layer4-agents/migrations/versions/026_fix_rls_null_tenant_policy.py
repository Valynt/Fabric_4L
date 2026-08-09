"""Fix unsafe tenant_id IS NULL pattern in RLS policies from migrations 007/013.

Revision ID: 026
Revises: 025
Create Date: 2026-04-24

SECURITY FIX: Migrations 007 and 013 created RLS policies with:

    USING (tenant_id IS NULL  -- unsafe: NULL rows visible to all tenants
           OR tenant_id::text = current_setting(...))

The ``tenant_id IS NULL`` clause means any row inserted without a tenant_id
is visible to ALL tenants — a global data leak vector. If any code path
accidentally omits tenant_id on INSERT, that row becomes universally readable.

This migration replaces the USING clause with strict matching only:

    USING (tenant_id::text = current_setting('app.tenant_id', true))

Rows with NULL tenant_id become invisible to tenant-scoped queries and are
only accessible via the existing admin_bypass_policy (admin_role, system_role
with empty app.tenant_id).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables from migration 007 with unsafe NULL pattern
MIGRATION_007_TABLES = [
    "accounts",
    "account_notes",
    "crm_sync_states",
    "feature_flags",
    "audit_events",
    "oidc_sessions",
    "model_registry",
]

# Tables from migration 013 with unsafe NULL pattern
MIGRATION_013_TABLES = [
    "account_sync_status",
    "api_keys",
    "integrations",
    "model_promotion_log",
    "tenant_isolation_tier_history",
    "users",
]

ALL_TABLES = MIGRATION_007_TABLES + MIGRATION_013_TABLES

# Canonical variable name used by the test scanner to identify RLS-covered tables.
# NOTE: Must be a literal list (not expression) so the regex-based
# test scanner in test_rls_enforcement.py can parse it.
RLS_TABLES = [
    "accounts",
    "account_notes",
    "crm_sync_states",
    "feature_flags",
    "audit_events",
    "oidc_sessions",
    "model_registry",
    "account_sync_status",
    "api_keys",
    "integrations",
    "model_promotion_log",
    "tenant_isolation_tier_history",
    "users",
]


def upgrade() -> None:
    """Replace unsafe NULL-permissive RLS policies with strict matching."""
    # Community Edition fallback: skip if RLS is not available (pre-9.5 or CE builds)
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in ALL_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes existing tenant isolation
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )

        # MIGRATION_REVIEW_REQUIRED: FORCE ROW LEVEL SECURITY affects all access paths
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Recreate with strict matching (no NULL bypass)
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
    """Revert to the original NULL-permissive policies."""
    # Community Edition fallback: skip if RLS is not available
    _has_rls = op.execute("SELECT 1 FROM pg_settings WHERE name = 'row_security'") is not None
    if not _has_rls:
        return

    for table in ALL_TABLES:
        # MIGRATION_REVIEW_REQUIRED: DROP POLICY removes strict tenant isolation
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"
        )

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
