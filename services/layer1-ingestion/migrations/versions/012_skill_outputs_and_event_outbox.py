"""Add skill output tables and event outbox for Layer 1 Source Intelligence Skills.

Revision ID: 012
Revises: 011
Create Date: 2026-05-14

Adds:
- skill-aware columns to scraping_jobs (skill_name, target_entity_type,
  output_contract, downstream_events)
- source_corpuses table — structured output from LicensingCompanyIntakeSkill
- account_intelligence_packets table — structured output from ProspectResearchSkill
- event_outbox table — durable transactional outbox for downstream event emission

The event_outbox ensures that layer1.source_corpus.ready and
layer1.account_intelligence.ready events are only emitted after durable storage
succeeds, and that delivery is retried on failure rather than silently dropped.
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Skill-aware columns on scraping_jobs
    # -------------------------------------------------------------------------
    op.add_column(
        "scraping_jobs",
        sa.Column("skill_name", sa.String(100), nullable=True),
    )
    op.add_column(
        "scraping_jobs",
        sa.Column("target_entity_type", sa.String(100), nullable=True),
    )
    op.add_column(
        "scraping_jobs",
        sa.Column("output_contract", sa.String(100), nullable=True),
    )
    op.add_column(
        "scraping_jobs",
        sa.Column(
            "downstream_events",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # -------------------------------------------------------------------------
    # 2. source_corpuses
    # -------------------------------------------------------------------------
    op.create_table(
        "source_corpuses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.String(255), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column(
            "corpus_type",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'licensing_company_ontology_seed'"),
        ),
        sa.Column(
            "source_groups",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "candidate_concepts",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provenance",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "extraction_status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'ready_for_extraction'"),
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scraping_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_source_corpuses_tenant_created",
        "source_corpuses",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_source_corpuses_company",
        "source_corpuses",
        ["tenant_id", "company_id"],
    )
    op.create_index(
        "idx_source_corpuses_job_id",
        "source_corpuses",
        ["job_id"],
    )

    # -------------------------------------------------------------------------
    # 3. account_intelligence_packets
    # -------------------------------------------------------------------------
    op.create_table(
        "account_intelligence_packets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(255), nullable=True),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column(
            "packet_type",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'prospect_research'"),
        ),
        sa.Column(
            "company_profile",
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "observed_signals",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "likely_pain_areas",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "likely_stakeholders",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "source_references",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "confidence_summary",
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "next_recommended_events",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scraping_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_account_intel_packets_tenant_created",
        "account_intelligence_packets",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_account_intel_packets_account",
        "account_intelligence_packets",
        ["tenant_id", "account_id"],
    )
    op.create_index(
        "idx_account_intel_packets_job_id",
        "account_intelligence_packets",
        ["job_id"],
    )

    # -------------------------------------------------------------------------
    # 4. event_outbox
    # -------------------------------------------------------------------------
    op.create_table(
        "event_outbox",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_event_outbox_status_created",
        "event_outbox",
        ["status", "created_at"],
    )
    op.create_index(
        "idx_event_outbox_tenant_id",
        "event_outbox",
        ["tenant_id"],
    )
    op.create_index(
        "idx_event_outbox_event_type",
        "event_outbox",
        ["event_type"],
    )
    op.create_index(
        "idx_event_outbox_aggregate",
        "event_outbox",
        ["aggregate_type", "aggregate_id"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("event_outbox")
    op.drop_table("account_intelligence_packets")
    op.drop_table("source_corpuses")

    op.drop_column("scraping_jobs", "downstream_events")
    op.drop_column("scraping_jobs", "output_contract")
    op.drop_column("scraping_jobs", "target_entity_type")
    op.drop_column("scraping_jobs", "skill_name")
