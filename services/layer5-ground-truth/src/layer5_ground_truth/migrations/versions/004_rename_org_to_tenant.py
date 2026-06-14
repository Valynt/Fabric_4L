"""Rename organization_id to tenant_id in Layer 5 tables.

Revision ID: 004
Revises: 003_add_model_registry
Create Date: 2026-04-23

This migration normalizes column naming across the codebase, changing
`organization_id` to `tenant_id` for consistency with Layer 4 tenant model.

Affected tables:
- truth_objects
- truth_sources
- model_versions
- model_deployments
- model_evaluations
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def _drop_index_if_exists(index_name: str) -> None:
    """Drop an index defensively so rename steps tolerate earlier name drift."""
    op.execute(f'DROP INDEX IF EXISTS {index_name}')


def _has_column(table_name: str, column_name: str) -> bool:
    """Return whether a column exists in the current migration database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    """Rename organization_id columns to tenant_id."""

    # truth_objects
    _drop_index_if_exists('ix_truth_objects_organization_id')
    _drop_index_if_exists('ix_truth_objects_org_id')
    op.alter_column(
        'truth_objects',
        'organization_id',
        new_column_name='tenant_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_truth_objects_tenant_id',
        'truth_objects',
        ['tenant_id'],
    )

    # truth_sources
    _drop_index_if_exists('ix_truth_sources_organization_id')
    _drop_index_if_exists('ix_truth_sources_org_id')
    op.alter_column(
        'truth_sources',
        'organization_id',
        new_column_name='tenant_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_truth_sources_tenant_id',
        'truth_sources',
        ['tenant_id'],
    )

    # model_versions - drop composite indexes first
    _drop_index_if_exists('ix_model_versions_org_provider_name')
    _drop_index_if_exists('ix_model_versions_org_default')
    _drop_index_if_exists('ix_model_versions_tenant_provider_name')
    _drop_index_if_exists('ix_model_versions_tenant_default')
    if _has_column('model_versions', 'organization_id'):
        op.alter_column(
            'model_versions',
            'organization_id',
            new_column_name='tenant_id',
            existing_type=sa.UUID(),
            existing_nullable=False,
        )
    # Recreate indexes with new column name
    op.create_index(
        'ix_model_versions_tenant_provider_name',
        'model_versions',
        ['tenant_id', 'provider', 'name'],
    )
    op.create_index(
        'ix_model_versions_tenant_default',
        'model_versions',
        ['tenant_id', 'is_default'],
    )

    # model_deployments
    _drop_index_if_exists('ix_model_deployments_organization_id')
    _drop_index_if_exists('ix_model_deployments_org_env_default')
    _drop_index_if_exists('ix_model_deployments_org_env_status')
    _drop_index_if_exists('ix_model_deployments_tenant_id')
    _drop_index_if_exists('ix_model_deployments_tenant_env_default')
    _drop_index_if_exists('ix_model_deployments_tenant_env_status')
    if _has_column('model_deployments', 'organization_id'):
        op.alter_column(
            'model_deployments',
            'organization_id',
            new_column_name='tenant_id',
            existing_type=sa.UUID(),
            existing_nullable=False,
        )
    op.create_index(
        'ix_model_deployments_tenant_id',
        'model_deployments',
        ['tenant_id'],
    )
    op.create_index(
        'ix_model_deployments_tenant_env_default',
        'model_deployments',
        ['tenant_id', 'environment', 'is_default_for_env'],
    )
    op.create_index(
        'ix_model_deployments_tenant_env_status',
        'model_deployments',
        ['tenant_id', 'environment', 'status'],
    )

    # model_evaluations
    _drop_index_if_exists('ix_model_evaluations_organization_id')
    _drop_index_if_exists('ix_model_evaluations_org_benchmark')
    _drop_index_if_exists('ix_model_evaluations_org_model')
    _drop_index_if_exists('ix_model_evaluations_tenant_id')
    _drop_index_if_exists('ix_model_evaluations_tenant_benchmark')
    _drop_index_if_exists('ix_model_evaluations_tenant_model')
    if _has_column('model_evaluations', 'organization_id'):
        op.alter_column(
            'model_evaluations',
            'organization_id',
            new_column_name='tenant_id',
            existing_type=sa.UUID(),
            existing_nullable=False,
        )
    op.create_index(
        'ix_model_evaluations_tenant_id',
        'model_evaluations',
        ['tenant_id'],
    )
    op.create_index(
        'ix_model_evaluations_tenant_benchmark',
        'model_evaluations',
        ['tenant_id', 'benchmark_name'],
    )
    op.create_index(
        'ix_model_evaluations_tenant_model',
        'model_evaluations',
        ['tenant_id', 'model_version_id'],
    )

    # validation_events
    op.alter_column(
        'validation_events',
        'organization_id',
        new_column_name='tenant_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.execute('DROP INDEX IF EXISTS ix_validation_events_org_status')
    op.create_index(
        'ix_validation_events_tenant_status',
        'validation_events',
        ['tenant_id', 'to_status'],
    )

    # maturity_history
    op.alter_column(
        'maturity_history',
        'organization_id',
        new_column_name='tenant_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_maturity_history_tenant_id',
        'maturity_history',
        ['tenant_id'],
    )


def downgrade():
    """Revert tenant_id columns back to organization_id."""

    # maturity_history
    op.drop_index('ix_maturity_history_tenant_id', table_name='maturity_history')
    op.alter_column(
        'maturity_history',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )

    # validation_events
    op.drop_index('ix_validation_events_tenant_status', table_name='validation_events')
    op.alter_column(
        'validation_events',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_validation_events_org_status',
        'validation_events',
        ['organization_id', 'to_status'],
    )

    # model_evaluations
    op.drop_index('ix_model_evaluations_tenant_id', table_name='model_evaluations')
    op.drop_index('ix_model_evaluations_tenant_benchmark', table_name='model_evaluations')
    op.drop_index('ix_model_evaluations_tenant_model', table_name='model_evaluations')
    op.alter_column(
        'model_evaluations',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_model_evaluations_organization_id',
        'model_evaluations',
        ['organization_id'],
    )
    op.create_index(
        'ix_model_evaluations_org_benchmark',
        'model_evaluations',
        ['organization_id', 'benchmark_name'],
    )
    op.create_index(
        'ix_model_evaluations_org_model',
        'model_evaluations',
        ['organization_id', 'model_version_id'],
    )

    # model_deployments
    op.drop_index('ix_model_deployments_tenant_id', table_name='model_deployments')
    op.drop_index('ix_model_deployments_tenant_env_default', table_name='model_deployments')
    op.drop_index('ix_model_deployments_tenant_env_status', table_name='model_deployments')
    op.alter_column(
        'model_deployments',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_model_deployments_organization_id',
        'model_deployments',
        ['organization_id'],
    )
    op.create_index(
        'ix_model_deployments_org_env_default',
        'model_deployments',
        ['organization_id', 'environment', 'is_default_for_env'],
    )
    op.create_index(
        'ix_model_deployments_org_env_status',
        'model_deployments',
        ['organization_id', 'environment', 'status'],
    )

    # model_versions
    op.drop_index('ix_model_versions_tenant_provider_name', table_name='model_versions')
    op.drop_index('ix_model_versions_tenant_default', table_name='model_versions')
    op.alter_column(
        'model_versions',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_model_versions_org_provider_name',
        'model_versions',
        ['organization_id', 'provider', 'name'],
    )
    op.create_index(
        'ix_model_versions_org_default',
        'model_versions',
        ['organization_id', 'is_default'],
    )

    # truth_sources
    op.drop_index('ix_truth_sources_tenant_id', table_name='truth_sources')
    op.alter_column(
        'truth_sources',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_truth_sources_organization_id',
        'truth_sources',
        ['organization_id'],
    )

    # truth_objects
    op.drop_index('ix_truth_objects_tenant_id', table_name='truth_objects')
    op.alter_column(
        'truth_objects',
        'tenant_id',
        new_column_name='organization_id',
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.create_index(
        'ix_truth_objects_organization_id',
        'truth_objects',
        ['organization_id'],
    )
