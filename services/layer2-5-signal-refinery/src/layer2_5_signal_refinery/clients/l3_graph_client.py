from __future__ import annotations

import logging
from typing import Any

import httpx

from value_fabric.shared.resilience import CircuitBreaker, CircuitBreakerOpen

from ..config import get_settings

"""L3 Knowledge Graph client for L2.5 Signal Refinery.

Pushes ValueSignal objects to L3 as graph nodes after refinement.
All operations are best-effort — L2.5 remains operational if L3 is unavailable.

P1-014 pilot: circuit breaker protects the L3 push path.
"""

logger = logging.getLogger(__name__)

# P1-014 pilot: single breaker for the L3 downstream dependency
_l3_circuit_breaker = CircuitBreaker(
    service_name="layer3-knowledge",
    failure_threshold=3,
    recovery_timeout=30.0,
    half_open_max_calls=1,
)


class L3GraphClient:
    """Async HTTP client for the L3 Knowledge Graph signal endpoints.

    Uses a single shared httpx.AsyncClient for connection pooling across calls.
    Call ``aclose()`` during application shutdown to release connections.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def _base_url(self) -> str:
        return self._settings.layer3_base_url.rstrip("/")

    async def aclose(self) -> None:
        """Close the underlying HTTP client. Call during application shutdown."""
        await self._client.aclose()

    async def push_signal(
        self,
        signal: dict[str, Any],
        tenant_id: str,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> bool:
        """Push a ValueSignal to L3 as a graph node.

        Returns True on success, False on any failure (non-blocking).
        Protected by a circuit breaker (P1-014 pilot).
        """
        headers = {"X-Tenant-ID": tenant_id}
        if request_id:
            headers["X-Request-ID"] = request_id
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        elif request_id:
            headers["X-Correlation-ID"] = request_id

        try:
            response = await _l3_circuit_breaker.call(
                self._client.post,
                f"{self._base_url}/api/v1/graph/signals",
                json=signal,
                headers=headers,
            )
            if response.status_code in (200, 201):
                return True
            logger.warning(
                "L3 signal push returned %s for signal %s",
                response.status_code,
                signal.get("id"),
            )
            return False
        except CircuitBreakerOpen:
            logger.warning(
                "L3 signal push skipped for signal %s — circuit breaker is open",
                signal.get("id"),
            )
            return False
        except Exception:
            logger.warning(
                "L3 signal push failed for signal %s — L3 may be unavailable",
                signal.get("id"),
                exc_info=True,
            )
            return False

    async def get_account_signals(
        self,
        account_id: str,
        tenant_id: str,
        *,
        lifecycle_states: list[str] | None = None,
        signal_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query L3 for ValueSignal nodes for an account.

        Returns empty list on failure.
        """
        params: dict[str, Any] = {"account_id": account_id}
        if lifecycle_states:
            params["lifecycle_states"] = lifecycle_states
        if signal_types:
            params["types"] = signal_types

        headers = {"X-Tenant-ID": tenant_id}
        try:
            response = await self._client.get(
                f"{self._base_url}/api/v1/graph/signals",
                params=params,
                headers=headers,
            )
            if response.status_code == 200:
                return response.json().get("items", [])
            return []
        except Exception:
            logger.warning("L3 signal query failed", exc_info=True)
            return []


_client: L3GraphClient | None = None


def get_l3_client() -> L3GraphClient:
    global _client
    if _client is None:
        _client = L3GraphClient()
    return _client
