"""Add tenant_id columns to billing tables for multi-tenant isolation.

Revision ID: 014
Revises: 013
Create Date: 2026-04-23

This migration adds tenant isolation to the billing system:
- Adds tenant_id to billing_customers (nullable for backward compatibility)
- Adds tenant_id to billing_subscriptions (nullable for backward compatibility)
- Adds tenant_id to billing_webhook_events (nullable for backward compatibility)
- Enables Row-Level Security on all billing tables
- Creates tenant isolation policies

SECURITY: Billing data isolation is critical. A bug that charges Tenant A 
for Tenant B's usage is a trust-destroying event.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that need tenant_id added and RLS enabled
BILLING_TABLES = [
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
]


def upgrade() -> None:
    """Add tenant_id columns and enable RLS on billing tables."""
    
    # Step 1: Add tenant_id columns (nullable for backward compatibility)
    # Customer table - tenant_id links to the tenant this customer belongs to
    op.add_column(
        'billing_customers',
        sa.Column('tenant_id', sa.String(255), nullable=True, index=True)
    )
    op.create_index('ix_billing_customers_tenant', 'billing_customers', ['tenant_id'])
    
    # Subscription table - tenant_id for query optimization and security
    op.add_column(
        'billing_subscriptions',
        sa.Column('tenant_id', sa.String(255), nullable=True, index=True)
    )
    op.create_index('ix_billing_subscriptions_tenant', 'billing_subscriptions', ['tenant_id'])
    
    # Webhook events table - tenant_id for debugging and audit
    op.add_column(
        'billing_webhook_events',
        sa.Column('tenant_id', sa.String(255), nullable=True, index=True)
    )
    op.create_index('ix_billing_webhook_events_tenant', 'billing_webhook_events', ['tenant_id'])
    
    # Step 2: Enable Row-Level Security on billing tables
    for table in BILLING_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    
    # Step 3: Create tenant isolation policies
    # Users can only see billing data for their tenant
    # NULL tenant_id allows system-level records (backward compatibility)
    for table in BILLING_TABLES:
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id IS NULL OR
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id IS NULL OR
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
        """)
    
    # Step 4: Create admin bypass policy for system operations
    for table in BILLING_TABLES:
        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {table}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)
    
    # Step 5: Add composite unique constraint for tenant-scoped customer lookup
    # This ensures a customer_id is unique within a tenant, but different tenants
    # can have customers with the same logical ID
    op.create_index(
        'ix_billing_customers_tenant_customer',
        'billing_customers',
        ['tenant_id', 'id'],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL")
    )


def downgrade() -> None:
    """Remove tenant_id columns and disable RLS on billing tables."""
    # Step 1: Drop RLS policies
    for table in BILLING_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
    
    # Step 2: Disable RLS
    for table in BILLING_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    
    # Step 3: Drop unique constraint
    op.drop_index('ix_billing_customers_tenant_customer', table_name='billing_customers')
    
    # Step 4: Drop tenant_id columns
    op.drop_column('billing_webhook_events', 'tenant_id')
    op.drop_column('billing_subscriptions', 'tenant_id')
    op.drop_column('billing_customers', 'tenant_id')
