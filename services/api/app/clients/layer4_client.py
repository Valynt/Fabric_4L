from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer4Client:
    """Internal client to the Layer 4 agentic workflow service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer4_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer4_timeout_seconds
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
            detail = response.text or f"Layer 4 request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def submit_workflow(
        self,
        tenant_id: str,
        workflow_type: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/workflows",
            tenant_id,
            json={"workflow_type": workflow_type, "inputs": inputs},
        )

    async def get_workflow(self, tenant_id: str, workflow_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/workflows/{workflow_id}", tenant_id)

    async def get_workflow_result(
        self, tenant_id: str, workflow_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"/v1/workflows/{workflow_id}/result", tenant_id
        )

    async def generate_narrative(
        self, tenant_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", "/v1/narratives/generate", tenant_id, json=payload
        )

    async def generate_hypotheses(
        self, tenant_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", "/v1/hypotheses/generate", tenant_id, json=payload
        )

    async def run_roi_analysis(
        self, tenant_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", "/v1/analysis/roi", tenant_id, json=payload
        )
