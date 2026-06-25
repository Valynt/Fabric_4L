"""Add tenant_id column and RLS policies to business_case_records.

Revision ID: 027
Revises: 026
Create Date: 2026-05-05
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id column, index, and RLS policies to business_case_records."""
    # Add tenant_id column with default for existing rows
    op.add_column(
        "business_case_records",
        sa.Column(
            "tenant_id",
            sa.String(length=100),
            nullable=False,
            server_default="default",
            comment="Tenant identifier for RLS isolation",
        ),
    )

    # Create index for tenant lookups
    op.create_index(
        "ix_business_case_records_tenant_id",
        "business_case_records",
        ["tenant_id"],
        unique=False,
    )

    # Enable RLS
    op.execute("ALTER TABLE business_case_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_case_records FORCE ROW LEVEL SECURITY")

    # Create strict tenant isolation policy (no NULL bypass)
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON business_case_records
            FOR ALL
            TO PUBLIC
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
    """)

    # Create admin bypass policy
    op.execute("""
        CREATE POLICY admin_bypass_policy ON business_case_records
            FOR ALL
            TO admin_role, system_role
            USING (current_setting('app.tenant_id', true) = '')
    """)

    # Remove server_default after backfill so new inserts must provide tenant_id
    op.alter_column(
        "business_case_records",
        "tenant_id",
        server_default=None,
    )


def downgrade() -> None:
    """Remove tenant_id column and RLS policies."""
    # Drop policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON business_case_records")
    op.execute("DROP POLICY IF EXISTS admin_bypass_policy ON business_case_records")

    # Disable RLS
    op.execute("ALTER TABLE business_case_records NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_case_records DISABLE ROW LEVEL SECURITY")

    # Drop index
    op.drop_index("ix_business_case_records_tenant_id", table_name="business_case_records")

    # Drop column
    op.drop_column("business_case_records", "tenant_id")
