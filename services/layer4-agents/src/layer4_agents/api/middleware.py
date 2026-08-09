from __future__ import annotations

"""Middleware composition for Layer 4 API."""


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.fastapi_framework.middleware import resolve_cors_policy
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.security import SecurityConfig, add_security_middleware

from ..database import db_session_for_context
from ..metrics import get_metrics
from ..tenants import get_tenant_settings, lookup_api_key_by_hash


def on_rate_limit_hit(tenant_id: str, scope: str):
    metrics = get_metrics()
    if metrics:
        metrics.increment_rate_limit_hit(tenant_id, scope)


async def _tenant_settings_lookup(tenant_id) -> dict | None:
    from value_fabric.shared.identity.context import RequestContext
    if tenant_id is None:
        return None
    context = RequestContext(tenant_id=tenant_id)
    async with db_session_for_context(context) as db:
        return await get_tenant_settings(db, tenant_id)


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=lookup_api_key_by_hash,
        rate_limiter=getattr(app.state, "rate_limiter", None),
        on_rate_limit_hit=on_rate_limit_hit,
        tenant_settings_resolver=_tenant_settings_lookup,
    )

    security_config = SecurityConfig.from_env(
        skip_validation_paths=frozenset({"/health", "/metrics"}),
        strict_mode=True,
    )
    add_security_middleware(app, config=security_config)
    app.add_middleware(CORSMiddleware, **resolve_cors_policy().as_kwargs())
    register_exception_handlers(app)
