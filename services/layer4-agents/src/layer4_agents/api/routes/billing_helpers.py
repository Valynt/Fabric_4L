"""Pure serialization and request helper utilities for Layer 4 billing routes.

Extracted to isolate request shaping and data formatting from routing logic,
mitigating import cycles and churn.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from ...models.billing import (
        BillingCharge,
        BillingCustomer,
        BillingInvoice,
        BillingInvoiceItem,
        BillingSubscription,
        BillingUsageEvent,
    )

logger = logging.getLogger(__name__)

# Known Stripe webhook IPs (documented by Stripe) + loopback for local dev
_STRIPE_WEBHOOK_IPS = {"3.18.12.63", "52.15.183.38", "54.187.174.170", "127.0.0.1", "::1"}


def is_stripe_webhook_ip(ip: str) -> bool:
    """Return True if *ip* is a known Stripe webhook or loopback address."""
    return ip in _STRIPE_WEBHOOK_IPS


def get_client_ip(request: Request) -> str:
    """Extract the client IP from forwarded headers or the transport socket."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    x_real = request.headers.get("X-Real-IP")
    if x_real:
        return x_real.strip()
    if request.client is not None:
        return request.client.host
    return ""


def dt_iso(dt: datetime | None) -> str | None:
    """Serialize a datetime to ISO format."""
    return dt.isoformat() if dt else None


def serialize_subscription(sub: BillingSubscription | None) -> dict[str, object]:
    """Serialize a BillingSubscription to the frontend contract shape."""
    if sub is None:
        return {
            "id": None,
            "plan_id": "free",
            "status": "active",
            "current_period_start": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "status": sub.status,
        "current_period_start": dt_iso(sub.current_period_start),
        "current_period_end": dt_iso(sub.current_period_end),
        "cancel_at_period_end": sub.cancel_at_period_end,
    }


def serialize_invoice_item(item: BillingInvoiceItem) -> dict[str, object]:
    """Serialize an invoice item to JSON-compatible dictionary."""
    return {
        "id": item.id,
        "type": item.type,
        "description": item.description,
        "quantity": float(item.quantity),
        "unit_amount_cents": item.unit_amount,
        "amount_cents": item.amount,
        "amount_dollars": item.amount_dollars,
        "period_start": dt_iso(item.period_start),
        "period_end": dt_iso(item.period_end),
        "usage_quantity": float(item.usage_quantity) if item.usage_quantity is not None else None,
        "usage_metric": item.usage_metric,
        "tax_cents": item.tax_amount,
        "discount_cents": item.discount_amount,
    }


def serialize_charge(charge: BillingCharge) -> dict[str, object]:
    """Serialize a charge record to JSON-compatible dictionary."""
    return {
        "id": charge.id,
        "customer_id": charge.customer_id,
        "invoice_id": charge.invoice_id,
        "invoice_number": charge.invoice.invoice_number if charge.invoice else None,
        "status": charge.status,
        "amount_cents": charge.amount,
        "amount_dollars": charge.amount_dollars,
        "amount_refunded_cents": charge.amount_refunded,
        "net_amount_cents": charge.net_amount,
        "stripe_charge_id": charge.stripe_charge_id,
        "payment_method_id": charge.payment_method_id,
        "payment_method_type": charge.payment_method_type,
        "failure_code": charge.failure_code,
        "failure_message": charge.failure_message,
        "receipt_url": charge.receipt_url,
        "description": charge.description,
        "created_at": dt_iso(charge.created_at),
        "captured_at": dt_iso(charge.captured_at),
        "refunded_at": dt_iso(charge.refunded_at),
    }


def serialize_invoice(
    inv: BillingInvoice, *, include_items: bool = True, include_charges: bool = False
) -> dict[str, object]:
    """Serialize an invoice record to JSON-compatible dictionary."""
    result: dict[str, object] = {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id": inv.customer_id,
        "status": inv.status,
        "currency": inv.currency,
        "subtotal_cents": inv.subtotal,
        "tax_cents": inv.tax,
        "total_cents": inv.total,
        "total_dollars": inv.total_dollars,
        "amount_paid_cents": inv.amount_paid,
        "amount_due_cents": inv.amount_due,
        "amount_due_dollars": inv.amount_due_dollars,
        "balance_cents": inv.balance,
        "period_start": dt_iso(inv.period_start),
        "period_end": dt_iso(inv.period_end),
        "due_date": dt_iso(inv.due_date),
        "paid_at": dt_iso(inv.paid_at),
        "voided_at": dt_iso(inv.voided_at),
        "created_at": dt_iso(inv.created_at),
        "description": inv.description,
        "hosted_invoice_url": inv.hosted_invoice_url,
        "invoice_pdf_url": inv.invoice_pdf_url,
    }
    if include_items:
        result["items"] = [serialize_invoice_item(item) for item in (inv.items or [])]
    if include_charges:
        result["charges"] = [serialize_charge(charge) for charge in (inv.charges or [])]
    return result


def serialize_usage_event(event: BillingUsageEvent) -> dict[str, object]:
    """Serialize a usage event to JSON-compatible dictionary."""
    return {
        "id": event.id,
        "event_id": event.event_id,
        "customer_id": event.customer_id,
        "tenant_id": event.tenant_id,
        "event_name": event.event_name,
        "metric_name": event.metric_name,
        "quantity": event.quantity,
        "timestamp": dt_iso(event.timestamp),
        "created_at": dt_iso(event.created_at),
        "status": event.status,
        "unit": event.unit,
    }


def serialize_customer(customer: BillingCustomer) -> dict[str, object]:
    """Serialize a customer record to JSON-compatible dictionary."""
    return {
        "id": customer.id,
        "tenant_id": customer.tenant_id,
        "email": customer.email,
        "name": customer.name,
        "stripe_customer_id": customer.stripe_customer_id,
    }
