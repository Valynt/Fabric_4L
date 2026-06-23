"""Shared Pydantic-only billing schemas for cross-service communication.

These schemas are shared between ``services/billing/`` (the Stripe billing service)
and any service that calls it (e.g. ``services/layer4-agents/``).

No SQLAlchemy models are exported from this package — only serialisable Pydantic
types that can travel across HTTP boundaries.
"""

from .customers import CustomerCreateRequest, CustomerRead
from .plans import PlanId, SubscriptionStatus
from .subscriptions import SubscriptionCreateRequest, SubscriptionRead
from .webhooks import WebhookEvent

__all__ = [
    "CustomerCreateRequest",
    "CustomerRead",
    "PlanId",
    "SubscriptionCreateRequest",
    "SubscriptionRead",
    "SubscriptionStatus",
    "WebhookEvent",
]
