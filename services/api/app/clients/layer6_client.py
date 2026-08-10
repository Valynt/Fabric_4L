from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer6Client:
    """Internal client to the Layer 6 benchmarks service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer6_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer6_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str) -> dict[str, str]:
        return {
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
            "Content-Type": "application/json",
        }

    async def list_datasets(self, tenant_id: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/v1/benchmarks/datasets"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers(tenant_id))
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Layer 6 benchmarks unavailable")
        return response.json()

    async def compare(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/benchmarks/compare"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers(tenant_id))
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Layer 6 comparison failed")
        return response.json()
