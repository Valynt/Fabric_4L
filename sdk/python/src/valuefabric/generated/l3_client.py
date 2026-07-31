"""Generated HTTP client for Value Fabric - Knowledge Graph & Semantic Layer."""

from __future__ import annotations

from typing import Any

import httpx

from .l3 import SearchRequest, SearchResponse


class L3Client:
    """HTTP client for Value Fabric - Knowledge Graph & Semantic Layer.

    Generated from OpenAPI spec at layer3-knowledge.json
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
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Expected a JSON object response")
        return payload

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
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Expected a JSON object response")
        return payload

    def health(self) -> dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    async def ahealth(self) -> dict[str, Any]:
        """Check API health (async)."""
        return await self._arequest("GET", "/health")

    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute canonical hybrid search."""
        payload = self._request(
            "POST",
            "/v1/search/hybrid",
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return SearchResponse.model_validate(payload)

    async def asearch(self, request: SearchRequest) -> SearchResponse:
        """Execute canonical hybrid search asynchronously."""
        payload = await self._arequest(
            "POST",
            "/v1/search/hybrid",
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return SearchResponse.model_validate(payload)
