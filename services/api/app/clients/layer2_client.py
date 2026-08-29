from __future__ import annotations

import os

from fastapi import HTTPException
from value_fabric.shared.clients.layer2 import (
    EXTRACT_AND_INGEST_PATH,
    EXTRACT_PATH,
    EXTRACT_STATUS_PATH,
    Layer2Transport,
    Layer2TransportError,
)
from value_fabric.shared.models import JSONDict

from app.core.config import get_settings


class Layer2Client:
    """Gateway adapter to the Layer 2 extraction service.

    Endpoint literals and transport (URL construction, tenant/service-auth
    headers, serialization, timeout, HTTP boundary, retry is a consumer
    concern) are centralized in ``value_fabric.shared.clients.layer2``.
    This adapter keeps the gateway's public surface and error semantics:
    any upstream failure (4xx/5xx) is translated to ``HTTPException(502)``
    for the frontend.

    Payloads follow the canonical ``ExtractRequest`` contract
    (``content_id``, ``source_url``, ``markdown_content``, optional
    ``extraction_config``).
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer2_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer2_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")
        self._transport = Layer2Transport(
            base_url=self.base_url,
            timeout=self.timeout,
            service_secret=self.service_secret,
        )

    async def _request(
        self,
        method: str,
        path: str,
        tenant_id: str,
        json: JSONDict | None = None,
    ) -> JSONDict:
        try:
            response = await self._transport.request(
                method,
                path,
                tenant_id=tenant_id,
                json=json,
            )
        except Layer2TransportError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return response.json()

    async def extract(
        self,
        tenant_id: str,
        content_id: str = "",
        source_url: str = "",
        markdown_content: str = "",
        extraction_config: JSONDict | None = None,
    ) -> JSONDict:
        """Start an extraction job (extraction only)."""
        payload: JSONDict = {
            "content_id": content_id,
            "source_url": source_url,
            "markdown_content": markdown_content,
        }
        if extraction_config is not None:
            payload["extraction_config"] = extraction_config
        return await self._request("POST", EXTRACT_PATH, tenant_id, payload)

    async def extract_and_ingest(
        self,
        tenant_id: str,
        content_id: str = "",
        source_url: str = "",
        markdown_content: str = "",
        extraction_config: JSONDict | None = None,
    ) -> JSONDict:
        """Extract and ingest into Layer 3 knowledge graph."""
        payload: JSONDict = {
            "content_id": content_id,
            "source_url": source_url,
            "markdown_content": markdown_content,
        }
        if extraction_config is not None:
            payload["extraction_config"] = extraction_config
        return await self._request("POST", EXTRACT_AND_INGEST_PATH, tenant_id, payload)

    async def get_job_status(self, tenant_id: str, job_id: str) -> JSONDict:
        """Get extraction job status."""
        return await self._request(
            "GET", EXTRACT_STATUS_PATH.format(job_id=job_id), tenant_id
        )
