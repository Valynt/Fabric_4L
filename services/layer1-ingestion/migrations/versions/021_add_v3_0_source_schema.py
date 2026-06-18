"""Add v3.0 source schema: consent, custody, evidence chunks, external identity.

Revision ID: 021
Revises: 020
Create Date: 2026-06-19

Adds the durable schema foundation required by the Fabric_4L Integration Design
Brief v3.0:

- source_consents: explicit consent before ingestion
- evidence_chunks: atomic evidence units with provenance anchors
- ingested_sources: custody mode, consent, and external identity fields
- source_versions: custody-aware storage metadata
- source_ingestion_runs: connector and consent binding

This migration is additive and does not remove existing scraping-target tables.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create v3.0 source schema objects."""
    op.create_table(
        "source_consents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("account_id", sa.String(255), nullable=False, index=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("consent_hash", sa.String(64), nullable=False),
        sa.Column("granted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Index("idx_source_consents_tenant_account", "tenant_id", "account_id", "created_at"),
        sa.Index("idx_source_consents_status", "tenant_id", "status"),
    )

    op.create_table(
        "evidence_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "source_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("anchor", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="1.00"),
        sa.Column("trust_score", sa.Numeric(3, 2), nullable=False, server_default="1.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("source_version_id", "chunk_index", name="uq_evidence_chunk_version_index"),
        sa.Index("idx_evidence_chunks_version", "source_version_id", "created_at"),
        sa.Index("idx_evidence_chunks_tenant", "tenant_id", "status"),
    )

    # ingested_sources: v3.0 custody, consent, and external identity
    op.add_column("ingested_sources", sa.Column("custody_mode", sa.String(1), nullable=False, server_default="A"))
    op.add_column("ingested_sources", sa.Column("consent_id", UUID(as_uuid=True), nullable=True))
    op.add_column("ingested_sources", sa.Column("external_system", sa.String(100), nullable=True))
    op.add_column("ingested_sources", sa.Column("external_object_type", sa.String(100), nullable=True))
    op.add_column("ingested_sources", sa.Column("external_object_id", sa.String(255), nullable=True))
    op.add_column("ingested_sources", sa.Column("external_version", sa.String(100), nullable=True))
    op.add_column("ingested_sources", sa.Column("snapshot_hash", sa.String(64), nullable=True))
    op.add_column("ingested_sources", sa.Column("field_scope_id", sa.String(255), nullable=True))
    op.create_index("idx_ingested_sources_consent", "ingested_sources", ["consent_id"])
    op.create_index(
        "idx_ingested_sources_external_identity",
        "ingested_sources",
        ["tenant_id", "external_system", "external_object_type", "external_object_id"],
    )
    op.create_foreign_key(
        "fk_ingested_sources_consent",
        "ingested_sources",
        "source_consents",
        ["consent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # source_versions: v3.0 custody-aware storage
    op.add_column("source_versions", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_versions", sa.Column("source_uri", sa.Text, nullable=True))
    op.add_column("source_versions", sa.Column("storage_backend", sa.String(50), nullable=True))

    # source_ingestion_runs: v3.0 connector and consent binding
    op.add_column("source_ingestion_runs", sa.Column("connector_name", sa.String(100), nullable=True))
    op.add_column("source_ingestion_runs", sa.Column("connector_config_hash", sa.String(64), nullable=True))
    op.add_column("source_ingestion_runs", sa.Column("policy_version", sa.String(50), nullable=True))
    op.add_column("source_ingestion_runs", sa.Column("source_snapshot_hash", sa.String(64), nullable=True))
    op.add_column("source_ingestion_runs", sa.Column("consent_id", UUID(as_uuid=True), nullable=True))
    op.create_index("idx_source_ingestion_runs_consent", "source_ingestion_runs", ["consent_id"])
    op.create_foreign_key(
        "fk_source_ingestion_runs_consent",
        "source_ingestion_runs",
        "source_consents",
        ["consent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove v3.0 source schema objects."""
    op.drop_constraint("fk_source_ingestion_runs_consent", "source_ingestion_runs", type_="foreignkey")
    op.drop_index("idx_source_ingestion_runs_consent", table_name="source_ingestion_runs")
    op.drop_column("source_ingestion_runs", "consent_id")
    op.drop_column("source_ingestion_runs", "source_snapshot_hash")
    op.drop_column("source_ingestion_runs", "policy_version")
    op.drop_column("source_ingestion_runs", "connector_config_hash")
    op.drop_column("source_ingestion_runs", "connector_name")

    op.drop_column("source_versions", "storage_backend")
    op.drop_column("source_versions", "source_uri")
    op.drop_column("source_versions", "fetched_at")

    op.drop_constraint("fk_ingested_sources_consent", "ingested_sources", type_="foreignkey")
    op.drop_index("idx_ingested_sources_external_identity", table_name="ingested_sources")
    op.drop_index("idx_ingested_sources_consent", table_name="ingested_sources")
    op.drop_column("ingested_sources", "field_scope_id")
    op.drop_column("ingested_sources", "snapshot_hash")
    op.drop_column("ingested_sources", "external_version")
    op.drop_column("ingested_sources", "external_object_id")
    op.drop_column("ingested_sources", "external_object_type")
    op.drop_column("ingested_sources", "external_system")
    op.drop_column("ingested_sources", "consent_id")
    op.drop_column("ingested_sources", "custody_mode")

    op.drop_table("evidence_chunks")
    op.drop_table("source_consents")
