from __future__ import annotations

"""Shared async HTTP scaffolding for Layer 4 cross-layer integration clients.

Centralizes the duplicated patterns previously re-implemented in
``layer1_client``, ``layer2_client``, ``layer3_client``, ``layer5_client``
and ``adapters/benchmark_client``:

* tenant / service-auth / trace header injection (``ServiceAuthHeaders``),
* ``httpx.AsyncClient`` lifetime, connection limits and ``close()``
  semantics (``ServiceHttpClient``).

Edge clients extend :class:`ServiceHttpClient` and delegate request headers
to :meth:`ServiceHttpClient._get_headers` so a header or auth regression has
a single place to be authored and reviewed.
"""

import logging
import os
from typing import Final

import httpx
from value_fabric.shared.observability.trace_context import CANONICAL_TRACE_HEADER

logger = logging.getLogger(__name__)

TENANT_ID_HEADER: Final = "X-Tenant-ID"
SERVICE_AUTH_HEADER: Final = "X-Service-Auth"

DEFAULT_CONNECTION_LIMITS: Final = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
)


class ServiceAuthHeaders:
    """Centralized builder for tenant / service-auth / trace headers.

    ``SERVICE_AUTH_SECRET`` is read at call time (not cached) so both tests
    and runtime env changes are honored without re-instantiation.
    """

    def build(
        self,
        tenant_id: str | None = None,
        *,
        trace_id: str | None = None,
    ) -> dict[str, str]:
        """Return per-request headers for the given tenant context."""
        headers: dict[str, str] = {}
        if tenant_id:
            headers[TENANT_ID_HEADER] = tenant_id
        service_auth = os.getenv("SERVICE_AUTH_SECRET")
        if service_auth:
            headers[SERVICE_AUTH_HEADER] = service_auth
        if trace_id:
            headers[CANONICAL_TRACE_HEADER] = trace_id
        return headers


class ServiceHttpClient:
    """Base class owning ``httpx.AsyncClient`` lifetime and header injection.

    Subclasses keep control of their client attribute (eager ``self.client``
    vs lazy ``self._client``) but should reuse :meth:`_build_client` and
    :meth:`_get_headers`.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        tenant_id: str | None = None,
        limits: httpx.Limits | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._default_tenant_id = tenant_id
        self._limits = limits or DEFAULT_CONNECTION_LIMITS
        self._auth_headers = ServiceAuthHeaders()

    # ------------------------------------------------------------------
    # Header injection
    # ------------------------------------------------------------------

    def _get_headers(
        self,
        tenant_id: str | None = None,
        *,
        trace_id: str | None = None,
    ) -> dict[str, str]:
        """Build per-request headers with tenant context for service calls."""
        return self._auth_headers.build(
            tenant_id or self._default_tenant_id,
            trace_id=trace_id,
        )

    @staticmethod
    def client_auth_headers(api_key: str | None) -> dict[str, str]:
        """Headers constant for the lifetime of the client.

        Preserves the legacy ``Authorization`` behavior used by the Layer 1/2
        clients: a configured API key yields an Authorization header on every
        request.
        """
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    # ------------------------------------------------------------------
    # Client lifetime
    # ------------------------------------------------------------------

    def _build_client(
        self,
        *,
        headers: dict[str, str] | None = None,
        limits: httpx.Limits | None = None,
    ) -> httpx.AsyncClient:
        """Create an ``httpx.AsyncClient`` with shared limits and timeout."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            limits=limits or self._limits,
        )

    async def close(self) -> None:
            """Close the underlying HTTP client.

            Supports both documented styles: eagerly-created ``self.client`` and
            lazily-created ``self._client``. No-op if no client is present.
            """
            client = getattr(self, "client", None) or getattr(self, "_client", None)
            if client is not None:
                await client.aclose()
