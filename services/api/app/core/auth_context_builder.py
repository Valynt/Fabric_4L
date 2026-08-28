"""Builds a verified Fabric4L :class:`AuthContext` from Clerk claims.

This is the only place in the codebase that ties Clerk identifiers to
internal Fabric4L IDs. The result is the source of truth for every
downstream authorization decision (tenant scope, RBAC, RLS).
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.identity.fabric_auth import AuthContext

from .auth_directory import AuthDirectory
from .clerk_config import InternalEnvelopeSettings
from .clerk_verifier import ClerkClaims

logger = logging.getLogger(__name__)


class TenantResolutionError(Exception):
    """Raised when Clerk claims cannot be resolved to a Fabric4L tenant."""

    code: str = ErrorCode.AUTH_TENANT_UNRESOLVED
    http_status: int = 403
    public_message: str = "You do not have access to this resource."

    def __init__(self, *, log_detail: str | None = None) -> None:
        super().__init__(log_detail or self.public_message)
        self.log_detail = log_detail


class MembershipNotActiveError(TenantResolutionError):
    code = ErrorCode.AUTH_MEMBERSHIP_INACTIVE


class UserNotProvisionedError(TenantResolutionError):
    code = ErrorCode.AUTH_USER_UNPROVISIONED


def normalize_clerk_role(role: str | None) -> str | None:
    """Map Clerk organization roles to Fabric RBAC role names."""
    if role is None:
        return None
    normalized = role.strip().lower()
    role_map = {
        "admin": "tenant_admin",
        "org:admin": "tenant_admin",
        "basic_member": "analyst",
        "org:member": "analyst",
        "member": "analyst",
        "guest_member": "read_only",
        "org:guest": "read_only",
        "guest": "read_only",
    }
    return role_map.get(normalized, normalized)


def build_auth_context(
    *,
    claims: ClerkClaims,
    directory: AuthDirectory,
    envelope_settings: InternalEnvelopeSettings,
    request_id: str | None = None,
    now: int | None = None,
) -> AuthContext:
    """Translate verified Clerk claims into a Fabric4L :class:`AuthContext`.

    Raises:
        UserNotProvisionedError: Clerk user has no Fabric4L user record.
            Webhook backfill should have created one; missing means the
            webhook is misconfigured or the event hasn't replicated yet.
        TenantResolutionError: Clerk org cannot be mapped to a tenant.
        MembershipNotActiveError: User has no active membership in the tenant.
    """
    user = directory.get_user_by_clerk(claims.sub)
    if user is None or user.status != "active":
        raise UserNotProvisionedError(
            log_detail=f"no active Fabric4L user for clerk_user_id={claims.sub!r}"
        )

    if claims.org_id is None:
        raise TenantResolutionError(
            log_detail=f"clerk token for {claims.sub!r} has no active org_id"
        )

    tenant = directory.get_tenant_by_clerk_org(claims.org_id)
    if tenant is None or tenant.status != "active":
        raise TenantResolutionError(
            log_detail=f"no active tenant for clerk_org_id={claims.org_id!r}"
        )

    membership = directory.get_active_membership(
        clerk_org_id=claims.org_id, clerk_user_id=claims.sub
    )
    if membership is None:
        raise MembershipNotActiveError(
            log_detail=(
                f"no active membership clerk_user={claims.sub!r} "
                f"clerk_org={claims.org_id!r}"
            )
        )

    iat = now if now is not None else int(datetime.now(UTC).timestamp())
    exp = iat + envelope_settings.envelope_ttl_seconds
    rid = request_id or f"req_{uuid.uuid4().hex[:16]}"

    if envelope_settings.signing_key is None:
        msg = "envelope_settings.signing_key must be configured at the gateway"
        raise RuntimeError(msg)

    normalized_roles = {
        role
        for role in (
            normalize_clerk_role(membership.role),
            normalize_clerk_role(claims.org_role),
        )
        if role
    }

    return AuthContext(
        clerk_user_id=claims.sub,
        clerk_org_id=claims.org_id,
        user_id=user.id,
        tenant_id=tenant.id,
        roles=frozenset(normalized_roles),
        permissions=frozenset(claims.org_permissions),
        request_id=rid,
        iat=iat,
        exp=exp,
        nbf=iat,
        iss=envelope_settings.issuer,
        aud=envelope_settings.audience,
        kid=envelope_settings.signing_key.kid,
    )
