"""Add enrichment columns to accounts table.

Data Intelligence Layer Phase 1: Account enrichment fields for
tech stack detection, executive mapping, financial data, and pain signals.

Revision ID: 019
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enrichment status tracking
    op.add_column(
        "accounts",
        sa.Column(
            "enrichment_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="Enrichment state: pending, in_progress, enriched, failed, stale",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "enriched_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful enrichment timestamp",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "enrichment_sources",
            JSON,
            nullable=False,
            server_default="[]",
            comment="List of sources used for enrichment",
        ),
    )

    # Enrichment data columns (JSONB)
    op.add_column(
        "accounts",
        sa.Column(
            "tech_stack",
            JSON,
            nullable=True,
            comment="Detected technology stack: {category: [technologies]}",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "executives",
            JSON,
            nullable=False,
            server_default="[]",
            comment="Key executives: [{name, title, linkedin_url, email}]",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "financials", JSON, nullable=True, comment="Financial data from SEC/public sources"
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "competitive_landscape",
            JSON,
            nullable=False,
            server_default="[]",
            comment="Known competitors: [{name, domain, overlap_areas}]",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "pain_signals",
            JSON,
            nullable=False,
            server_default="[]",
            comment="Detected pain signals: [{signal, source, confidence, detected_at}]",
        ),
    )

    # Indexes
    op.create_index("ix_accounts_enrichment_status", "accounts", ["enrichment_status"])
    # Tenant ownership, its index, and strict RLS were established by
    # revisions 002, 007, and 026. Do not recreate them here: doing so makes
    # clean upgrades fail on duplicate column/index definitions.


def downgrade() -> None:
    op.drop_index("ix_accounts_enrichment_status", table_name="accounts")

    op.drop_column("accounts", "pain_signals")
    op.drop_column("accounts", "competitive_landscape")
    op.drop_column("accounts", "financials")
    op.drop_column("accounts", "executives")
    op.drop_column("accounts", "tech_stack")
    op.drop_column("accounts", "enrichment_sources")
    op.drop_column("accounts", "enriched_at")
    op.drop_column("accounts", "enrichment_status")
