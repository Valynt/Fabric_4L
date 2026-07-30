from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer1Client:
    """Internal client to the Layer 1 ingestion service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer1_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer1_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str) -> dict[str, str]:
        return {
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        tenant_id: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(tenant_id),
                json=json,
            )
        if response.status_code >= 400:
            detail = response.text or f"Layer 1 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def create_source(
        self,
        tenant_id: str,
        url: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new source in the Layer 1 catalog."""
        payload = {"url": url}
        if name:
            payload["name"] = name
        if config:
            payload["config"] = config
        return await self._request("POST", "/api/v1/ingestion/sources", tenant_id, json=payload)

    async def create_source_version(
        self,
        tenant_id: str,
        source_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new version for a source."""
        payload = {"content": content}
        if metadata:
            payload["metadata"] = metadata
        return await self._request("POST", f"/api/v1/ingestion/sources/{source_id}/versions", tenant_id, json=payload)

    async def create_ingestion_run(
        self,
        tenant_id: str,
        source_version_id: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Trigger an ingestion run for a source version."""
        payload = {"source_version_id": source_version_id}
        if config:
            payload["config"] = config
        return await self._request("POST", "/api/v1/ingestion/runs", tenant_id, json=payload)

    async def get_ingestion_run(
        self,
        tenant_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        """Get status of an ingestion run."""
        return await self._request("GET", f"/api/v1/ingestion/runs/{run_id}", tenant_id)

    async def list_sources(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List sources in the catalog."""
        return await self._request("GET", "/api/v1/ingestion/sources", tenant_id, json={"limit": limit, "offset": offset})