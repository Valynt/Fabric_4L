"""Harden tenant isolation for tables that gained tenant identity after creation.

Revision ID: 045_harden_late_tenant_tables
Revises: 044_repair_integration_state_drift
Create Date: 2026-07-31
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "045_harden_late_tenant_tables"
down_revision: Union[str, None] = "044_repair_integration_state_drift"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = [
    "account_sync_status",
    "model_promotion_log",
]


def upgrade() -> None:
    """Add promotion-log ownership and enforce strict tenant policies."""
    op.add_column(
        "model_promotion_log",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("""
        UPDATE model_promotion_log AS promotion
        SET tenant_id = model.tenant_id
        FROM model_versions AS model
        WHERE model.id = promotion.model_version_id
    """)
    op.alter_column("model_promotion_log", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_model_promotion_log_tenant_id",
        "model_promotion_log",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_model_promotion_log_tenant_id",
        "model_promotion_log",
        ["tenant_id"],
    )

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
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
    """Remove the late-table policies and promotion-log tenant column."""
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_model_promotion_log_tenant_id",
        table_name="model_promotion_log",
    )
    op.drop_constraint(
        "fk_model_promotion_log_tenant_id",
        "model_promotion_log",
        type_="foreignkey",
    )
    op.drop_column("model_promotion_log", "tenant_id")
