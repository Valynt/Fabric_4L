"""Behavior-only mixins for the Layer 3 APIKey model.

These mixins contain only computed properties and helper methods that depend on
fields defined on the concrete ``APIKey`` class. Fields remain on ``APIKey`` so
Pydantic validation, serialization, and the public API contract stay unchanged.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.auth.api_keys import Permission


class _APIKeyExpirationProtocol(Protocol):
    expires_at: datetime | None


class APIKeyExpirationMixin:
    """Mixin exposing API key expiration checks."""

    def is_expired(self: _APIKeyExpirationProtocol) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class _APIKeyIPValidationProtocol(Protocol):
    allowed_ips: list[str] | None


class APIKeyIPValidationMixin:
    """Mixin exposing API key IP-address validation."""

    def is_valid_ip(self: _APIKeyIPValidationProtocol, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.allowed_ips:
            return True
        return ip_address in self.allowed_ips


class _APIKeyPermissionProtocol(Protocol):
    permissions: set[Any]


class APIKeyPermissionMixin:
    """Mixin exposing API key permission checks."""

    def has_permission(
        self: _APIKeyPermissionProtocol, permission: Permission
    ) -> bool:
        """Check if key has specific permission."""
        return permission in self.permissions


class _APIKeyUsageProtocol(Protocol):
    last_used_at: datetime | None
    usage_count: int


class APIKeyUsageMixin:
    """Mixin exposing API key usage tracking updates."""

    def update_usage(self: _APIKeyUsageProtocol) -> None:
        """Update usage statistics."""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
