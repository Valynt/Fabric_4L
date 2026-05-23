"""Canonical billing service interfaces — re-exported from layer4-agents during pilot.

See COMPAT-L4-002 for migration timeline.
"""

from __future__ import annotations

from value_fabric.layer4.services.billing_service import BillingService

__all__ = ["BillingService"]
