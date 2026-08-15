"""Build contract-valid authorization snapshots from verified gateway identity."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import AuthDirectory

_ROLE_ALIASES = {
    "read_only": "member",
    "content_admin": "account_admin",
    "super_admin": "platform_admin",
}
_CANONICAL_ROLES = {"member", "analyst", "account_admin", "tenant_admin", "platform_admin"}


def build_authorization_snapshot(
    *, auth: AuthContext, request: Request, directory: AuthDirectory
) -> dict[str, object]:
    """Return authorization facts bound to the authenticated tenant and session."""
    if auth.clerk_org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    tenant = directory.get_tenant_by_clerk_org(auth.clerk_org_id)
    if tenant is None or tenant.status != "active" or tenant.id != auth.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")

    roles = sorted({_ROLE_ALIASES.get(role, role) for role in auth.roles})
    if not roles or any(role not in _CANONICAL_ROLES for role in roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role access denied")

    account_id = request.headers.get("X-Account-ID")
    if account_id:
        # Account authorization needs a verified directory projection. Never widen
        # an unverified account request to tenant scope.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account access denied")

    credential = request.headers.get("Authorization", "")
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    session_discriminator = hashlib.sha256(credential.encode()).hexdigest()
    issued_at = datetime.now(UTC)
    expires_at = datetime.fromtimestamp(auth.exp, UTC)
    if expires_at <= issued_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication expired"
        )

    return {
        "principalId": auth.user_id,
        "sessionDiscriminator": session_discriminator,
        "tenant": {"id": tenant.id, "slug": tenant.slug or tenant.id},
        "accountScope": {"kind": "tenant"},
        "roles": roles,
        "permissions": sorted(auth.permissions),
        "entitlements": [],
        "source": "backend",
        "issuedAt": issued_at.isoformat().replace("+00:00", "Z"),
        "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
    }
