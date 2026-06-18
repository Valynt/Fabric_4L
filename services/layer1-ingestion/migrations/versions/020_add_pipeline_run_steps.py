"""Add pipeline run steps and outbox routing columns.

Revision ID: 020
Revises: 019
Create Date: 2026-06-19

Adds durable per-stage execution tracking for the canonical source ingestion
pipeline and extends the transactional outbox with routing metadata.

- ingestion_run_steps: idempotent stage attempts with artifact references
- source_ingestion_runs.current_step_id: pointer to active step
- event_outbox.stage_name / topic: routing for pipeline events
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pipeline stage tracking and outbox routing columns."""
    op.create_table(
        "ingestion_run_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("source_ingestion_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("stage_name", sa.String(50), nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("input_artifact_ids", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_artifact_ids", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail_safe", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("run_id", "stage_name", "attempt", name="uq_ingestion_run_step_stage_attempt"),
        sa.Index("idx_ingestion_run_steps_tenant_status", "tenant_id", "status"),
        sa.Index("idx_ingestion_run_steps_run_stage", "run_id", "stage_name"),
        sa.Index("idx_ingestion_run_steps_run_created", "run_id", "created_at"),
    )

    op.add_column(
        "source_ingestion_runs",
        sa.Column("current_step_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_source_ingestion_runs_current_step",
        "source_ingestion_runs",
        ["current_step_id"],
    )
    op.create_foreign_key(
        "fk_source_ingestion_runs_current_step",
        "source_ingestion_runs",
        "ingestion_run_steps",
        ["current_step_id"],
        ["id"],
    )

    op.add_column(
        "event_outbox",
        sa.Column("stage_name", sa.String(50), nullable=True),
    )
    op.add_column(
        "event_outbox",
        sa.Column("topic", sa.String(100), nullable=True),
    )
    op.create_index(
        "idx_event_outbox_stage_name",
        "event_outbox",
        ["stage_name"],
    )
    op.create_index(
        "idx_event_outbox_topic",
        "event_outbox",
        ["topic"],
    )


def downgrade() -> None:
    """Remove pipeline stage tracking and outbox routing columns."""
    op.drop_index("idx_event_outbox_topic", table_name="event_outbox")
    op.drop_index("idx_event_outbox_stage_name", table_name="event_outbox")
    op.drop_column("event_outbox", "topic")
    op.drop_column("event_outbox", "stage_name")

    op.drop_constraint("fk_source_ingestion_runs_current_step", "source_ingestion_runs", type_="foreignkey")
    op.drop_index("idx_source_ingestion_runs_current_step", table_name="source_ingestion_runs")
    op.drop_column("source_ingestion_runs", "current_step_id")

    op.drop_table("ingestion_run_steps")
