"""Add billing_usage_events table for high-throughput usage metering.

Revision ID: 015
Revises: 014
Create Date: 2026-04-23

This migration creates the usage event ingestion table for metering:
- High-throughput event storage with tenant isolation
- Idempotency via (tenant_id, event_id) unique constraint
- JSONB metadata for flexible event attributes
- RLS policies for secure multi-tenant access

SECURITY: Usage events are tenant-scoped - tenants can only see their own events.
PERFORMANCE: Optimized indexes for time-series queries and aggregation.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create billing_usage_events table with RLS."""

    # Create the usage events table
    op.create_table(
        'billing_usage_events',
        # Primary key
        sa.Column('id', sa.String(100), primary_key=True),

        # Tenant and customer attribution
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('customer_id', sa.String(100), nullable=False, index=True),

        # Event identification (idempotency)
        sa.Column('event_id', sa.String(255), nullable=False),

        # Event type and metric
        sa.Column('event_name', sa.String(100), nullable=False, index=True),
        sa.Column('metric_name', sa.String(100), nullable=False, index=True),

        # Quantities
        sa.Column('quantity', sa.Float(), nullable=False, server_default=sa.text('1.0')),
        sa.Column('unit', sa.String(50), nullable=True),

        # Timestamping
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # Processing status
        sa.Column('status', sa.String(50), nullable=False, server_default=sa.text("'pending'")),

        # Flexible metadata
        sa.Column('metadata', postgresql.JSONB(), nullable=True),

        # Audit timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for query optimization
    op.create_index(
        'ix_billing_usage_events_customer_timestamp',
        'billing_usage_events',
        ['customer_id', 'timestamp']
    )
    op.create_index(
        'ix_billing_usage_events_status_created',
        'billing_usage_events',
        ['status', 'created_at']
    )
    op.create_index(
        'ix_billing_usage_events_event_name',
        'billing_usage_events',
        ['event_name']
    )

    # Create unique constraint for idempotency
    op.create_unique_constraint(
        'uq_billing_usage_events_tenant_event',
        'billing_usage_events',
        ['tenant_id', 'event_id']
    )

    # Create status index with partial index for pending events (optimization)
    op.create_index(
        'ix_billing_usage_events_pending',
        'billing_usage_events',
        ['tenant_id', 'customer_id', 'metric_name'],
        postgresql_where=sa.text("status = 'pending'")
    )

    # Enable Row-Level Security
    op.execute("ALTER TABLE billing_usage_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE billing_usage_events FORCE ROW LEVEL SECURITY")

    # Create tenant isolation policy
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON billing_usage_events
            FOR ALL
            TO PUBLIC
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
            )
    """)

    # Create admin bypass policy
    op.execute("""
        CREATE POLICY admin_bypass_policy ON billing_usage_events
            FOR ALL
            TO admin_role, system_role
            USING (current_setting('app.tenant_id', true) = '')
    """)

    # Create partial index for recent events (hot data)
    op.execute("""
        CREATE INDEX ix_billing_usage_events_recent 
        ON billing_usage_events (tenant_id, created_at DESC)
        WHERE created_at > NOW() - INTERVAL '7 days'
    """)


def downgrade() -> None:
    """Drop billing_usage_events table."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON billing_usage_events")
    op.execute("DROP POLICY IF EXISTS admin_bypass_policy ON billing_usage_events")

    # Disable RLS
    op.execute("ALTER TABLE billing_usage_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE billing_usage_events DISABLE ROW LEVEL SECURITY")

    # Drop the table
    op.drop_table('billing_usage_events')
