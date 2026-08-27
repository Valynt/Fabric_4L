"""Canonical Layer 2 Extraction HTTP transport.

This module is the single authoritative home for the Layer 2 Extraction
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
    "EXTRACT_AND_INGEST_PATH",
    "EXTRACT_BATCH_PATH",
    "EXTRACT_PATH",
    "EXTRACT_STATUS_PATH",
    "LAYER2_ENDPOINTS",
    "Layer2Transport",
    "Layer2TransportError",
]

# ---------------------------------------------------------------------------
# Endpoint contract — single source of truth for Layer 2 API paths
# ---------------------------------------------------------------------------

EXTRACT_PATH = "/v1/extract"
EXTRACT_AND_INGEST_PATH = "/v1/extract-and-ingest"
EXTRACT_STATUS_PATH = "/v1/extract/status/{job_id}"
EXTRACT_BATCH_PATH = "/v1/extract/batch"

#: Registry used by tests to prove every endpoint literal is still live in the
#: authoritative OpenAPI contract (drift regression guard).
LAYER2_ENDPOINTS: dict[str, str] = {
    "extract": EXTRACT_PATH,
    "extract_and_ingest": EXTRACT_AND_INGEST_PATH,
    "extract_status": EXTRACT_STATUS_PATH,
    "extract_batch": EXTRACT_BATCH_PATH,
}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class Layer2TransportError(RuntimeError):
    """Raised by :class:`Layer2Transport` for any 4xx/5xx Layer 2 response."""

    def __init__(self, message: str, *, status_code: int, response_text: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class Layer2Transport:
    """Contract-aware HTTP transport for the Layer 2 Extraction service.

    Owns only transport concerns:

    - base URL construction
    - service-to-service auth (``X-Tenant-ID`` + ``X-Service-Auth``)
    - JSON serialization and query params
    - per-request timeout
    - HTTP status boundary (raises :class:`Layer2TransportError` on >= 400)

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
        """Send a request to Layer 2 and return the verified response.

        Raises:
            Layer2TransportError: Any 4xx/5xx upstream response.
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
            detail = response.text or f"Layer 2 request failed ({response.status_code})"
            raise Layer2TransportError(
                detail,
                status_code=response.status_code,
                response_text=response.text or "",
            )
        return response