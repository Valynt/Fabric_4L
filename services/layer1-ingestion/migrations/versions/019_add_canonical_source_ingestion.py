"""Add canonical source ingestion tables.

Revision ID: 019
Revises: 018
Create Date: 2026-06-18

Adds the durable, versioned, tenant-scoped source ingestion model required by
the unified Source Ingestion Layer UI:

- ingested_sources: logical source record
- source_versions: immutable source content versions
- source_ingestion_runs: durable async pipeline runs
- normalized_documents: common normalized representation

This migration is additive and does not alter existing scraping-target tables.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create canonical source ingestion tables."""
    op.create_table(
        "ingested_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("account_id", sa.String(255), nullable=False, index=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("external_reference", sa.String(500), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("latest_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("latest_version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("retention_class", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "account_id", "fingerprint", name="uix_ingested_source_fingerprint"),
        sa.Index("idx_ingested_sources_tenant_account", "tenant_id", "account_id", "created_at"),
    )

    op.create_table(
        "source_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("ingested_sources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_storage_uri", sa.Text, nullable=False),
        sa.Column("raw_bytes_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="stored"),
        sa.Column("meta", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("source_id", "version_number", name="uix_source_version_number"),
        sa.Index("idx_source_versions_source_created", "source_id", "created_at"),
    )

    op.create_table(
        "source_ingestion_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("ingested_sources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_version_id", UUID(as_uuid=True), sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACCEPTED"),
        sa.Column("requested_outputs", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("idempotency_key", sa.String(255), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("stage_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail_safe", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Index("idx_source_ingestion_runs_tenant_status", "tenant_id", "status"),
        sa.Index("idx_source_ingestion_runs_idempotency", "tenant_id", "idempotency_key"),
    )

    op.create_table(
        "normalized_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_version_id", UUID(as_uuid=True), sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("document_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sections", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("participants", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalizer_version", sa.String(50), nullable=False),
        sa.Column("chunks", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Index("idx_normalized_documents_tenant", "tenant_id", "created_at"),
    )

    # Add foreign key from ingested_sources.latest_version_id to source_versions.
    op.create_foreign_key(
        "fk_ingested_sources_latest_version",
        "ingested_sources",
        "source_versions",
        ["latest_version_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop canonical source ingestion tables."""
    op.drop_constraint("fk_ingested_sources_latest_version", "ingested_sources", type_="foreignkey")
    op.drop_table("normalized_documents")
    op.drop_table("source_ingestion_runs")
    op.drop_table("source_versions")
    op.drop_table("ingested_sources")
