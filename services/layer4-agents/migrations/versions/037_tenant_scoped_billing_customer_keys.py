"""Enforce tenant-scoped billing customer keys and FK constraints.

Revision ID: 037_tenant_scoped_billing_customer_keys
Revises: 036_add_billing_customer_sync_state
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "037_tenant_scoped_billing_customer_keys"
down_revision = "036_add_billing_customer_sync_state"
branch_labels = None
depends_on = None

MIGRATION_REVIEW_REQUIRED = (
    "Tenant-safety migration intentionally replaces customer-only foreign keys "
    "with tenant-scoped composite foreign keys during upgrade."
)


def upgrade() -> None:
    # Backfill tenant IDs before tightening constraints.
    op.execute("""
    UPDATE billing_subscriptions s
    SET tenant_id = c.tenant_id
    FROM billing_customers c
    WHERE s.customer_id = c.id
      AND s.tenant_id IS NULL
      AND c.tenant_id IS NOT NULL
    """)
    for table in ("billing_usage_events", "billing_invoices", "billing_charges"):
        op.execute(f"""
        UPDATE {table} t
        SET tenant_id = c.tenant_id
        FROM billing_customers c
        WHERE t.customer_id = c.id
          AND t.tenant_id IS NOT NULL
          AND c.tenant_id IS NOT NULL
          AND t.tenant_id <> c.tenant_id
        """)

    op.alter_column("billing_customers", "tenant_id", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("billing_subscriptions", "tenant_id", existing_type=sa.String(length=255), nullable=False)

    op.drop_constraint("billing_subscriptions_customer_id_fkey", "billing_subscriptions", type_="foreignkey")
    op.create_foreign_key(
        "fk_billing_subscriptions_tenant_customer",
        "billing_subscriptions",
        "billing_customers",
        ["tenant_id", "customer_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_billing_usage_events_tenant_customer",
        "billing_usage_events",
        "billing_customers",
        ["tenant_id", "customer_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_billing_invoices_tenant_customer",
        "billing_invoices",
        "billing_customers",
        ["tenant_id", "customer_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_billing_charges_tenant_customer",
        "billing_charges",
        "billing_customers",
        ["tenant_id", "customer_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_billing_charges_tenant_customer", "billing_charges", type_="foreignkey")
    op.drop_constraint("fk_billing_invoices_tenant_customer", "billing_invoices", type_="foreignkey")
    op.drop_constraint("fk_billing_usage_events_tenant_customer", "billing_usage_events", type_="foreignkey")
    op.drop_constraint("fk_billing_subscriptions_tenant_customer", "billing_subscriptions", type_="foreignkey")

    op.create_foreign_key(
        "billing_subscriptions_customer_id_fkey",
        "billing_subscriptions",
        "billing_customers",
        ["customer_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.alter_column("billing_subscriptions", "tenant_id", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("billing_customers", "tenant_id", existing_type=sa.String(length=255), nullable=True)
