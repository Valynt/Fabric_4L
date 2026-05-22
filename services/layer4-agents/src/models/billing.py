"""SQLAlchemy models for Stripe billing integration.

Billing layer includes: subscription management, customer sync, webhook idempotency,
usage-based metering, and invoice/charge tracking with tenant isolation.

SECURITY: All tables have Row-Level Security (RLS) policies for multi-tenant isolation.
IDEMPOTENCY: Duplicate event detection via unique constraints on (tenant_id, event_id).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class SubscriptionStatus(str, PyEnum):
    """Stripe subscription statuses we care about."""

    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"


class PlanId(str, PyEnum):
    """Internal plan identifiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UsageEventStatus(str, PyEnum):
    """Status of a usage event."""

    PENDING = "pending"  # Received but not yet aggregated
    PROCESSED = "processed"  # Included in billing calculation
    FAILED = "failed"  # Validation or processing error
    IGNORED = "ignored"  # Duplicate or out-of-period event


class BillingCustomer(Base):
    """Customer record synced with Stripe.

    Maps app user_id to Stripe customer for subscription management.
    """

    __tablename__ = "billing_customers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # App user_id
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, primary_key=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    stripe_sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    stripe_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_sync_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    subscriptions: Mapped[list[BillingSubscription]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_billing_customers_stripe_id", "stripe_customer_id"),
        Index("ix_billing_customers_tenant", "tenant_id"),
        # Composite unique constraint for tenant-scoped customer lookup
        # Different tenants can have customers with the same logical ID
        UniqueConstraint("tenant_id", "id", name="uq_billing_customers_tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<BillingCustomer(id={self.id}, stripe_id={self.stripe_customer_id})>"


class BillingSubscription(Base):
    """Subscription record synced with Stripe.

    Tracks plan, status, and billing period for entitlement checks.
    """

    __tablename__ = "billing_subscriptions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False, default=PlanId.FREE)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionStatus.INCOMPLETE
    )
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    customer: Mapped[BillingCustomer] = relationship(back_populates="subscriptions")

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "customer_id"], ["billing_customers.tenant_id", "billing_customers.id"], ondelete="CASCADE"),
        Index("ix_billing_subscriptions_customer", "tenant_id", "customer_id"),
        Index("ix_billing_subscriptions_status", "status"),
        Index("ix_billing_subscriptions_plan", "plan_id"),
        Index("ix_billing_subscriptions_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<BillingSubscription(id={self.id}, plan={self.plan_id}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is in an active state."""
        return self.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        )

    @property
    def is_canceled(self) -> bool:
        """Check if subscription is canceled or will cancel."""
        return self.status == SubscriptionStatus.CANCELED or self.cancel_at_period_end


class BillingWebhookEvent(Base):
    """Webhook event log for idempotency.

    Prevents duplicate processing of Stripe webhook events.
    """

    __tablename__ = "billing_webhook_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Stripe event ID
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_billing_webhook_events_type", "type"),
        Index("ix_billing_webhook_events_processed", "processed_at"),
        Index("ix_billing_webhook_events_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<BillingWebhookEvent(id={self.id}, type={self.type})>"


class BillingUsageEvent(Base):
    """Usage event for metering and billing.

    High-throughput event ingestion for usage-based billing.
    Events are aggregated into billable quantities at period end.

    SECURITY: Events are tenant-scoped via RLS policies.
    IDEMPOTENCY: Duplicate event_id within tenant is rejected.
    """

    __tablename__ = "billing_usage_events"

    # Primary key - UUID generated by application or database
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Tenant isolation
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Customer attribution
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Event identification (idempotency key)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Event type and metric
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Quantities
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamping
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UsageEventStatus.PENDING, index=True
    )

    # Metadata for debugging and enrichment
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "customer_id"], ["billing_customers.tenant_id", "billing_customers.id"], ondelete="CASCADE"),
        # Idempotency: event_id + tenant_id must be unique
        UniqueConstraint("tenant_id", "event_id", name="uq_billing_usage_events_tenant_event"),
        # Query optimization indexes
        Index("ix_billing_usage_events_customer_timestamp", "tenant_id", "customer_id", "timestamp"),
        Index("ix_billing_usage_events_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BillingUsageEvent(id={self.id}, customer={self.customer_id}, metric={self.metric_name}, qty={self.quantity})>"


class InvoiceStatus:
    """Invoice status constants."""

    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class BillingInvoice(Base):
    """Invoice record for customer billing period.

    Stores invoice headers with financial totals and billing period.
    Line items are stored in BillingInvoiceItem.

    SECURITY: Invoices are tenant-scoped via RLS policies.
    """

    __tablename__ = "billing_invoices"

    # Primary key - UUID generated by application
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Tenant isolation
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Customer attribution
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Stripe IDs (nullable for offline invoices)
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Invoice details
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default=InvoiceStatus.DRAFT)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Financial amounts (stored in cents to avoid float precision issues)
    subtotal: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    amount_paid: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    amount_due: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)  # Can be negative for credit

    # Billing period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Display
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Hosted resources
    hosted_invoice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    items: Mapped[list[BillingInvoiceItem]] = relationship(
        "BillingInvoiceItem",
        back_populates="invoice",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    charges: Mapped[list[BillingCharge]] = relationship(
        "BillingCharge",
        back_populates="invoice",
        lazy="selectin"
    )

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "customer_id"], ["billing_customers.tenant_id", "billing_customers.id"], ondelete="CASCADE"),
        UniqueConstraint("tenant_id", "invoice_number", name="uq_billing_invoices_tenant_number"),
        Index("ix_billing_invoices_tenant_status", "tenant_id", "status"),
        Index("ix_billing_invoices_tenant_period", "tenant_id", "period_start", "period_end"),
        Index("ix_billing_invoices_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BillingInvoice(id={self.id}, number={self.invoice_number}, status={self.status}, total={self.total})>"

    @property
    def total_dollars(self) -> float:
        """Convert total cents to dollars."""
        return self.total / 100.0

    @property
    def amount_due_dollars(self) -> float:
        """Convert amount due cents to dollars."""
        return self.amount_due / 100.0


class BillingInvoiceItem(Base):
    """Line item for a billing invoice.

    Each invoice has one or more line items representing charges.
    Items can be subscription charges, metered usage, one-time fees, or prorations.

    SECURITY: Items are tenant-scoped via RLS policies (same as parent invoice).
    """

    __tablename__ = "billing_invoice_items"

    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Tenant isolation
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Parent invoice
    invoice_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Stripe IDs
    stripe_invoice_item_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    subscription_item_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Item details
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # subscription, metered, one_time, proration
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Pricing
    quantity: Mapped[float] = mapped_column(Numeric(precision=20, scale=8), nullable=False, default=1.0)
    unit_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # cents per unit
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # total in cents (quantity * unit_amount)

    # Period (for subscription/metered items)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Usage details (for metered billing)
    usage_quantity: Mapped[float | None] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    usage_metric: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Adjustments
    tax_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Metadata
    item_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    invoice: Mapped[BillingInvoice] = relationship("BillingInvoice", back_populates="items")

    __table_args__ = (
        Index("ix_billing_invoice_items_invoice", "invoice_id", "created_at"),
        Index("ix_billing_invoice_items_type", "tenant_id", "type"),
    )

    def __repr__(self) -> str:
        return f"<BillingInvoiceItem(id={self.id}, type={self.type}, amount={self.amount})>"

    @property
    def amount_dollars(self) -> float:
        """Convert amount cents to dollars."""
        return self.amount / 100.0


class ChargeStatus:
    """Charge status constants."""

    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"


class BillingCharge(Base):
    """Charge attempt record for payment processing.

    Tracks both successful and failed charge attempts.
    Provides audit trail for payment disputes and reconciliation.

    SECURITY: Charges are tenant-scoped via RLS policies.
    """

    __tablename__ = "billing_charges"

    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Tenant isolation
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Customer attribution
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional invoice link
    invoice_id: Mapped[str | None] = mapped_column(
        String(100), ForeignKey("billing_invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Stripe IDs
    stripe_charge_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Charge details
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default=ChargeStatus.PENDING)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # cents
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    amount_refunded: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Payment method
    payment_method_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_method_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_method_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Failure details
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Receipt evidence
    receipt_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Dispute tracking
    disputed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dispute_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    charge_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    invoice: Mapped[BillingInvoice | None] = relationship("BillingInvoice", back_populates="charges")

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "customer_id"], ["billing_customers.tenant_id", "billing_customers.id"], ondelete="CASCADE"),
        Index("ix_billing_charges_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_billing_charges_tenant_status", "tenant_id", "status"),
        Index("ix_billing_charges_tenant_created", "tenant_id", "created_at"),
        Index("ix_billing_charges_stripe_id", "stripe_charge_id"),
    )

    def __repr__(self) -> str:
        return f"<BillingCharge(id={self.id}, status={self.status}, amount={self.amount})>"

    @property
    def amount_dollars(self) -> float:
        """Convert amount cents to dollars."""
        return self.amount / 100.0

    @property
    def net_amount(self) -> int:
        """Net amount after refunds."""
        return self.amount - self.amount_refunded
