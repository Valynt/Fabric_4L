"""Canonical billing models — re-exported from layer4-agents during pilot.

See COMPAT-L4-002 for migration timeline.
"""

from __future__ import annotations

# Runtime import from the current canonical source tree.
# After billing service extraction, these will be defined locally.
from value_fabric.layer4.models.billing import (
    BillingCharge as Charge,
    BillingCustomer,
    BillingInvoice,
    BillingInvoiceItem,
    BillingPlanVersion as BillingPlan,
    BillingSubscription,
    BillingUsageEvent,
    BillingWebhookEvent,
    PlanId,
    SubscriptionStatus,
)

__all__ = [
    "BillingCustomer",
    "BillingInvoice",
    "BillingInvoiceItem",
    "BillingPlan",
    "BillingSubscription",
    "BillingUsageEvent",
    "BillingWebhookEvent",
    "Charge",
    "PlanId",
    "SubscriptionStatus",
]
