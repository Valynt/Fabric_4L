"""Verify that the API gateway installs central governance middleware.

The platform audit (``audit_protected_routes``) requires any app with
non-public routes to install ``GovernanceMiddleware``. The API gateway was
missing it, causing the shared tenant-enforcement middleware to return 403
because no tenant context had been established.
"""

from __future__ import annotations

from value_fabric.shared.identity.middleware import GovernanceMiddleware


def test_api_gateway_includes_governance_middleware():
    """The API gateway app stack must include GovernanceMiddleware."""
    # Importing app.main triggers the full application factory.
    from app.main import app

    middleware_classes = {middleware.cls for middleware in app.user_middleware}
    assert GovernanceMiddleware in middleware_classes, (
        "API gateway must install GovernanceMiddleware so tenant context is "
        "available before the shared tenant-enforcement middleware runs."
    )
