from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer2Client:
    """Internal client to the Layer 2 extraction service."""

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
        extraction_method: str = "llm",
        source_id: str | None = None,
        job_id: str | None = None,
        tenant_id_override: str | None = None,
        model_version: str | None = None,
        schema_version: str = "1.0",
        prompt_version: str = "entity_extraction_v1",
        options: dict[str, Any] | None = None,
        extraction_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract entities and relationships from content."""
        payload = {
            "content": content,
            "content_type": content_type,
            "extraction_method": extraction_method,
        }
        if source_id:
            payload["source_id"] = source_id
        if job_id:
            payload["job_id"] = job_id
        if tenant_id_override:
            payload["tenant_id"] = tenant_id_override
        if model_version:
            payload["model_version"] = model_version
        payload["schema_version"] = schema_version
        payload["prompt_version"] = prompt_version
        if options:
            payload["options"] = options
        if extraction_schema:
            payload["extraction_schema"] = extraction_schema

        return await self._request("POST", "/v1/extract", tenant_id, json=payload)

    async def extract_and_ingest(
        self,
        tenant_id: str,
        content: str,
        content_type: str = "text",
        extraction_method: str = "llm",
        source_id: str | None = None,
        job_id: str | None = None,
        tenant_id_override: str | None = None,
        model_version: str | None = None,
        schema_version: str = "1.0",
        prompt_version: str = "entity_extraction_v1",
        options: dict[str, Any] | None = None,
        extraction_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract and ingest into Layer 3 knowledge graph."""
        payload = {
            "content": content,
            "content_type": content_type,
            "extraction_method": extraction_method,
        }
        if source_id:
            payload["source_id"] = source_id
        if job_id:
            payload["job_id"] = job_id
        if tenant_id_override:
            payload["tenant_id"] = tenant_id_override
        if model_version:
            payload["model_version"] = model_version
        payload["schema_version"] = schema_version
        payload["prompt_version"] = prompt_version
        if options:
            payload["options"] = options
        if extraction_schema:
            payload["extraction_schema"] = extraction_schema

        return await self._request("POST", "/v1/extract-and-ingest", tenant_id, json=payload)

    async def get_job_status(
        self,
        tenant_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Get extraction job status."""
        return await self._request("GET", f"/v1/extractions/{job_id}", tenant_id)