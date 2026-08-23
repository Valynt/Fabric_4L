from __future__ import annotations

"""Model Registry Client with fail-closed bootstrap semantics.

P2 Risk #14: Model Registry Observability
Registry failure may use an explicitly enabled bootstrap model for local
development or disaster recovery. Merely defining ``FALLBACK_MODEL`` is not
authorization to change providers or models.
"""


import json
import os
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.observability.logging import get_logger

audit_log = get_logger(__name__)


class ModelRegistryClient_get_fallback_statsResult(TypedDictModel):
    fallback_count: Any
    fallback_model: Any
    registry_url: Any
    strict_mode: bool


@dataclass
class ModelSpec:
    """Model specification."""

    id: str
    source: str  # "registry" or explicit "bootstrap"
    version: str | None = None
    metadata: dict | None = None


class RegistryUnavailable(Exception):
    """Raised when model registry is unavailable."""

    pass


class ModelRegistryClient:
    """Client for model registry with observable fallback behavior.

    Registry unavailability fails closed unless ``GATEWAY_BOOTSTRAP_MODE`` is
    explicitly true and ``FALLBACK_MODEL`` names the approved bootstrap model.
    """

    def __init__(
        self,
        registry_url: str | None = None,
        timeout: float | None = None,
        cache_ttl: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize client.

        Args:
            registry_url: URL of the model registry service.
                         Defaults to MODEL_REGISTRY_URL env var.
            timeout: HTTP request timeout in seconds (default 5.0).
            cache_ttl: In-memory TTL cache duration in seconds (default 60.0).
            http_client: Optional injected httpx.AsyncClient for testing/reuse.
        """
        self.registry_url = (
            registry_url or os.getenv("MODEL_REGISTRY_URL", "http://model-registry:8080")
        ).rstrip("/")
        self.timeout = timeout if timeout is not None else float(
            os.getenv("MODEL_REGISTRY_TIMEOUT_SEC", "5.0")
        )
        self.cache_ttl = cache_ttl if cache_ttl is not None else float(
            os.getenv("MODEL_REGISTRY_CACHE_TTL_SEC", "60.0")
        )
        self._http_client = http_client
        self._cache: dict[tuple[str, str | None], tuple[float, ModelSpec]] = {}
        self._fallback_count = 0

    async def _fetch_from_registry(
        self,
        model_id: str,
        tenant_id: str | UUID | None = None,
    ) -> ModelSpec:
        """Fetch model from registry via HTTP.

        Args:
            model_id: The model identifier
            tenant_id: Optional tenant identifier

        Returns:
            ModelSpec from registry

        Raises:
            RegistryUnavailable: If registry cannot be reached or returns an error
        """
        base_url = self.registry_url.rstrip("/")
        if base_url.endswith("/models"):
            url = f"{base_url}/{model_id}"
        elif base_url.endswith("/v1"):
            url = f"{base_url}/models/{model_id}"
        else:
            url = f"{base_url}/models/{model_id}"

        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        tenant_str = str(tenant_id) if tenant_id else None
        if tenant_str:
            headers["X-Tenant-ID"] = tenant_str

        try:
            if self._http_client is not None:
                resp = await self._http_client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if not isinstance(data, dict):
                    raise RegistryUnavailable(
                        f"Registry at {self.registry_url} returned non-object JSON payload: {type(data).__name__}"
                    )
                spec = ModelSpec(
                    id=str(data.get("model_name") or data.get("id") or model_id),
                    source="registry",
                    version=data.get("model_version") or data.get("version"),
                    metadata=data,
                )
                if self.cache_ttl > 0:
                    self._cache[(model_id, tenant_str)] = (
                        time.monotonic() + self.cache_ttl,
                        spec,
                    )
                return spec
            elif resp.status_code == 404:
                raise RegistryUnavailable(
                    f"Model '{model_id}' not found in registry at {self.registry_url} (HTTP 404)"
                )
            else:
                raise RegistryUnavailable(
                    f"Registry at {self.registry_url} returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except (httpx.RequestError, httpx.TimeoutException, json.JSONDecodeError, ValueError, AttributeError) as exc:
            if isinstance(exc, RegistryUnavailable):
                raise
            raise RegistryUnavailable(
                f"Failed to connect to model registry at {self.registry_url}: {exc}"
            ) from exc

    async def get_model(
        self,
        model_id: str,
        tenant_id: str | UUID | None = None,
    ) -> ModelSpec:
        """Get model spec with observable fallback.

        Attempts to fetch from registry first. Bootstrap operation is an
        explicit degraded mode, not an implicit environment-variable fallback.

        Args:
            model_id: The requested model identifier
            tenant_id: Optional tenant identifier

        Returns:
            ModelSpec with source indicating origin

        Raises:
            RegistryUnavailable: If registry is unavailable and explicit
                bootstrap operation is not fully enabled.
        """
        tenant_str = str(tenant_id) if tenant_id else None
        cache_key = (model_id, tenant_str)
        if self.cache_ttl > 0 and cache_key in self._cache:
            expiry, cached_spec = self._cache[cache_key]
            if time.monotonic() < expiry:
                return cached_spec
            del self._cache[cache_key]

        try:
            if tenant_id is not None:
                return await self._fetch_from_registry(model_id, tenant_id=tenant_id)
            return await self._fetch_from_registry(model_id)
        except RegistryUnavailable:
            fallback = os.getenv("FALLBACK_MODEL")
            bootstrap_enabled = os.getenv("GATEWAY_BOOTSTRAP_MODE", "false").lower() == "true"
            if not bootstrap_enabled or not fallback:
                audit_log.error(
                    "model_registry_unavailable_fail_closed",
                    requested_model=model_id,
                    registry_url=self.registry_url,
                    bootstrap_enabled=bootstrap_enabled,
                    action="hard_failure",
                )
                raise

            # Observable degradation
            self._fallback_count += 1
            audit_log.warning(
                "model_registry_fallback_used",
                requested_model=model_id,
                fallback_model=fallback,
                reason="registry_unavailable",
                fallback_count=self._fallback_count,
                action="degraded_mode_activated",
            )

            return ModelSpec(
                id=fallback,
                source="bootstrap",
                metadata={
                    "requested": model_id,
                    "fallback_reason": "registry_unavailable",
                    "degraded": True,
                },
            )

    def get_fallback_stats(self) -> dict:
        """Get statistics on fallback usage.

        Returns:
            Dict with fallback count and configuration
        """
        return ModelRegistryClient_get_fallback_statsResult.model_validate(
            {
                "fallback_count": self._fallback_count,
                "fallback_model": os.getenv("FALLBACK_MODEL"),
                "strict_mode": os.getenv("GATEWAY_BOOTSTRAP_MODE", "false").lower() != "true",
                "registry_url": self.registry_url,
            }
        )
