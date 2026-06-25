"""Migration: Add invoice and charge record tables for billing history.

Revision ID: 024
Revises: 023
Create Date: 2026-04-23

This migration creates:
- billing_invoices: Invoice records for customer billing periods
- billing_invoice_items: Line items for each invoice
- billing_charges: Charge attempts (successful and failed)
- Indexes and RLS policies for tenant isolation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create invoice and charge tables with tenant isolation."""
    
    # ============================================================
    # Billing Invoices Table
    # ============================================================
    op.create_table(
        'billing_invoices',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('customer_id', sa.String(100), nullable=False, index=True),
        sa.Column('stripe_invoice_id', sa.String(100), nullable=True, index=True),
        sa.Column('subscription_id', sa.String(100), nullable=True, index=True),
        
        # Invoice details
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, index=True),  # draft, open, paid, void, uncollectible
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        
        # Financial amounts (stored as cents to avoid float issues)
        sa.Column('subtotal', sa.BigInteger, nullable=False, server_default='0'),  # cents
        sa.Column('tax', sa.BigInteger, nullable=False, server_default='0'),  # cents
        sa.Column('total', sa.BigInteger, nullable=False, server_default='0'),  # cents
        sa.Column('amount_paid', sa.BigInteger, nullable=False, server_default='0'),  # cents
        sa.Column('amount_due', sa.BigInteger, nullable=False, server_default='0'),  # cents
        sa.Column('balance', sa.BigInteger, nullable=False, server_default='0'),  # cents (can be negative for credit)
        
        # Billing period
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False, index=True),
        
        # Dates
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('footer', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        
        # Host information
        sa.Column('hosted_invoice_url', sa.Text, nullable=True),
        sa.Column('invoice_pdf_url', sa.Text, nullable=True),
        
        # Indexes
        sa.Index('ix_billing_invoices_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_billing_invoices_tenant_period', 'tenant_id', 'period_start', 'period_end'),
        sa.Index('ix_billing_invoices_number', 'tenant_id', 'invoice_number'),
        sa.Index('ix_billing_invoices_created', 'created_at'),
    )
    
    # Unique constraint on invoice number per tenant
    op.create_unique_constraint(
        'uq_billing_invoices_tenant_number',
        'billing_invoices',
        ['tenant_id', 'invoice_number']
    )
    
    # ============================================================
    # Billing Invoice Items Table (Line Items)
    # ============================================================
    op.create_table(
        'billing_invoice_items',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('invoice_id', sa.String(100), nullable=False, index=True),
        
        # Item details
        sa.Column('stripe_invoice_item_id', sa.String(100), nullable=True, index=True),
        sa.Column('subscription_item_id', sa.String(100), nullable=True),
        sa.Column('price_id', sa.String(100), nullable=True),
        
        # Line item type and description
        sa.Column('type', sa.String(50), nullable=False),  # subscription, metered, one_time, proration
        sa.Column('description', sa.Text, nullable=False),
        
        # Quantity and pricing
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False, server_default='1'),
        sa.Column('unit_amount', sa.BigInteger, nullable=False),  # cents per unit
        sa.Column('amount', sa.BigInteger, nullable=False),  # total in cents
        
        # Period (for subscription items)
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        
        # Usage details (for metered items)
        sa.Column('usage_quantity', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('usage_metric', sa.String(100), nullable=True),
        
        # Tax and discounts
        sa.Column('tax_amount', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('discount_amount', sa.BigInteger, nullable=False, server_default='0'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign key to invoice
        sa.ForeignKeyConstraint(
            ['invoice_id'],
            ['billing_invoices.id'],
            ondelete='CASCADE'
        ),
        
        # Indexes
        sa.Index('ix_billing_invoice_items_invoice', 'invoice_id', 'created_at'),
        sa.Index('ix_billing_invoice_items_type', 'tenant_id', 'type'),
    )
    
    # ============================================================
    # Billing Charges Table (Charge Attempts)
    # ============================================================
    op.create_table(
        'billing_charges',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('customer_id', sa.String(100), nullable=False, index=True),
        sa.Column('invoice_id', sa.String(100), nullable=True, index=True),
        
        # Stripe charge details
        sa.Column('stripe_charge_id', sa.String(100), nullable=True, index=True),
        sa.Column('stripe_payment_intent_id', sa.String(100), nullable=True),
        
        # Charge details
        sa.Column('status', sa.String(50), nullable=False, index=True),  # succeeded, pending, failed
        sa.Column('amount', sa.BigInteger, nullable=False),  # cents
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('amount_refunded', sa.BigInteger, nullable=False, server_default='0'),
        
        # Payment method
        sa.Column('payment_method_id', sa.String(100), nullable=True),
        sa.Column('payment_method_type', sa.String(50), nullable=True),  # card, bank_transfer, etc.
        sa.Column('payment_method_details', postgresql.JSONB, nullable=True),
        
        # Failure details
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('failure_message', sa.Text, nullable=True),
        sa.Column('decline_code', sa.String(100), nullable=True),
        
        # Receipt and evidence
        sa.Column('receipt_url', sa.Text, nullable=True),
        sa.Column('receipt_number', sa.String(100), nullable=True),
        
        # Dispute info
        sa.Column('disputed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('dispute_reason', sa.String(100), nullable=True),
        
        # Metadata
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign key to invoice
        sa.ForeignKeyConstraint(
            ['invoice_id'],
            ['billing_invoices.id'],
            ondelete='SET NULL'
        ),
        
        # Indexes
        sa.Index('ix_billing_charges_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_billing_charges_tenant_created', 'tenant_id', 'created_at'),
        sa.Index('ix_billing_charges_stripe_id', 'stripe_charge_id'),
    )
    
    # ============================================================
    # Enable Row-Level Security
    # ============================================================
    op.execute("ALTER TABLE billing_invoices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE billing_invoice_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE billing_charges ENABLE ROW LEVEL SECURITY")
    
    # ============================================================
    # RLS Policies for Tenant Isolation
    # ============================================================
    
    # Billing Invoices - Tenant Isolation
    op.execute("""
        CREATE POLICY tenant_isolation_billing_invoices ON billing_invoices
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR OR
               current_setting('app.bypass_rls', true)::BOOLEAN = true)
    """)
    
    # Billing Invoice Items - Tenant Isolation (uses parent invoice tenant)
    op.execute("""
        CREATE POLICY tenant_isolation_billing_invoice_items ON billing_invoice_items
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR OR
               current_setting('app.bypass_rls', true)::BOOLEAN = true)
    """)
    
    # Billing Charges - Tenant Isolation
    op.execute("""
        CREATE POLICY tenant_isolation_billing_charges ON billing_charges
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR OR
               current_setting('app.bypass_rls', true)::BOOLEAN = true)
    """)


def downgrade() -> None:
    """Remove invoice and charge tables."""
    
    # Drop tables (will cascade drop policies and indexes)
    op.drop_table('billing_charges')
    op.drop_table('billing_invoice_items')
    op.drop_table('billing_invoices')
