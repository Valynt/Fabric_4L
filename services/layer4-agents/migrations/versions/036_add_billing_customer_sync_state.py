"""Add explicit Stripe sync state fields for billing customers.

Revision ID: 036_add_billing_customer_sync_state
Revises: 035_add_billing_plan_versions
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "036_add_billing_customer_sync_state"
down_revision = "035_add_billing_plan_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_customers", sa.Column("stripe_sync_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("billing_customers", sa.Column("stripe_sync_error", sa.Text(), nullable=True))
    op.add_column("billing_customers", sa.Column("stripe_sync_attempted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_billing_customers_stripe_sync_status", "billing_customers", ["stripe_sync_status"])
    op.alter_column("billing_customers", "stripe_sync_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_billing_customers_stripe_sync_status", table_name="billing_customers")
    op.drop_column("billing_customers", "stripe_sync_attempted_at")
    op.drop_column("billing_customers", "stripe_sync_error")
    op.drop_column("billing_customers", "stripe_sync_status")
