"""Canonical billing runtime for Value Fabric Layer 4.

This module provides the stable import surface for billing domain models,
schemas, and service interfaces. During the L4 decomposition pilot, the
implementations are re-exported from the layer4-agents monolith. After the
billing service extraction completes, this module will redirect to
``services/billing/src/billing/``.

Compatibility: COMPAT-L4-002 (removal target 2026-09-30)
"""

from __future__ import annotations

from .models import (
    BillingCustomer,
    BillingInvoice,
    BillingInvoiceItem,
    BillingPlan,
    BillingSubscription,
    BillingUsageEvent,
    BillingWebhookEvent,
    Charge,
    PlanId,
    SubscriptionStatus,
)
from .schemas import (
    CheckoutRequest,
    CreateInvoiceRequest,
    CustomerSyncRequest,
    PortalRequest,
    SubscriptionResponse,
    UsageBatchRequest,
    UsageEventRequest,
)
from .services import BillingService

__all__ = [
    # Models
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
    # Schemas
    "CheckoutRequest",
    "CreateInvoiceRequest",
    "CustomerSyncRequest",
    "PortalRequest",
    "SubscriptionResponse",
    "UsageBatchRequest",
    "UsageEventRequest",
    # Services
    "BillingService",
]
