"""Generated HTTP client for Layer 4: Agentic Workflow Engine."""

from __future__ import annotations

from typing import Any

import httpx


class L4Client:
    """HTTP client for Layer 4: Agentic Workflow Engine.

    Generated from OpenAPI spec at layer4-agents.json
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        elif jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        self._sync_client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._sync_client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json()

    async def _arequest(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._async_client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    async def ahealth(self) -> dict[str, Any]:
        """Check API health (async)."""
        return await self._arequest("GET", "/health")
