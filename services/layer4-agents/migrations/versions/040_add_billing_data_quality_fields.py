"""Add billing data quality and trust fields.

Adds updated_at to webhook events for freshness tracking and
source_system to usage events for provenance.

Revision ID: 040_add_billing_data_quality_fields
Revises: 039_add_user_email_hash_blind_index
Create Date: 2026-06-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "040_add_billing_data_quality_fields"
down_revision = "039_add_user_email_hash_blind_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Track when webhook event state last changed (retries, status transitions)
    op.add_column(
        "billing_webhook_events",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_billing_webhook_events_updated_at",
        "billing_webhook_events",
        ["updated_at"],
    )

    # Track provenance source for usage events (e.g. "api", "stripe", "batch_import")
    op.add_column(
        "billing_usage_events",
        sa.Column("source_system", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_billing_usage_events_source_system",
        "billing_usage_events",
        ["source_system"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_usage_events_source_system", table_name="billing_usage_events"
    )
    op.drop_column("billing_usage_events", "source_system")

    op.drop_index(
        "ix_billing_webhook_events_updated_at", table_name="billing_webhook_events"
    )
    op.drop_column("billing_webhook_events", "updated_at")
