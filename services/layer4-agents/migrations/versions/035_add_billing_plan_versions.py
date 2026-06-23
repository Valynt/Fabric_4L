"""add billing plan versioning

Revision ID: 035_add_billing_plan_versions
Revises: 034_add_harness_claim_validation_results
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "035_add_billing_plan_versions"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_plan_versions",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("usage_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("config_signature", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "plan_id", "version", name="uq_billing_plan_versions_scope_plan_version"),
    )
    op.create_index("ix_billing_plan_versions_scope_effective", "billing_plan_versions", ["tenant_id", "plan_id", "effective_from"])

    op.add_column("billing_subscriptions", sa.Column("plan_version_id", sa.String(length=100), nullable=True))
    op.create_index("ix_billing_subscriptions_plan_version_id", "billing_subscriptions", ["plan_version_id"])
    op.create_foreign_key(
        "fk_billing_subscriptions_plan_version_id",
        "billing_subscriptions",
        "billing_plan_versions",
        ["plan_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_billing_subscriptions_plan_version_id", "billing_subscriptions", type_="foreignkey")
    op.drop_index("ix_billing_subscriptions_plan_version_id", table_name="billing_subscriptions")
    op.drop_column("billing_subscriptions", "plan_version_id")
    op.drop_index("ix_billing_plan_versions_scope_effective", table_name="billing_plan_versions")
    op.drop_table("billing_plan_versions")
