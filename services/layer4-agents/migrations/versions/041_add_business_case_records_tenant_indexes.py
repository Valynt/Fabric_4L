"""Add the business_case_records tenant/status composite index.

Revision 027 already created the single-column tenant index. This revision adds
only the missing composite index used by tenant-scoped status queries.

Revision ID: 041_add_business_case_records_tenant_indexes
Revises: 040_add_billing_data_quality_fields
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op

revision = "041_add_business_case_records_tenant_indexes"
down_revision = "040_add_billing_data_quality_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_business_case_records_tenant_status",
        "business_case_records",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_case_records_tenant_status",
        table_name="business_case_records",
    )
