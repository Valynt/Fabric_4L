from __future__ import annotations

"""Model Registry Client with observability for fallback scenarios.

P2 Risk #14: Model Registry Observability
Provides audit logging for registry fallback scenarios to ensure
degraded mode operations are visible and traceable.
"""


import os
from dataclasses import dataclass
from typing import Any

from value_fabric.shared.audit import audit_log
from value_fabric.shared.models.typed_dict import TypedDictModel


class ModelRegistryClient_get_fallback_statsResult(TypedDictModel):
    fallback_count: Any
    fallback_model: Any
    registry_url: Any
    strict_mode: bool


@dataclass
class ModelSpec:
    """Model specification."""
    id: str
    source: str  # "registry" or "env_fallback"
    version: str | None = None
    metadata: dict | None = None


class RegistryUnavailable(Exception):
    """Raised when model registry is unavailable."""
    pass


class ModelRegistryClient:
    """Client for model registry with observable fallback behavior.

    When registry is unavailable, falls back to environment variables
    but logs audit events for observability.
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

        Attempts to fetch from registry first. If unavailable and
        FALLBACK_MODEL is configured, returns fallback with audit logging.

        Args:
            model_id: The requested model identifier

        Returns:
            ModelSpec with source indicating origin

        Raises:
            RegistryUnavailable: If registry unavailable and no fallback
            RuntimeError: If STRICT_MODE=true and fallback would be used
        """
        try:
            return await self._fetch_from_registry(model_id)
        except RegistryUnavailable:
            fallback = os.getenv("FALLBACK_MODEL")
            if not fallback:
                # No fallback configured - hard fail
                audit_log.error(
                    "model_registry_unavailable_no_fallback",
                    requested_model=model_id,
                    registry_url=self.registry_url,
                    action="hard_failure"
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
                action="degraded_mode_activated"
            )

            if os.getenv("STRICT_MODE") == "true":
                audit_log.error(
                    "model_registry_fallback_blocked",
                    requested_model=model_id,
                    fallback_model=fallback,
                    reason="STRICT_MODE_enabled",
                    action="blocked_degraded_mode"
                )
                raise RuntimeError(
                    f"Registry fallback prohibited in STRICT_MODE. "
                    f"Requested: {model_id}, Fallback: {fallback}"
                )

            return ModelSpec(
                id=fallback,
                source="env_fallback",
                metadata={"requested": model_id, "fallback_reason": "registry_unavailable"}
            )

    def get_fallback_stats(self) -> dict:
        """Get statistics on fallback usage.

        Returns:
            Dict with fallback count and configuration
        """
        return ModelRegistryClient_get_fallback_statsResult.model_validate({
            "fallback_count": self._fallback_count,
            "fallback_model": os.getenv("FALLBACK_MODEL"),
            "strict_mode": os.getenv("STRICT_MODE") == "true",
            "registry_url": self.registry_url,
        })
