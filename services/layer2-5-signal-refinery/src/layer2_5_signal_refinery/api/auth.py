from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from value_fabric.shared.error_handling.exceptions import AuthenticationError

"""Auth helpers for L2.5 Signal Refinery.

Wraps value_fabric.shared.identity with a graceful fallback for
environments where the shared package is not installed (e.g. isolated tests).
"""

logger = logging.getLogger(__name__)

try:
    from value_fabric.shared.identity.context import (
        RequestContext as _SharedRequestContext,
    )
    from value_fabric.shared.identity.context import (
        get_request_context as _shared_get_request_context,
    )
    from value_fabric.shared.identity.dependencies import (
        require_authenticated,
    )
    _SHARED_IDENTITY_AVAILABLE = True
except ImportError:
    _SharedRequestContext = None  # type: ignore[assignment]
    _shared_get_request_context = None  # type: ignore[assignment]
    _SHARED_IDENTITY_AVAILABLE = False

    def require_authenticated() -> None:
        return None


# Fallback Protocol class. This is the ONLY definition of the name
# `RequestContext` that mypy ever sees at module level, so there is no
# `[no-redef]`. The optional TYPE_CHECKING branch below aliases it to the
# shared class when installed, giving callers the precise shared type.
class RequestContext(Protocol):
    tenant_id: str | None


if TYPE_CHECKING and _SHARED_IDENTITY_AVAILABLE:
    RequestContext = _SharedRequestContext  # type: ignore[misc,no-redef]


# Runtime binding: delegate to the shared implementation when installed.
if _SHARED_IDENTITY_AVAILABLE:
    get_request_context = _shared_get_request_context
else:

    def get_request_context() -> RequestContext | None:
        return None


def get_tenant_id_from_context() -> str:
    """Extract tenant_id from RequestContext. Fail closed if missing."""
    ctx = get_request_context()
    if ctx is not None and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)

    raise AuthenticationError(message="Tenant context required.")
