"""Add billing tables for Stripe integration.

Revision ID: 009
Revises: 008
Create Date: 2026-04-15

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create billing_customers table (synced with Stripe)
    op.create_table(
        'billing_customers',
        sa.Column('id', sa.String(100), primary_key=True),  # Maps to app user_id
        sa.Column('stripe_customer_id', sa.String(100), nullable=True, unique=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Index('ix_billing_customers_stripe_id', 'stripe_customer_id'),
    )

    # Create billing_subscriptions table (synced with Stripe)
    op.create_table(
        'billing_subscriptions',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('customer_id', sa.String(100), sa.ForeignKey('billing_customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=True, unique=True),
        sa.Column('plan_id', sa.String(50), nullable=False),  # 'free', 'pro', 'enterprise'
        sa.Column('status', sa.String(50), nullable=False, server_default='incomplete'),  # Stripe statuses
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Index('ix_billing_subscriptions_customer', 'customer_id'),
        sa.Index('ix_billing_subscriptions_status', 'status'),
        sa.Index('ix_billing_subscriptions_plan', 'plan_id'),
    )

    # Create billing_webhook_events table (idempotency)
    op.create_table(
        'billing_webhook_events',
        sa.Column('id', sa.String(100), primary_key=True),  # Stripe event ID
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Index('ix_billing_webhook_events_type', 'type'),
        sa.Index('ix_billing_webhook_events_processed', 'processed_at'),
    )


def downgrade() -> None:
    op.drop_table('billing_webhook_events')
    op.drop_table('billing_subscriptions')
    op.drop_table('billing_customers')
