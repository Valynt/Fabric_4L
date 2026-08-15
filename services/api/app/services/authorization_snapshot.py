"""Atomically issue backend-authoritative browser authorization snapshots."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import (
    AuthDirectory,
    DirectoryMembership,
    DirectoryTenant,
    DirectoryUser,
)

MAX_SNAPSHOT_TTL_SECONDS = 300
_ACCOUNT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class CanonicalAuthorizationRole(StrEnum):
    TENANT_ADMIN = "tenant_admin"
    CONTENT_ADMIN = "content_admin"
    ANALYST = "analyst"
    READ_ONLY = "read_only"


ROLE_PERMISSIONS: dict[CanonicalAuthorizationRole, tuple[str, ...]] = {
    CanonicalAuthorizationRole.TENANT_ADMIN: (
        "*",
        "tier:admin:access",
        "tier:advanced:access",
        "tier:standard:access",
    ),
    CanonicalAuthorizationRole.CONTENT_ADMIN: (
        "content:read",
        "content:write",
        "tier:advanced:access",
        "tier:standard:access",
    ),
    CanonicalAuthorizationRole.ANALYST: (
        "account:read",
        "intelligence:read",
        "tier:standard:access",
    ),
    CanonicalAuthorizationRole.READ_ONLY: ("account:read", "tier:standard:access"),
}


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda value: "".join(
            [value.split("_")[0], *[part.title() for part in value.split("_")[1:]]]
        ),
        populate_by_name=True,
    )


class SnapshotIdentity(_CamelModel):
    clerk_user_id: str
    fabric_user_id: str
    session_discriminator: str


class SnapshotTenant(_CamelModel):
    fabric_tenant_id: str
    clerk_organization_id: str
    tenant_slug: str | None
    membership_id: str
    membership_status: Literal["active"]


class SnapshotAccountScope(_CamelModel):
    scope_type: Literal["tenant", "account"]
    account_id: str | None


class AuthorizationSnapshot(_CamelModel):
    schema_version: Literal["1"] = "1"
    source: Literal["backend"] = "backend"
    identity: SnapshotIdentity
    tenant: SnapshotTenant
    account_scope: SnapshotAccountScope
    roles: list[CanonicalAuthorizationRole]
    permissions: list[str]
    entitlements: list[str]
    issued_at: str
    expires_at: str


def _deny_account(request_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "account_scope_denied",
            "message": "The requested account scope is not authorized.",
            "request_id": request_id,
        },
        headers={"Cache-Control": "private, no-store"},
    )


class AuthorizationSnapshotService:
    def __init__(self, directory: AuthDirectory) -> None:
        self._directory = directory

    def issue(
        self,
        *,
        auth: AuthContext,
        verified_claims: dict[str, object],
        account_id: str | None,
    ) -> AuthorizationSnapshot:
        sid = verified_claims.get("sid")
        token_exp = verified_claims.get("exp")
        if not isinstance(sid, str) or not sid.strip() or not isinstance(token_exp, int):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "auth.session_invalid",
                    "message": "Authentication required.",
                    "request_id": auth.request_id,
                },
            )
        normalized_account = account_id.strip() if account_id is not None else None
        if normalized_account is not None and not _ACCOUNT_ID.fullmatch(normalized_account):
            raise _deny_account(auth.request_id)
        if auth.clerk_org_id is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "auth.tenant_unresolved",
                    "message": "You do not have access to this resource.",
                    "request_id": auth.request_id,
                },
            )

        projection = self._directory.read_authorization_projection(
            clerk_org_id=auth.clerk_org_id,
            clerk_user_id=auth.clerk_user_id,
            account_id=normalized_account,
        )
        if projection is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "auth.membership_inactive",
                    "message": "You do not have access to this resource.",
                    "request_id": auth.request_id,
                },
            )
        user = projection["user"]
        tenant = projection["tenant"]
        membership = projection["membership"]
        assert (
            isinstance(user, DirectoryUser)
            and isinstance(tenant, DirectoryTenant)
            and isinstance(membership, DirectoryMembership)
        )
        if user.id != auth.user_id or tenant.id != auth.tenant_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "auth.context_mismatch",
                    "message": "You do not have access to this resource.",
                    "request_id": auth.request_id,
                },
            )
        if normalized_account is not None and projection["account_allowed"] is not True:
            raise _deny_account(auth.request_id)
        try:
            role = CanonicalAuthorizationRole(membership.role)
        except ValueError as exc:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "auth.role_unknown",
                    "message": "You do not have access to this resource.",
                    "request_id": auth.request_id,
                },
            ) from exc

        now = int(datetime.now(UTC).timestamp())
        expiry_limits = [token_exp, auth.exp, now + MAX_SNAPSHOT_TTL_SECONDS]
        for key in (
            "membership_valid_until",
            "permission_policy_valid_until",
            "entitlement_valid_until",
        ):
            limit = projection[key]
            if limit is not None:
                if not isinstance(limit, int):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "auth.projection_invalid",
                            "message": "You do not have access to this resource.",
                            "request_id": auth.request_id,
                        },
                    )
                expiry_limits.append(limit)
        expires = min(expiry_limits)
        if expires <= now:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "auth.session_expired",
                    "message": "Authentication required.",
                    "request_id": auth.request_id,
                },
            )
        permissions = sorted(ROLE_PERMISSIONS[role])
        return AuthorizationSnapshot(
            identity=SnapshotIdentity(
                clerk_user_id=auth.clerk_user_id, fabric_user_id=user.id, session_discriminator=sid
            ),
            tenant=SnapshotTenant(
                fabric_tenant_id=tenant.id,
                clerk_organization_id=tenant.clerk_org_id,
                tenant_slug=tenant.slug,
                membership_id=membership.clerk_membership_id,
                membership_status="active",
            ),
            account_scope=SnapshotAccountScope(
                scope_type="account" if normalized_account else "tenant",
                account_id=normalized_account,
            ),
            roles=[role],
            permissions=permissions,
            entitlements=list(projection["entitlements"]),
            issued_at=datetime.fromtimestamp(now, UTC).isoformat(),
            expires_at=datetime.fromtimestamp(expires, UTC).isoformat(),
        )
