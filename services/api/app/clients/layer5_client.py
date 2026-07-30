from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
from fastapi import HTTPException

from app.core.config import get_settings

if TYPE_CHECKING:
    pass

JSONDict = dict[str, object]


class Layer5Client:
    """Internal client to the Layer 5 Ground Truth service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer5_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer5_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str) -> JSONDict:
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
        params: JSONDict | None = None,
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
    ) -> JSONDict:
        """List TruthObjects with optional filters."""
        params: JSONDict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if claim_type is not None:
            params["claim_type"] = claim_type
        return await self._request("GET", "/api/v1/truths", tenant_id, params=params)

    async def get_truth(self, tenant_id: str, truth_id: str) -> JSONDict:
        """Get a single TruthObject by ID."""
        return await self._request("GET", f"/api/v1/truths/{truth_id}", tenant_id)

    async def submit_truth(
        self,
        tenant_id: str,
        claim: str = "",
        claim_type: str = "other",
        confidence: float = 0.0,
        value: JSONDict | None = None,
        applies_to: JSONDict | None = None,
        sources: list[JSONDict] | None = None,
        extraction_job_id: str | None = None,
        extraction_model: str | None = None,
        raw_extraction_data: JSONDict | None = None,
    ) -> JSONDict:
        """Submit a new TruthObject."""
        payload: JSONDict = {
            "claim": claim,
            "claim_type": claim_type,
            "confidence": confidence,
        }
        if value is not None:
            payload["value"] = value
        if applies_to is not None:
            payload["applies_to"] = applies_to
        if sources is not None:
            payload["sources"] = sources
        if extraction_job_id is not None:
            payload["extraction_job_id"] = extraction_job_id
        if extraction_model is not None:
            payload["extraction_model"] = extraction_model
        if raw_extraction_data is not None:
            payload["raw_extraction_data"] = raw_extraction_data
        return await self._request("POST", "/api/v1/truths", tenant_id, payload)

    async def validate_truth(
        self,
        tenant_id: str,
        truth_id: str,
        action: str = "",
        actor: str = "",
        actor_type: str = "system",
        notes: str | None = None,
    ) -> JSONDict:
        """Validate or transition a TruthObject."""
        payload: JSONDict = {"action": action, "actor": actor, "actor_type": actor_type}
        if notes is not None:
            payload["notes"] = notes
        return await self._request("POST", f"/api/v1/truths/{truth_id}/validate", tenant_id, payload)

    async def sync_kg(self, tenant_id: str) -> JSONDict:
        """Sync validated TruthObjects to Layer 3 knowledge graph."""
        return await self._request("POST", "/api/v1/truths/sync-kg", tenant_id)

    async def get_freshness_summary(self, tenant_id: str) -> JSONDict:
        """Get freshness summary of TruthObjects."""
        return await self._request("GET", "/api/v1/truths/freshness-summary", tenant_id)

    async def get_maturity_ladder(self, tenant_id: str) -> JSONDict:
        """Get maturity ladder reference."""
        return await self._request("GET", "/api/v1/maturity-ladder", tenant_id)
