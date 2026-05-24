"""Fabric4L internal AuthContext envelope (Phase 1 Clerk integration).

This subpackage owns the canonical cross-service identity contract:

- :class:`AuthContext`     — frozen pydantic model carried inside the envelope.
- :func:`sign_envelope`    — gateway-only, mints a short-lived Ed25519 JWT.
- :func:`verify_envelope`  — used by L1–L6 to verify ``X-Fabric-Auth``.
- :class:`FabricAuthMiddleware` — FastAPI middleware that enforces the envelope.
- :func:`apply_tenant_rls` — sets ``app.tenant_id`` on a SQLAlchemy session.

Phase 1 invariants:
- L1–L6 must NEVER verify a raw Clerk JWT. The envelope is the only trust boundary.
- The envelope tenant_id wins over any header/URL slug. ``X-Tenant-ID`` is
  observability-only and may only match (never override) the envelope tenant.
"""
from .context import AuthContext
from .errors import (
    FabricAuthError,
    EnvelopeMissingError,
    EnvelopeInvalidError,
    EnvelopeExpiredError,
    TenantMismatchError,
)
from .signer import (
    SigningKey,
    VerificationKey,
    KeySet,
    sign_envelope,
    verify_envelope,
)
from .fastapi_setup import register_fabric_auth_from_env
from .middleware import FabricAuthMiddleware, get_auth_context, require_auth_context
from .rls import apply_tenant_rls

__all__ = [
    "AuthContext",
    "FabricAuthError",
    "EnvelopeMissingError",
    "EnvelopeInvalidError",
    "EnvelopeExpiredError",
    "TenantMismatchError",
    "SigningKey",
    "VerificationKey",
    "KeySet",
    "sign_envelope",
    "verify_envelope",
    "FabricAuthMiddleware",
    "get_auth_context",
    "require_auth_context",
    "apply_tenant_rls",
    "register_fabric_auth_from_env",
]
