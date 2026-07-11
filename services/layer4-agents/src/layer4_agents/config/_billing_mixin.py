"""Billing-related behavior for Layer 4 Settings.

This mixin contains only computed properties and helper methods that depend on
billing fields defined on the concrete Settings class. Fields remain on
Settings so env-var loading and validation stay centralized.
"""
from __future__ import annotations

from typing import Protocol


class _BillingSettingsProtocol(Protocol):
    billing_enabled: bool
    stripe_secret_key: str | None


class BillingSettingsMixin:
    """Mixin exposing billing configuration helpers."""

    @property
    def is_billing_configured(self: _BillingSettingsProtocol) -> bool:
        """Check if Stripe billing is properly configured."""
        return self.billing_enabled and self.stripe_secret_key is not None
