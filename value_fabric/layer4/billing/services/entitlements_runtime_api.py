"""Single billing entitlement decision runtime API client for Layer 4."""

from __future__ import annotations

import os
import requests


class BillingEntitlementClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("LAYER7_BILLING_URL", "http://localhost:8007")

    def decide(self, *, tenant_id: str, actor: str, plan_id: str, feature: str) -> dict:
        response = requests.get(
            f"{self.base_url}/v1/billing/entitlements/{plan_id}/decision",
            params={"feature": feature},
            headers={"x-tenant-id": tenant_id, "x-actor": actor, "x-roles": "billing:read"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
