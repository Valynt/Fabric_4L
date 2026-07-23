"""Route audit for protected routes.

Verifies that any app exposing non-public routes has the central
``GovernanceMiddleware`` installed.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute

from .constants import _is_external_auth_bootstrap_path


def audit_protected_routes(app: FastAPI) -> None:
    """Fail closed if central auth middleware is missing for protected routes.

    Authentication and tenant-context enforcement are intentionally centralized
    in :class:`GovernanceMiddleware`; route handlers no longer need to repeat
    ``Depends(require_authenticated)`` solely to become private. This startup
    audit therefore verifies that any app exposing non-public routes has the
    central middleware installed. Explicit route dependencies remain valid for
    RBAC or endpoint-specific checks, but they are not the platform auth gate.
    """
    # Import here to avoid circular import at module load time.
    from .middleware import GovernanceMiddleware

    protected_routes: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _is_external_auth_bootstrap_path(route.path):
            continue
        methods = ",".join(sorted(route.methods or []))
        protected_routes.append(f"{methods} {route.path}")

    if not protected_routes:
        return

    middleware_types = [middleware.cls for middleware in app.user_middleware]
    if GovernanceMiddleware in middleware_types:
        return

    missing = "\n - ".join(sorted(protected_routes))
    raise RuntimeError(
        "Auth route audit failed. Apps with non-public routes must install "
        "GovernanceMiddleware for central auth and tenant-context enforcement."
        f"\n - {missing}"
    )
