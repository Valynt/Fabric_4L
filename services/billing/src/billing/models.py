"""SQLAlchemy ORM models for the billing service.

All tables include a ``tenant_id`` column and are protected by PostgreSQL
Row-Level Security (RLS) policies.  The session factory in ``database.py``
sets ``app.tenant_id`` via ``SET LOCAL`` before every query.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all billing ORM models."""


class SubscriptionStatus(str, PyEnum):
    """Stripe subscription statuses tracked in the database."""

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


class BillingCustomer(Base):
    """Customer record synced with Stripe.

    Maps application ``user_id`` to a Stripe customer for subscription management.
    """

    __tablename__ = "billing_customers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, primary_key=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    stripe_sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    stripe_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of customer email (raw PII not stored in ORM layer)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    subscriptions: Mapped[list[BillingSubscription]] = relationship(
        "BillingSubscription",
        back_populates="customer",
        cascade="all, delete-orphan",
        primaryjoin="and_(BillingCustomer.id == foreign(BillingSubscription.user_id), "
        "BillingCustomer.tenant_id == foreign(BillingSubscription.tenant_id))",
    )


class BillingSubscription(Base):
    """Subscription record synced with Stripe."""

    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        UniqueConstraint("stripe_subscription_id", name="uq_billing_subscriptions_stripe_id"),
        Index("ix_billing_subscriptions_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=SubscriptionStatus.INCOMPLETE.value,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    customer: Mapped[BillingCustomer] = relationship(
        "BillingCustomer",
        back_populates="subscriptions",
        primaryjoin="and_(foreign(BillingSubscription.user_id) == BillingCustomer.id, "
        "foreign(BillingSubscription.tenant_id) == BillingCustomer.tenant_id)",
    )


class BillingWebhookEvent(Base):
    """Idempotency table for processed Stripe webhook events."""

    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_billing_webhook_events_id_tenant"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="Stripe event ID")
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    livemode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

