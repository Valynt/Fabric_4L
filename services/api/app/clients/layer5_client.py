from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


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
        """List TruthObjects with optional filters."""
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
        """Get a single TruthObject by ID."""
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
        extraction_job_id: str | None = None,
        extraction_model: str | None = None,
        raw_extraction_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a new TruthObject."""
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
        if extraction_job_id:
            body["extraction_job_id"] = extraction_job_id
        if extraction_model:
            body["extraction_model"] = extraction_model
        if raw_extraction_data:
            body["raw_extraction_data"] = raw_extraction_data
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
        """Validate or transition a TruthObject."""
        payload = {
            "action": action,
            "actor": actor,
            "actor_type": actor_type,
        }
        if notes:
            payload["notes"] = notes
        return await self._request("POST", f"/api/v1/truths/{truth_id}/validate", tenant_id, json=payload)

    async def sync_kg(self, tenant_id: str) -> dict[str, Any]:
        """Trigger sync of validated TruthObjects to Layer 3 knowledge graph."""
        return await self._request("POST", "/api/v1/truths/sync-kg", tenant_id)

    async def get_freshness_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get freshness summary of TruthObjects."""
        return await self._request("GET", "/api/v1/truths/freshness-summary", tenant_id)

    async def get_maturity_ladder(self, tenant_id: str) -> dict[str, Any]:
        """Get maturity ladder reference."""
        return await self._request("GET", "/api/v1/maturity-ladder", tenant_id)