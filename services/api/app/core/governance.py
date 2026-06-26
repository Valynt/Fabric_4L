from __future__ import annotations

from fastapi import FastAPI
from value_fabric.shared.identity.middleware import GovernanceMiddleware, audit_protected_routes

from app.core.api_key_auth import resolve_api_key
from app.core.config import get_settings


async def _dev_tenant_status_resolver(tenant_id: str) -> str | None:
    """Return active in non-production environments so tests run without Redis.

    In production-like environments this returns ``None`` so the shared
    Redis-backed kill switch remains authoritative.
    """
    if get_settings().is_production_like:
        return None
    return "active"


def add_gateway_governance_middleware(app: FastAPI, *, rate_limiter=None) -> None:
    """Install GovernanceMiddleware with gateway API-key resolution."""
    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=resolve_api_key,
        rate_limiter=rate_limiter,
        tenant_status_resolver=_dev_tenant_status_resolver,
    )

    @app.on_event("startup")
    async def _audit_auth_routes() -> None:
        audit_protected_routes(app)
