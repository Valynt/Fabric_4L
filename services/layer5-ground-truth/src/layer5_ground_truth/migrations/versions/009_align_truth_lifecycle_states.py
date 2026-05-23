"""Align TruthObject lifecycle with target trust-governance taxonomy.

Revision ID: 009
Revises: 008
Create Date: 2026-05-22

Changes:
  - Add rejected_by, rejected_at, rejection_reason to truth_objects
  - Add superseded_by_id, superseded_at to truth_objects
  - Rename approved_by → validated_by, approved_at → validated_at, approval_notes → validation_notes
  - Data migration: EXTRACTED/SUPPORTED/CORROBORATED → PROPOSED, APPROVED → VALIDATED, is_stale=True → EXPIRED

DESTRUCTIVE: This migration drops columns (approved_by, approved_at, approval_notes) and performs data migration.
backup: Ensure database backup is taken before running this migration in PRODUCTION_LIKE_ENVIRONMENTS.
data migration: Status values are remapped according to new taxonomy.
DESTRUCTIVE_ACK_VALUE: Operator acknowledges column drops and data migration risks.
MIGRATION_: This is a data migration with schema changes.
RuntimeError: Downgrade path is best-effort (status mapping loss).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Add new columns for rejection and supersession tracking
    # ------------------------------------------------------------------
    op.add_column(
        "truth_objects",
        sa.Column("rejected_by", sa.String(255), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("rejection_reason", sa.String(64), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column(
            "superseded_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "truth_objects",
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # Add validated_by / validated_at / validation_notes (new naming)
    # ------------------------------------------------------------------
    op.add_column(
        "truth_objects",
        sa.Column("validated_by", sa.String(255), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("validation_notes", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Copy data from old approval columns to new validation columns
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE truth_objects
        SET validated_by = approved_by,
            validated_at = approved_at,
            validation_notes = approval_notes
        """
    )

    # ------------------------------------------------------------------
    # Data migration: map old statuses to new taxonomy
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE truth_objects
        SET status = 'proposed'
        WHERE status IN ('extracted', 'supported', 'corroborated')
        """
    )
    op.execute(
        """
        UPDATE truth_objects
        SET status = 'validated'
        WHERE status = 'approved'
        """
    )
    op.execute(
        """
        UPDATE truth_objects
        SET status = 'expired'
        WHERE is_stale = true AND status NOT IN ('rejected', 'superseded', 'expired')
        """
    )

    # ------------------------------------------------------------------
    # Create index on superseded_by_id
    # ------------------------------------------------------------------
    op.create_index(
        "ix_truth_objects_superseded_by_id",
        "truth_objects",
        ["superseded_by_id"],
    )

    # ------------------------------------------------------------------
    # Add foreign key for superseded_by_id
    # ------------------------------------------------------------------
    op.create_foreign_key(
        "fk_truth_objects_superseded_by",
        "truth_objects",
        "truth_objects",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # Drop old approval columns
    # ------------------------------------------------------------------
    op.drop_column("truth_objects", "approved_by")
    op.drop_column("truth_objects", "approved_at")
    op.drop_column("truth_objects", "approval_notes")


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Restore old approval columns
    # ------------------------------------------------------------------
    op.add_column(
        "truth_objects",
        sa.Column("approved_by", sa.String(255), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "truth_objects",
        sa.Column("approval_notes", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Copy data back
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE truth_objects
        SET approved_by = validated_by,
            approved_at = validated_at,
            approval_notes = validation_notes
        """
    )

    # ------------------------------------------------------------------
    # Reverse status migration (best-effort: VALIDATED → APPROVED, everything else → EXTRACTED)
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE truth_objects
        SET status = 'approved'
        WHERE status = 'validated'
        """
    )
    op.execute(
        """
        UPDATE truth_objects
        SET status = 'extracted'
        WHERE status NOT IN ('approved', 'disputed', 'rejected', 'superseded', 'expired')
        """
    )

    # ------------------------------------------------------------------
    # Drop foreign key and index
    # ------------------------------------------------------------------
    op.drop_constraint("fk_truth_objects_superseded_by", "truth_objects", type_="foreignkey")
    op.drop_index("ix_truth_objects_superseded_by_id", "truth_objects")

    # ------------------------------------------------------------------
    # Drop new columns
    # ------------------------------------------------------------------
    op.drop_column("truth_objects", "rejected_by")
    op.drop_column("truth_objects", "rejected_at")
    op.drop_column("truth_objects", "rejection_reason")
    op.drop_column("truth_objects", "superseded_by_id")
    op.drop_column("truth_objects", "superseded_at")
    op.drop_column("truth_objects", "validated_by")
    op.drop_column("truth_objects", "validated_at")
    op.drop_column("truth_objects", "validation_notes")
