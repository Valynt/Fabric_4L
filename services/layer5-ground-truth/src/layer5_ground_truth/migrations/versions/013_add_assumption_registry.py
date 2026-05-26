"""Add Assumption registry with evidence linkage.

This migration adds:
1. assumptions table - high-impact assumptions
2. assumption_evidence table - evidence supporting assumptions
3. assumption_reviews table - review records

Phase 4: Create Assumption registry with evidence linkage
Issue: Explicit assumption governance + evidence linkage + reviewability
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "013_add_assumption_registry"
down_revision = "012_add_governance_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create assumptions table
    op.create_table(
        "assumptions",
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
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("assumption_type", sa.String(32), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSON(), nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("impact_level", sa.String(32), nullable=False, index=True),
        sa.Column("sensitivity_analysis", postgresql.JSON(), nullable=True),
        sa.Column("truth_object_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, default=0),
        sa.Column("status", sa.String(32), nullable=False, default="draft", index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applies_to_opportunity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("applies_to_formula_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
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

    op.create_index("ix_assumptions_tenant_type", "assumptions", ["tenant_id", "assumption_type"])
    op.create_index("ix_assumptions_tenant_slug", "assumptions", ["tenant_id", "slug"])
    op.create_index("ix_assumptions_tenant_impact", "assumptions", ["tenant_id", "impact_level"])
    op.create_index("ix_assumptions_tenant_status", "assumptions", ["tenant_id", "status"])

    # Create assumption_evidence table
    op.create_table(
        "assumption_evidence",
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
            "assumption_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assumptions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("truth_object_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_title", sa.String(512), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(32), nullable=False, default="medium"),
        sa.Column("relevance", sa.String(32), nullable=False, default="medium"),
        sa.Column("added_by", sa.String(255), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_index("ix_assumption_evidence_tenant_assumption", "assumption_evidence", ["tenant_id", "assumption_id"])
    op.create_index("ix_assumption_evidence_truth_object", "assumption_evidence", ["truth_object_id"])

    # Create assumption_reviews table
    op.create_table(
        "assumption_reviews",
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
            "assumption_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assumptions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("review_type", sa.String(32), nullable=False),
        sa.Column("reviewed_by", sa.String(255), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=True),
        sa.Column("review_metadata", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_assumption_reviews_tenant_assumption", "assumption_reviews", ["tenant_id", "assumption_id"])
    op.create_index("ix_assumption_reviews_reviewed_by", "assumption_reviews", ["reviewed_by"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("assumption_reviews")
    op.drop_table("assumption_evidence")
    op.drop_table("assumptions")
