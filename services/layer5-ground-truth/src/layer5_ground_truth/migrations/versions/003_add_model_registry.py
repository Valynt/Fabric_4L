"""
Add Model Registry tables.

Revision ID: 003
Revises: 002
Create Date: 2026-04-19 14:51:00.000000+00:00

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Model Registry tables."""
    # Create model_versions table
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, default="other"),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("model_identifier", sa.String(128), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False, default=list),
        sa.Column("context_window", sa.Integer(), nullable=False, default=4096),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "cost_per_1k_input",
            sa.Numeric(10, 6),
            nullable=False,
            default=0.0,
        ),
        sa.Column(
            "cost_per_1k_output",
            sa.Numeric(10, 6),
            nullable=False,
            default=0.0,
        ),
        sa.Column("cost_per_1k_cached", sa.Numeric(10, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
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

    # Create indexes for model_versions
    op.create_index(
        "ix_model_versions_tenant_provider_name",
        "model_versions",
        ["tenant_id", "provider", "name"],
    )
    op.create_index(
        "ix_model_versions_tenant_default",
        "model_versions",
        ["tenant_id", "is_default"],
    )

    # Create model_deployments table
    op.create_table(
        "model_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "environment",
            sa.String(32),
            nullable=False,
            default="development",
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            default="pending",
        ),
        sa.Column("traffic_percentage", sa.Integer(), nullable=False, default=0),
        sa.Column("is_default_for_env", sa.Boolean(), nullable=False, default=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_by", sa.String(255), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_by", sa.String(255), nullable=True),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.Column("error_rate_5m", sa.Numeric(5, 4), nullable=True),
        sa.Column("latency_p50_ms", sa.Integer(), nullable=True),
        sa.Column("latency_p99_ms", sa.Integer(), nullable=True),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployment_notes", sa.Text(), nullable=True),
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

    # Create indexes for model_deployments
    op.create_index(
        "ix_model_deployments_tenant_env_default",
        "model_deployments",
        ["tenant_id", "environment", "is_default_for_env"],
    )
    op.create_index(
        "ix_model_deployments_tenant_env_status",
        "model_deployments",
        ["tenant_id", "environment", "status"],
    )

    # Create model_evaluations table
    op.create_table(
        "model_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("benchmark_name", sa.String(128), nullable=False),
        sa.Column("benchmark_version", sa.String(64), nullable=True),
        sa.Column("score", sa.Numeric(6, 4), nullable=False),
        sa.Column("score_details", postgresql.JSONB(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("evaluated_by", sa.String(255), nullable=True),
        sa.Column("evaluation_config", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("artifact_urls", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for model_evaluations
    op.create_index(
        "ix_model_evaluations_tenant_benchmark",
        "model_evaluations",
        ["tenant_id", "benchmark_name"],
    )
    op.create_index(
        "ix_model_evaluations_tenant_model",
        "model_evaluations",
        ["tenant_id", "model_version_id"],
    )

    # Add RLS policy for model_versions (follows existing RLS pattern)
    op.execute(
        """
        ALTER TABLE model_versions ENABLE ROW LEVEL SECURITY;
        CREATE POLICY model_versions_isolation_policy ON model_versions
            FOR ALL
            TO PUBLIC
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
            );
        """
    )

    # Add RLS policy for model_deployments
    op.execute(
        """
        ALTER TABLE model_deployments ENABLE ROW LEVEL SECURITY;
        CREATE POLICY model_deployments_isolation_policy ON model_deployments
            FOR ALL
            TO PUBLIC
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
            );
        """
    )

    # Add RLS policy for model_evaluations
    op.execute(
        """
        ALTER TABLE model_evaluations ENABLE ROW LEVEL SECURITY;
        CREATE POLICY model_evaluations_isolation_policy ON model_evaluations
            FOR ALL
            TO PUBLIC
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
            );
        """
    )


def downgrade() -> None:
    """Drop Model Registry tables."""
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("model_evaluations")
    op.drop_table("model_deployments")
    op.drop_table("model_versions")
