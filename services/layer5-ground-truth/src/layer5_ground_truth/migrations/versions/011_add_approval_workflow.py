"""Add approval workflow framework for governance artifacts.

This migration adds:
1. approval_requests table - individual approval requests
2. approval_decisions table - decision records
3. approval_workflows table - workflow definitions

Phase 2: Generic approval workflow for governance artifacts
Issue A: Missing generalized approval workflow for high-impact assumptions/formulas/benchmarks
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "011_add_approval_workflow"
down_revision = "010_harden_validation_event_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create approval_requests table
    op.create_table(
        "approval_requests",
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
        sa.Column("entity_type", sa.String(32), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("entity_version", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="draft", index=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("request_metadata", postgresql.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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

    # Create indexes for approval_requests
    op.create_index(
        "ix_approval_requests_tenant_entity",
        "approval_requests",
        ["tenant_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_approval_requests_tenant_status",
        "approval_requests",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_approval_requests_requested_by",
        "approval_requests",
        ["requested_by"],
    )

    # Create approval_decisions table
    op.create_table(
        "approval_decisions",
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
            "approval_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("decision_type", sa.String(32), nullable=False),
        sa.Column("decided_by", sa.String(255), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("decision_metadata", postgresql.JSON(), nullable=True),
        sa.Column("approval_level", sa.Integer(), nullable=False, default=1),
        sa.Column("escalated_from_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes for approval_decisions
    op.create_index(
        "ix_approval_decisions_tenant_request",
        "approval_decisions",
        ["tenant_id", "approval_request_id"],
    )
    op.create_index(
        "ix_approval_decisions_decided_by",
        "approval_decisions",
        ["decided_by"],
    )

    # Create approval_workflows table
    op.create_table(
        "approval_workflows",
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
        sa.Column("entity_type", sa.String(32), nullable=False, unique=True),
        sa.Column("workflow_name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_approval_levels", sa.Integer(), nullable=False, default=1),
        sa.Column("auto_approve_threshold", sa.Integer(), nullable=True),
        sa.Column("require_evidence", sa.Boolean(), nullable=False, default=True),
        sa.Column("require_justification", sa.Boolean(), nullable=False, default=True),
        sa.Column("approver_roles", postgresql.JSON(), nullable=False, default=list),
        sa.Column("escalation_roles", postgresql.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("version", sa.String(64), nullable=False, default="1.0"),
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

    # Create indexes for approval_workflows
    op.create_index(
        "ix_approval_workflows_tenant_entity",
        "approval_workflows",
        ["tenant_id", "entity_type"],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("approval_workflows")
    op.drop_table("approval_decisions")
    op.drop_table("approval_requests")
