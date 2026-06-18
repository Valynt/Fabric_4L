"""Add Value Evidence Graph tables.

Adds canonical tables for ValueClaim, Scenario, Assumption, EvidenceLink,
BusinessProblem, Stakeholder, Objection, RealizationEvent, and ValueCase.

Revision ID: 021
Revises: 020
Create Date: 2026-06-17
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "017"
branch_labels = None
depends_on = None


def _base_columns() -> list[sa.Column[Any]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "value_claims",
        *_base_columns(),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(32), nullable=False, index=True),
        sa.Column("value_unit", sa.String(32), nullable=False),
        sa.Column("conservative_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("expected_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("aggressive_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("weakest_assumption_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("maturity_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", sa.String(255), nullable=True),
        sa.Column("created_by_workflow_id", sa.String(255), nullable=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("truth_object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "value_scenarios",
        *_base_columns(),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scenario_type", sa.String(32), nullable=False, index=True),
        sa.Column("formula_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assumption_overrides", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("outputs", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sensitivity_ranking", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "value_assumptions",
        *_base_columns(),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("assumption_type", sa.String(32), nullable=False, index=True),
        sa.Column("value", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source_signal_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("impact_level", sa.String(16), nullable=False),
        sa.Column("approval_status", sa.String(32), nullable=False, index=True),
        sa.Column("benchmark_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("benchmark_metric", sa.String(128), nullable=True),
        sa.Column("benchmark_percentile", sa.Integer(), nullable=True),
    )

    op.create_table(
        "value_evidence_links",
        *_base_columns(),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("evidence_type", sa.String(32), nullable=False, index=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "business_problems",
        *_base_columns(),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("problem_type", sa.String(32), nullable=False),
        sa.Column("signal_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("driver_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        "value_stakeholders",
        *_base_columns(),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(128), nullable=False),
        sa.Column("influence_level", sa.String(16), nullable=False),
        sa.Column("decision_criteria", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_proof_types", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pain_points", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("goals", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        "value_objections",
        *_base_columns(),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("objection_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("raised_by_stakeholder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("counter_evidence_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )

    op.create_table(
        "value_realization_events",
        *_base_columns(),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(32), nullable=False, index=True),
        sa.Column("value", sa.Numeric(20, 6), nullable=False),
        sa.Column("value_unit", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("benchmark_ids", postgresql.JSONB(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.String(255), nullable=True),
    )

    op.create_table(
        "value_cases",
        *_base_columns(),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_case_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("claim_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("stakeholder_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Composite indexes for common lineage queries
    op.create_index("ix_value_claims_tenant_account_status", "value_claims", ["tenant_id", "account_id", "status"])
    op.create_index("ix_value_evidence_links_target", "value_evidence_links", ["target_type", "target_id"])
    op.create_index("ix_value_realization_events_claim", "value_realization_events", ["claim_id", "event_type"])


def downgrade() -> None:
    op.drop_table("value_cases")
    op.drop_table("value_realization_events")
    op.drop_table("value_objections")
    op.drop_table("value_stakeholders")
    op.drop_table("business_problems")
    op.drop_table("value_evidence_links")
    op.drop_table("value_assumptions")
    op.drop_table("value_scenarios")
    op.drop_table("value_claims")
