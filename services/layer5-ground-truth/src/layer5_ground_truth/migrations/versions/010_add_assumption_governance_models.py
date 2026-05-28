"""Add Layer 5 assumption governance models.

Revision ID: 010
Revises: 009
Create Date: 2026-05-25
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010a"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assumption_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("impact_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("is_approved_for_use", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_assumption_records_tenant_id", "assumption_records", ["tenant_id"])

    op.create_table(
        "formula_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assumption_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assumption_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="draft"),
    )
    op.create_table(
        "benchmark_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dataset_uri", sa.String(length=1024), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="draft"),
    )
    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("min_impact_threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("required_reviewer_role", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="published"),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assumption_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assumption_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policy_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_table(
        "approval_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_role", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("approval_decisions")
    op.drop_table("approval_requests")
    op.drop_table("policy_rules")
    op.drop_table("benchmark_datasets")
    op.drop_table("formula_definitions")
    op.drop_index("ix_assumption_records_tenant_id", table_name="assumption_records")
    op.drop_table("assumption_records")
