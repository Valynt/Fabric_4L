"""Drop legacy model registry RLS policies created by migration 003.

Revision ID: 018
Revises: 017
Create Date: 2026-06-16

Migration 003 originally created model registry RLS policies that referenced
the wrong per-tenant GUC. Migration 005 later added correct policies using
app.tenant_id, leaving the legacy policies with the wrong GUC in place on
existing deployments. This migration drops those legacy policies.
"""

from __future__ import annotations

from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | None = None
depends_on: str | None = None

# Tables affected by the legacy policies in migration 003.
MODEL_REGISTRY_TABLES = [
    "model_versions",
    "model_deployments",
    "model_evaluations",
]


def upgrade() -> None:
    """Drop the legacy model registry isolation policies."""
    for table in MODEL_REGISTRY_TABLES:
        op.execute(f'DROP POLICY IF EXISTS {table}_isolation_policy ON "{table}"')


def downgrade() -> None:
    """Recreate the model registry policies using the correct app.tenant_id GUC."""
    for table in MODEL_REGISTRY_TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f"""
            CREATE POLICY {table}_isolation_policy ON "{table}"
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
        """)
