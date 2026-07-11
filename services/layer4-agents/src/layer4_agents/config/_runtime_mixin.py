"""Runtime/environment-related behavior for Layer 4 Settings.

This mixin contains computed properties and environment helpers that depend on
runtime fields defined on the concrete Settings class. Fields remain on
Settings so env-var loading and validation stay centralized.
"""
from __future__ import annotations

from typing import Protocol


class _RuntimeSettingsProtocol(Protocol):
    environment: str
    cors_origins: str


class RuntimeSettingsMixin:
    """Mixin exposing runtime and environment helpers."""

    @property
    def is_production(self: _RuntimeSettingsProtocol) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self: _RuntimeSettingsProtocol) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def cors_origins_list(self: _RuntimeSettingsProtocol) -> list[str]:
        """Get CORS origins as a list.

        Returns explicit origins when configured. Falls back to wildcard only
        in development; all other environments return an empty list (the
        CORS validator on Settings will have already raised for production).
        """
        if not self.cors_origins:
            return ["*"] if self.is_development else []
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Wildcard is only permitted in development.
        if "*" in origins and not self.is_development:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' outside of development. "
                "Specify exact allowed origins."
            )
        return origins
