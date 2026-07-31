from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
from fastapi import HTTPException
from value_fabric.shared.models import JSONDict

from app.core.config import get_settings

if TYPE_CHECKING:
    pass


class Layer3Client:
    """Internal client to the Layer 3 knowledge graph service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer3_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer3_timeout_seconds
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
        json: JSONDict | None = None,
        params: dict[str, str] | None = None,
    ) -> JSONDict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(tenant_id),
                json=json,
                params=params,
            )
        if response.status_code >= 400:
            detail = response.text or f"Layer 3 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def query_entities(
        self,
        tenant_id: str,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> JSONDict:
        """Query entities from the knowledge graph."""
        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        if entity_type is not None:
            params["entity_type"] = entity_type
        return await self._request("GET", "/v1/query/entities", tenant_id, params=params)

    async def search(
        self,
        tenant_id: str,
        query: str = "",
        limit: int = 10,
    ) -> JSONDict:
        """Hybrid search in the knowledge graph."""
        return await self._request("POST", "/v1/search", tenant_id, {"query": query, "limit": limit})

    async def get_value_tree(self, tenant_id: str, tree_id: str) -> JSONDict:
        """Get a value tree by ID."""
        return await self._request("GET", f"/v1/value-trees/{tree_id}", tenant_id)

    async def ingest_rdf(
        self,
        tenant_id: str,
        rdf_data: str = "",
        source_version_id: str = "",
    ) -> JSONDict:
        """Ingest RDF data into the knowledge graph."""
        return await self._request(
            "POST",
            "/v1/ingest",
            tenant_id,
            {"rdf": rdf_data, "source_version_id": source_version_id},
        )

    async def query_graphrag(
        self,
        tenant_id: str,
        question: str = "",
        context: JSONDict | None = None,
    ) -> JSONDict:
        """Query using GraphRAG."""
        payload: JSONDict = {"question": question}
        if context is not None:
            payload["context"] = context
        return await self._request("POST", "/v1/query/graphrag", tenant_id, payload)
