"""add billing webhook inbox reliability fields

Revision ID: 037_add_billing_webhook_inbox_fields
Revises: 036_tenant_scoped_billing_customer_keys
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "037_add_billing_webhook_inbox_fields"
down_revision = "036_tenant_scoped_billing_customer_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_webhook_events", sa.Column("status", sa.String(length=32), nullable=False, server_default="processed"))
    op.add_column("billing_webhook_events", sa.Column("attempt_count", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("billing_webhook_events", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("billing_webhook_events", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_webhook_events", sa.Column("payload_hash", sa.String(length=128), nullable=True))
    op.create_index("ix_billing_webhook_events_status_retry", "billing_webhook_events", ["status", "next_retry_at"])
    op.alter_column("billing_webhook_events", "status", server_default=None)
    op.alter_column("billing_webhook_events", "attempt_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_billing_webhook_events_status_retry", table_name="billing_webhook_events")
    op.drop_column("billing_webhook_events", "payload_hash")
    op.drop_column("billing_webhook_events", "next_retry_at")
    op.drop_column("billing_webhook_events", "last_error")
    op.drop_column("billing_webhook_events", "attempt_count")
    op.drop_column("billing_webhook_events", "status")
