from __future__ import annotations

import logging
from typing import Protocol

from value_fabric.shared.error_handling.exceptions import AuthenticationError

"""Auth helpers for L2.5 Signal Refinery.

Wraps value_fabric.shared.identity with a graceful fallback for
environments where the shared package is not installed (e.g. isolated tests).
"""

logger = logging.getLogger(__name__)

try:  # noqa: E402
    from value_fabric.shared.identity.context import get_request_context  # noqa: E402
    from value_fabric.shared.identity.dependencies import require_authenticated  # noqa: E402

    SHARED_IDENTITY_AVAILABLE = True
except ImportError:
    SHARED_IDENTITY_AVAILABLE = False

    # Fallback types when shared.identity is not available
    class RequestContext(Protocol):
        tenant_id: str | None

    def get_request_context() -> RequestContext | None:
        return None

    def require_authenticated() -> None:
        return None


def get_tenant_id_from_context() -> str:
    """Extract tenant_id from RequestContext. Fail closed if missing."""
    ctx = get_request_context()
    if ctx is not None and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)

    raise AuthenticationError(message="Tenant context required.")
