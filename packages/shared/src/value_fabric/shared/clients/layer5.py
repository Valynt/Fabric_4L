"""Canonical Layer 5 Ground Truth HTTP transport.

This module is the single authoritative home for the Layer 5 Ground Truth
service endpoint literals and the transport that reaches them: URL
construction, service-to-service auth headers, JSON serialization, timeout,
and the HTTP status boundary.

Error *translation* into consumer semantics (gateway ``HTTPException(502)``
vs agent structured result dicts) intentionally lives in each consumer so
gateway and agent callers are not forced to share application-level error
behavior.  Retry policy is a consumer concern as well and is deliberately
not implemented here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from value_fabric.shared.identity.constants import (
    SERVICE_AUTH_HEADER,
    TENANT_ID_HEADER,
)

__all__ = [
    "HEALTH_PATH",
    "LAYER5_ENDPOINTS",
    "MATURITY_LADDER_PATH",
    "TRUTHS_CHECK_STALE_PATH",
    "TRUTHS_FRESHNESS_SUMMARY_PATH",
    "TRUTHS_PATH",
    "TRUTHS_STALE_PATH",
    "TRUTHS_SYNC_KG_PATH",
    "TRUTH_AUDIT_PATH",
    "TRUTH_ITEM_PATH",
    "TRUTH_SOURCES_PATH",
    "TRUTH_VALIDATE_PATH",
    "Layer5Transport",
    "Layer5TransportError",
]

# ---------------------------------------------------------------------------
# Endpoint contract — single source of truth for Layer 5 API paths
# ---------------------------------------------------------------------------

HEALTH_PATH = "/health"

TRUTHS_PATH = "/api/v1/truths"
TRUTH_ITEM_PATH = "/api/v1/truths/{truth_id}"
TRUTH_VALIDATE_PATH = "/api/v1/truths/{truth_id}/validate"
TRUTH_AUDIT_PATH = "/api/v1/truths/{truth_id}/audit"
TRUTH_SOURCES_PATH = "/api/v1/truths/{truth_id}/sources"
TRUTHS_SYNC_KG_PATH = "/api/v1/truths/sync-kg"
TRUTHS_CHECK_STALE_PATH = "/api/v1/truths/check-stale"
TRUTHS_STALE_PATH = "/api/v1/truths/stale"
TRUTHS_FRESHNESS_SUMMARY_PATH = "/api/v1/truths/freshness-summary"
MATURITY_LADDER_PATH = "/api/v1/maturity-ladder"

#: Registry used by tests to prove every endpoint literal is still live in the
#: authoritative OpenAPI contract (drift regression guard).  The ``HEALTH_PATH``
#: probe is intentionally excluded: it is a non-OpenAPI system endpoint and is
#: not part of the contract surface.
LAYER5_ENDPOINTS: dict[str, str] = {
    "list_truths": TRUTHS_PATH,
    "submit_truth": TRUTHS_PATH,
    "get_truth": TRUTH_ITEM_PATH,
    "validate_truth": TRUTH_VALIDATE_PATH,
    "get_truth_audit": TRUTH_AUDIT_PATH,
    "add_truth_sources": TRUTH_SOURCES_PATH,
    "sync_kg": TRUTHS_SYNC_KG_PATH,
    "check_stale": TRUTHS_CHECK_STALE_PATH,
    "get_stale_truths": TRUTHS_STALE_PATH,
    "get_freshness_summary": TRUTHS_FRESHNESS_SUMMARY_PATH,
    "get_maturity_ladder": MATURITY_LADDER_PATH,
}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class Layer5TransportError(RuntimeError):
    """Raised by :class:`Layer5Transport` for any 4xx/5xx Layer 5 response."""

    def __init__(self, message: str, *, status_code: int, response_text: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class Layer5Transport:
    """Contract-aware HTTP transport for the Layer 5 Ground Truth service.

    Owns only transport concerns:

    - base URL construction
    - service-to-service auth (``X-Tenant-ID`` + ``X-Service-Auth``)
    - JSON serialization and query params
    - per-request timeout
    - HTTP status boundary (raises :class:`Layer5TransportError` on >= 400)

    Tenant isolation is preserved: an authenticated tenant must be supplied
    per request and is always attached to the outbound headers.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 30.0,
        service_secret: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.service_secret = service_secret

    @staticmethod
    def build_headers(tenant_id: str, service_secret: str) -> dict[str, str]:
        """Build the standard service-to-service auth header set."""
        return {
            TENANT_ID_HEADER: tenant_id,
            SERVICE_AUTH_HEADER: service_secret,
            "Content-Type": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        tenant_id: str,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send a request to Layer 5 and return the verified response.

        Raises:
            Layer5TransportError: Any 4xx/5xx upstream response.
            httpx.HTTPError: Network/timeout failures (propagated unchanged so
                consumers keep their own retry semantics).
        """
        url = f"{self.base_url}{path}"
        headers = self.build_headers(tenant_id, self.service_secret)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
            )
        if response.status_code >= 400:
            detail = response.text or f"Layer 5 request failed ({response.status_code})"
            raise Layer5TransportError(
                detail,
                status_code=response.status_code,
                response_text=response.text or "",
            )
        return response