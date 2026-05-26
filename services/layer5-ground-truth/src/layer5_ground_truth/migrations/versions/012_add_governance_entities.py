"""Add Formula, Benchmark, and Policy governance entities.

This migration adds:
1. formulas, formula_versions, formula_parameters tables
2. benchmark_datasets, benchmark_versions, benchmark_scopes tables
3. policies, policy_versions, policy_rules, policy_applications tables

Phase 3: Create Formula/Benchmark/Policy governance entities
Issue: Formulas versioned/typed/schema-validated, Benchmark metadata completeness, Policy rules engine
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "012_add_governance_entities"
down_revision = "011_add_approval_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------
    # Formula governance tables
    # ---------------------------------------------------------------------

    op.create_table(
        "formulas",
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
        sa.Column("formula_type", sa.String(32), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("latest_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("input_schema", postgresql.JSON(), nullable=False),
        sa.Column("output_schema", postgresql.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
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

    op.create_index("ix_formulas_tenant_type", "formulas", ["tenant_id", "formula_type"])
    op.create_index("ix_formulas_tenant_slug", "formulas", ["tenant_id", "slug"])

    op.create_table(
        "formula_versions",
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
            "formula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formulas.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("expression_language", sa.String(32), nullable=False, default="python"),
        sa.Column("status", sa.String(32), nullable=False, default="draft", index=True),
        sa.Column("validation_errors", postgresql.JSON(), nullable=True),
        sa.Column("test_results", postgresql.JSON(), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_formula_versions_tenant_formula", "formula_versions", ["tenant_id", "formula_id"])
    op.create_index("ix_formula_versions_tenant_status", "formula_versions", ["tenant_id", "status"])
    op.create_index("ix_formula_versions_formula_version", "formula_versions", ["formula_id", "version"], unique=True)

    op.create_table(
        "formula_parameters",
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
            "formula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formulas.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("parameter_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, default=True),
        sa.Column("default_value", postgresql.JSON(), nullable=True),
        sa.Column("min_value", postgresql.JSON(), nullable=True),
        sa.Column("max_value", postgresql.JSON(), nullable=True),
        sa.Column("allowed_values", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_formula_parameters_tenant_formula", "formula_parameters", ["tenant_id", "formula_id"])
    op.create_index("ix_formula_parameters_formula_name", "formula_parameters", ["formula_id", "name"], unique=True)

    # ---------------------------------------------------------------------
    # Benchmark governance tables
    # ---------------------------------------------------------------------

    op.create_table(
        "benchmark_datasets",
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
        sa.Column("benchmark_type", sa.String(32), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("latest_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collection_methodology", sa.Text(), nullable=True),
        sa.Column("confidence_level", sa.String(32), nullable=False, default="medium"),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("margin_of_error", postgresql.JSON(), nullable=True),
        sa.Column("data_quality_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
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

    op.create_index("ix_benchmark_datasets_tenant_type", "benchmark_datasets", ["tenant_id", "benchmark_type"])
    op.create_index("ix_benchmark_datasets_tenant_slug", "benchmark_datasets", ["tenant_id", "slug"])

    op.create_table(
        "benchmark_versions",
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
            "benchmark_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("benchmark_datasets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("data", postgresql.JSON(), nullable=False),
        sa.Column("data_schema", postgresql.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="draft", index=True),
        sa.Column("validation_errors", postgresql.JSON(), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_benchmark_versions_tenant_benchmark", "benchmark_versions", ["tenant_id", "benchmark_id"])
    op.create_index("ix_benchmark_versions_tenant_status", "benchmark_versions", ["tenant_id", "status"])
    op.create_index("ix_benchmark_versions_benchmark_version", "benchmark_versions", ["benchmark_id", "version"], unique=True)
    op.create_index("ix_benchmark_versions_effective", "benchmark_versions", ["effective_from", "effective_until"])

    op.create_table(
        "benchmark_scopes",
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
            "benchmark_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("benchmark_datasets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_value", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_benchmark_scopes_tenant_benchmark", "benchmark_scopes", ["tenant_id", "benchmark_id"])
    op.create_index("ix_benchmark_scopes_type_value", "benchmark_scopes", ["benchmark_id", "scope_type", "scope_value"])

    # ---------------------------------------------------------------------
    # Policy governance tables
    # ---------------------------------------------------------------------

    op.create_table(
        "policies",
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
        sa.Column("policy_type", sa.String(32), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("latest_version", sa.String(64), nullable=False, default="1.0.0"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, default=True),
        sa.Column("severity", sa.String(32), nullable=False, default="medium"),
        sa.Column("applies_to_entity_types", postgresql.JSON(), nullable=False, default=list),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
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

    op.create_index("ix_policies_tenant_type", "policies", ["tenant_id", "policy_type"])
    op.create_index("ix_policies_tenant_slug", "policies", ["tenant_id", "slug"])

    op.create_table(
        "policy_versions",
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
            "policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("rules_engine_config", postgresql.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="draft", index=True),
        sa.Column("validation_errors", postgresql.JSON(), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_policy_versions_tenant_policy", "policy_versions", ["tenant_id", "policy_id"])
    op.create_index("ix_policy_versions_tenant_status", "policy_versions", ["tenant_id", "status"])
    op.create_index("ix_policy_versions_policy_version", "policy_versions", ["policy_id", "version"], unique=True)
    op.create_index("ix_policy_versions_effective", "policy_versions", ["effective_from", "effective_until"])

    op.create_table(
        "policy_rules",
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
            "policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_name", sa.String(128), nullable=False),
        sa.Column("rule_order", sa.Integer(), nullable=False, default=0),
        sa.Column("target_field", sa.String(128), nullable=False),
        sa.Column("operator", sa.String(32), nullable=False),
        sa.Column("expected_value", postgresql.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, default=True),
        sa.Column("severity", sa.String(32), nullable=False, default="medium"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_policy_rules_tenant_policy", "policy_rules", ["tenant_id", "policy_id"])
    op.create_index("ix_policy_rules_policy_order", "policy_rules", ["policy_id", "rule_order"])

    op.create_table(
        "policy_applications",
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
            "policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entity_type", sa.String(32), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("entity_version", sa.String(64), nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("applied_by", sa.String(255), nullable=True),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("rule_results", postgresql.JSON(), nullable=True),
        sa.Column("context", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("ix_policy_applications_tenant_policy", "policy_applications", ["tenant_id", "policy_id"])
    op.create_index("ix_policy_applications_entity", "policy_applications", ["entity_type", "entity_id"])
    op.create_index("ix_policy_applications_applied_at", "policy_applications", ["applied_at"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("policy_applications")
    op.drop_table("policy_rules")
    op.drop_table("policy_versions")
    op.drop_table("policies")
    op.drop_table("benchmark_scopes")
    op.drop_table("benchmark_versions")
    op.drop_table("benchmark_datasets")
    op.drop_table("formula_parameters")
    op.drop_table("formula_versions")
    op.drop_table("formulas")
