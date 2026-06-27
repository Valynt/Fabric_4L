from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException


class InternalAPIClient:
    """Calls the gateway's own internal routes for persistence/calculation operations.

    In production this should target the gateway service address
    (e.g. ``http://api:8000``). In local development it defaults to
    ``http://localhost:8000``.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or os.environ.get("INTERNAL_API_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.timeout = timeout or float(os.environ.get("INTERNAL_API_TIMEOUT_SECONDS", "10"))
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
            detail = response.text or f"Internal API request failed ({response.status_code})"
            raise HTTPException(status_code=502, detail=detail)
        return response.json()

    async def create_driver(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/drivers/generate", tenant_id, json=payload
        )

    async def get_value_tree(self, tenant_id: str, account_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/v1/accounts/{account_id}/value-tree", tenant_id
        )

    async def create_scenario(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/scenarios", tenant_id, json=payload
        )

    async def calculate_roi(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/roi/calculate", tenant_id, json=payload
        )

    async def create_value_case(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/value-case/generate", tenant_id, json=payload
        )

    async def patch_realization_actuals(
        self,
        tenant_id: str,
        account_id: str,
        plan_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/v1/accounts/{account_id}/realization-plans/{plan_id}/actuals",
            tenant_id,
            json=payload,
        )

    async def get_realization_variance(
        self, tenant_id: str, account_id: str, plan_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/accounts/{account_id}/realization-plans/{plan_id}/variance",
            tenant_id,
        )

    async def create_hypothesis(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/hypotheses/generate", tenant_id, json=payload
        )

    async def extract_signal(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/signals/extract", tenant_id, json=payload
        )

    async def create_review(
        self, tenant_id: str, account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/accounts/{account_id}/reviews", tenant_id, json=payload
        )
