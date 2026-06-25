"""Pydantic schemas for admin/health-related API operations."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ...shared.models import ProxyRotationStrategy


class ComponentHealth(BaseModel):
    """Component health status."""

    status: str
    latency_ms: int | None = None
    message: str | None = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime
    components: dict[str, ComponentHealth]
    metrics: dict[str, int | None | dict[str, Any]]


class CreateProxyPoolRequest(BaseModel):
    """Request to create a proxy pool."""

    name: str
    proxies: list[dict[str, Any]]
    rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN


class ProxyPoolResponse(BaseModel):
    """Proxy pool response."""

    id: UUID
    name: str
    proxy_count: int
    rotation_strategy: str
    created_at: datetime
