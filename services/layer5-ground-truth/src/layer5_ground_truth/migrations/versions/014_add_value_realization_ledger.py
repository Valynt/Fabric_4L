"""Add Value Realization Ledger for auditable ROI updates.

This migration adds:
1. value_realization_entries table - value realization records
2. value_realization_updates table - update records with audit trail

Phase 5: Create ValueRealizationLedger for auditable ROI updates
Issue: Value realization updates auditable
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "014_add_value_realization_ledger"
down_revision = "013_add_assumption_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create value_realization_entries table
    op.create_table(
        "value_realization_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("entry_type", sa.String(32), nullable=False, index=True),
        sa.Column("entry_name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("value_unit", sa.String(32), nullable=True),
        sa.Column("value_currency", sa.String(3), nullable=True),
        sa.Column("formula_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("formula_version", sa.String(64), nullable=True),
        sa.Column("benchmark_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("benchmark_version", sa.String(64), nullable=True),
        sa.Column("assumption_ids", postgresql.JSON(), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("business_case_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_value_realization_entries_tenant_type", "value_realization_entries", ["tenant_id", "entry_type"])
    op.create_index("ix_value_realization_entries_tenant_opportunity", "value_realization_entries", ["tenant_id", "opportunity_id"])
    op.create_index("ix_value_realization_entries_tenant_account", "value_realization_entries", ["tenant_id", "account_id"])

    # Create value_realization_updates table
    op.create_table(
        "value_realization_updates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("value_realization_entries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("previous_value", sa.Numeric(20, 6), nullable=True),
        sa.Column("new_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("value_change", sa.Numeric(20, 6), nullable=True),
        sa.Column("value_change_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("update_reason", sa.String(32), nullable=False, index=True),
        sa.Column("update_notes", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("updated_by_type", sa.String(32), nullable=False, default="human"),
        sa.Column("formula_id_at_update", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("formula_version_at_update", sa.String(64), nullable=True),
        sa.Column("benchmark_id_at_update", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("benchmark_version_at_update", sa.String(64), nullable=True),
        sa.Column("assumption_ids_at_update", postgresql.JSON(), nullable=True),
        sa.Column("calculation_metadata", postgresql.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_value_realization_updates_tenant_entry", "value_realization_updates", ["tenant_id", "entry_id"])
    op.create_index("ix_value_realization_updates_updated_by", "value_realization_updates", ["updated_by"])
    # NOTE: ix_value_realization_updates_updated_at is omitted because the
    # `updated_at` column above already has index=True, which causes Alembic to
    # create the index automatically. The explicit CREATE INDEX below duplicated
    # that work and failed with "relation already exists" on Postgres.
    op.create_index("ix_value_realization_updates_reason", "value_realization_updates", ["update_reason"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("value_realization_updates")
    op.drop_table("value_realization_entries")
