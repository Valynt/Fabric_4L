from __future__ import annotations

import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.usage_event import UsageEventRecord


class BillingEventPublisher:
    """Publishes gateway usage events to Layer 4/7 billing.

    Maps each gateway usage event to a billing usage event. The customer_id
    is the same as the tenant_id for gateway-billed usage; downstream billing
    services should treat it as the external customer reference.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer4_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer4_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str) -> dict[str, str]:
        return {
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
            "Content-Type": "application/json",
        }

    def _payload(self, event: UsageEventRecord) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "customer_id": event.tenant_id,
            "event_name": event.product_code,
            "metric_name": event.product_code,
            "quantity": event.quantity,
            "unit": event.unit or "request",
            "timestamp": event.timestamp,
            "metadata": {
                "endpoint": event.endpoint,
                "method": event.method,
                "api_key_id": event.api_key_id,
                **(event.metadata or {}),
            },
        }

    async def publish(self, event: UsageEventRecord) -> dict[str, Any]:
        url = f"{self.base_url}/v1/billing/events"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=self._payload(event),
                headers=self._headers(event.tenant_id),
            )
        # Accept 200/201/202; do not fail the API call if billing is unreachable.
        if response.status_code in (200, 201, 202):
            return response.json()
        return {"forwarded": False, "status_code": response.status_code, "body": response.text}
