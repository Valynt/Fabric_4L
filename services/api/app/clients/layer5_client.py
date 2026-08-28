from __future__ import annotations

import os

from fastapi import HTTPException
from value_fabric.shared.clients.layer5 import (
    MATURITY_LADDER_PATH,
    TRUTH_ITEM_PATH,
    TRUTH_VALIDATE_PATH,
    TRUTHS_FRESHNESS_SUMMARY_PATH,
    TRUTHS_PATH,
    TRUTHS_SYNC_KG_PATH,
    Layer5Transport,
    Layer5TransportError,
)
from value_fabric.shared.models import JSONDict

from app.core.config import get_settings


class Layer5Client:
    """Gateway adapter to the Layer 5 Ground Truth service.

    Endpoint literals and transport (URL construction, tenant/service-auth
    headers, serialization, timeout, HTTP boundary) are centralized in
    ``value_fabric.shared.clients.layer5``.  This adapter keeps the gateway's
    public surface and error semantics: any upstream failure (4xx/5xx) is
    translated to ``HTTPException(502)`` for the frontend.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer5_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer5_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")
        self._transport = Layer5Transport(
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
        params: dict[str, str] | None = None,
    ) -> JSONDict:
        try:
            response = await self._transport.request(
                method,
                path,
                tenant_id=tenant_id,
                json=json,
                params=params,
            )
        except Layer5TransportError as exc:
            # Do not surface raw exception text: the secure error envelope gate
            # forbids leaking str(exc) into HTTP responses.  Rebuild the safe
            # detail from the transport's structured fields instead.
            detail = exc.response_text or f"Layer 5 request failed ({exc.status_code})"
            raise HTTPException(status_code=502, detail=detail) from exc
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
        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        if status is not None:
            params["status"] = status
        if claim_type is not None:
            params["claim_type"] = claim_type
        return await self._request("GET", TRUTHS_PATH, tenant_id, params=params)

    async def get_truth(self, tenant_id: str, truth_id: str) -> JSONDict:
        """Get a single TruthObject by ID."""
        return await self._request("GET", TRUTH_ITEM_PATH.format(truth_id=truth_id), tenant_id)

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
        return await self._request("POST", TRUTHS_PATH, tenant_id, payload)

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
        return await self._request(
            "POST", TRUTH_VALIDATE_PATH.format(truth_id=truth_id), tenant_id, payload
        )

    async def sync_kg(self, tenant_id: str) -> JSONDict:
        """Sync validated TruthObjects to Layer 3 knowledge graph."""
        return await self._request("POST", TRUTHS_SYNC_KG_PATH, tenant_id)

    async def get_freshness_summary(self, tenant_id: str) -> JSONDict:
        """Get freshness summary of TruthObjects."""
        return await self._request("GET", TRUTHS_FRESHNESS_SUMMARY_PATH, tenant_id)

    async def get_maturity_ladder(self, tenant_id: str) -> JSONDict:
        """Get maturity ladder reference."""
        return await self._request("GET", MATURITY_LADDER_PATH, tenant_id)
