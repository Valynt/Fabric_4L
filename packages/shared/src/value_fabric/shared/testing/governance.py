"""Test-only helpers for the shared governance middleware.

These utilities are intentionally kept out of production code paths. They make
it possible to run route-level tests without requiring a live Redis instance
for the tenant kill switch while preserving the production fail-closed behavior.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI
from starlette.middleware import Middleware

from value_fabric.shared.identity.middleware import GovernanceMiddleware


async def _default_active_tenant_status_resolver(_tenant_id: str) -> str:
    """Return a known-active status for every tenant.

    This short-circuits the Redis-backed kill switch so that tests exercise
    route business logic rather than infrastructure availability.
    """
    return "active"


TenantStatusResolver = Callable[[str], Awaitable[str]]


def patch_governance_middleware_for_tests(
    app: FastAPI,
    tenant_status_resolver: TenantStatusResolver | None = None,
) -> None:
    """Replace the app's GovernanceMiddleware instance with a test-aware copy.

    The replacement keeps all original middleware options (rate limiter, API key
    resolver, etc.) and injects a ``tenant_status_resolver`` that returns
    ``"active"`` for all tenants.  This prevents the kill switch from returning
    HTTP 503 when Redis is not running in the test environment.

    Args:
        app: The FastAPI application whose middleware stack contains
            ``GovernanceMiddleware``.
        tenant_status_resolver: Optional async callable ``(tenant_id: str) -> str``.
            Defaults to a resolver that always returns ``"active"``.

    Raises:
        RuntimeError: If ``GovernanceMiddleware`` is not found in the app's
            middleware stack.  This is a test-authoring signal, not a runtime
            failure.
    """
    if tenant_status_resolver is None:
        tenant_status_resolver = _default_active_tenant_status_resolver

    for index, middleware in enumerate(app.user_middleware):
        if getattr(middleware, "cls", None) is GovernanceMiddleware:
            kwargs: dict[str, Any] = dict(getattr(middleware, "kwargs", {}))
            kwargs["tenant_status_resolver"] = tenant_status_resolver
            app.user_middleware[index] = Middleware(
                GovernanceMiddleware,
                *getattr(middleware, "args", ()),
                **kwargs,
            )
            return

    raise RuntimeError(
        "GovernanceMiddleware was not found in app.user_middleware; "
        "cannot inject test tenant status resolver."
    )
