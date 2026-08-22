from __future__ import annotations

"""Model Registry Client with fail-closed bootstrap semantics.

P2 Risk #14: Model Registry Observability
Registry failure may use an explicitly enabled bootstrap model for local
development or disaster recovery. Merely defining ``FALLBACK_MODEL`` is not
authorization to change providers or models.
"""


import os
from dataclasses import dataclass
from typing import Any

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

    def __init__(self, registry_url: str | None = None) -> None:
        """Initialize client.

        Args:
            registry_url: URL of the model registry service.
                         Defaults to MODEL_REGISTRY_URL env var.
        """
        self.registry_url = registry_url or os.getenv(
            "MODEL_REGISTRY_URL", "http://model-registry:8080"
        )
        self._fallback_count = 0

    async def _fetch_from_registry(self, model_id: str) -> ModelSpec:
        """Fetch model from registry.

        Args:
            model_id: The model identifier

        Returns:
            ModelSpec from registry

        Raises:
            RegistryUnavailable: If registry cannot be reached
        """
        # Implementation would make actual HTTP call to registry
        # For now, raise to demonstrate fallback path
        raise RegistryUnavailable(f"Registry at {self.registry_url} unavailable")

    async def get_model(self, model_id: str) -> ModelSpec:
        """Get model spec with observable fallback.

        Attempts to fetch from registry first. Bootstrap operation is an
        explicit degraded mode, not an implicit environment-variable fallback.

        Args:
            model_id: The requested model identifier

        Returns:
            ModelSpec with source indicating origin

        Raises:
            RegistryUnavailable: If registry is unavailable and explicit
                bootstrap operation is not fully enabled.
        """
        try:
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
