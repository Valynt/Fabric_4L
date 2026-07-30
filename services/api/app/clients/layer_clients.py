from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer3Client:
    """Internal client to the Layer 3 Knowledge Graph service."""

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
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        if entity_type:
            params["entity_type"] = entity_type
        return await self._request("GET", "/v1/query/entities", tenant_id, params=params)

    async def search(
        self,
        tenant_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/search",
            tenant_id,
            json={"query": query, "limit": limit},
        )

    async def get_value_tree(
        self,
        tenant_id: str,
        tree_id: str,
    ) -> dict[str, Any]:
        return await self._request("GET", f"/v1/value-trees/{tree_id}", tenant_id)

    async def ingest_rdf(
        self,
        tenant_id: str,
        rdf_data: str,
        source_version_id: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/ingest",
            tenant_id,
            json={"rdf": rdf_data, "source_version_id": source_version_id},
        )


class Layer5Client:
    """Internal client to the Layer 5 Ground Truth service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer5_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer5_timeout_seconds
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
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
            detail = response.text or f"Layer 5 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def list_truths(
        self,
        tenant_id: str,
        status: str | None = None,
        claim_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if claim_type:
            params["claim_type"] = claim_type
        return await self._request("GET", "/api/v1/truths", tenant_id, params=params)

    async def get_truth(
        self,
        tenant_id: str,
        truth_id: str,
    ) -> dict[str, Any]:
        return await self._request("GET", f"/api/v1/truths/{truth_id}", tenant_id)

    async def submit_truth(
        self,
        tenant_id: str,
        claim: str,
        claim_type: str,
        confidence: float,
        value: dict[str, Any] | None = None,
        applies_to: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body = {
            "claim": claim,
            "claim_type": claim_type,
            "confidence": confidence,
        }
        if value:
            body["value"] = value
        if applies_to:
            body["applies_to"] = applies_to
        if sources:
            body["sources"] = sources
        return await self._request("POST", "/api/v1/truths", tenant_id, json=body)

    async def validate_truth(
        self,
        tenant_id: str,
        truth_id: str,
        action: str,
        actor: str,
        actor_type: str = "system",
        notes: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "action": action,
            "actor": actor,
            "actor_type": actor_type,
        }
        if notes:
            payload["notes"] = notes
        return await self._request("POST", f"/api/v1/truths/{truth_id}/validate", tenant_id, json=payload)

    async def sync_kg(self, tenant_id: str) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/truths/sync-kg", tenant_id)


class Layer1Client:
    """Internal client to the Layer 1 Ingestion service."""

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
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
            detail = response.text or f"Layer 1 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def create_source(
        self,
        tenant_id: str,
        url: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {"url": url}
        if config:
            body["config"] = config
        return await self._request("POST", "/api/v1/ingestion/sources", tenant_id, json=body)

    async def create_source_version(
        self,
        tenant_id: str,
        source_id: str,
        content: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/ingestion/sources/{source_id}/versions",
            tenant_id,
            json={"content": content},
        )

    async def start_ingestion_run(
        self,
        tenant_id: str,
        source_version_id: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {"source_version_id": source_version_id}
        if config:
            body["config"] = config
        return await self._request("POST", "/api/v1/ingestion/runs", tenant_id, json=body)

    async def get_ingestion_run(
        self,
        tenant_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        return await self._request("GET", f"/api/v1/ingestion/runs/{run_id}", tenant_id)


class Layer2Client:
    """Internal client to the Layer 2 Extraction service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer2_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer2_timeout_seconds
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
            detail = response.text or f"Layer 2 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def extract(
        self,
        tenant_id: str,
        content: str,
        content_type: str = "text",
        extraction_method: str = "deterministic",
        source_id: str | None = None,
        job_id: str | None = None,
        model_version: str | None = None,
        schema_version: str = "1.0",
        prompt_version: str = "entity_extraction_v1",
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {
            "content": content,
            "content_type": content_type,
            "extraction_method": extraction_method,
        }
        if source_id:
            body["source_id"] = source_id
        if job_id:
            body["job_id"] = job_id
        if model_version:
            body["model_version"] = model_version
        body["schema_version"] = schema_version
        body["prompt_version"] = prompt_version
        if options:
            body["options"] = options
        return await self._request("POST", "/v1/extract", tenant_id, json=body)

    async def extract_and_ingest(
        self,
        tenant_id: str,
        content: str,
        content_type: str = "text",
        source_id: str | None = None,
        source_version_id: str | None = None,
        job_id: str | None = None,
        model_version: str | None = None,
        schema_version: str = "1.0",
        prompt_version: str = "entity_extraction_v1",
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {
            "content": content,
            "content_type": content_type,
        }
        if source_id:
            body["source_id"] = source_id
        if source_version_id:
            body["source_version_id"] = source_version_id
        if job_id:
            body["job_id"] = job_id
        if model_version:
            body["model_version"] = model_version
        body["schema_version"] = schema_version
        body["prompt_version"] = prompt_version
        if options:
            body["options"] = options
        return await self._request("POST", "/v1/extract-and-ingest", tenant_id, json=body)