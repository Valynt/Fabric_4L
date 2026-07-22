"""Context building, validation, and tenant ID coercion helpers.

These functions build validated ``RequestContext`` objects from JWT claims,
API key records, or role-based parameters, and enforce tenant identifier
consistency across trusted and untrusted inputs.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status

from .constants import _LEGACY_TEST_TENANT_ID_RE
from .context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
)
from .permissions import ROLE_PERMISSIONS, Permission, Role, normalize_role_claims
from value_fabric.shared.tenant_context_metrics import record_inconsistent_tenant_context_access

logger = logging.getLogger(__name__)

_KNOWN_PERMISSION_VALUES: frozenset[str] = frozenset(p.value for p in Permission)


def _is_known_permission(value: str) -> bool:
    """Return True only for strings that map to a known Permission enum value.

    Wildcards (``"*"``, ``"all"``) and any other unrecognised strings return
    False so they are silently discarded when building a RequestContext.
    """
    return value in _KNOWN_PERMISSION_VALUES


def _allow_legacy_test_tenant_ids() -> bool:
    environment = (
        os.getenv("ENVIRONMENT")
        or os.getenv("ENV")
        or os.getenv("APP_ENV")
        or "development"
    )
    explicit_test_flag = (
        os.getenv("ALLOW_LEGACY_TEST_TENANT_IDS", "").strip().lower() == "true"
        or os.getenv("TESTING", "").strip().lower() == "true"
    )
    if not explicit_test_flag:
        return False
    if environment.strip().lower() in {"prod", "production", "staging", "stage"}:
        return False
    # Reject legacy tenant IDs when production-like deployment markers are present,
    # matching the fail-closed behaviour in jwt.py.
    production_like_markers = (
        "KUBERNETES_SERVICE_HOST",
        "K_SERVICE",
        "ECS_CONTAINER_METADATA_URI",
        "ECS_CONTAINER_METADATA_URI_V4",
        "AWS_EXECUTION_ENV",
        "DYNO",
    )
    if any(os.getenv(key, "").strip() for key in production_like_markers):
        return False
    return True


def _coerce_tenant_id_for_context(raw_tenant_id: Any) -> UUID | str:
    try:
        return UUID(str(raw_tenant_id))
    except (TypeError, ValueError) as exc:
        if _allow_legacy_test_tenant_ids() and _LEGACY_TEST_TENANT_ID_RE.fullmatch(
            str(raw_tenant_id)
        ):
            return str(raw_tenant_id)
        raise ValueError("Invalid tenant_id in JWT claims") from exc


def extract_context_from_jwt(payload: dict[str, Any]) -> RequestContext:
    """Build a validated request context from decoded JWT claims.

    This helper is intentionally small and shared by middleware and security
    contract tests so JWT tenant/user extraction has one fail-closed contract.
    Supports both internal (HS256) and Keycloak (RS256) token claim shapes.
    """
    if "tenant_id" not in payload or not payload.get("tenant_id"):
        raise ValueError("tenant_id is required in JWT claims")
    tenant_id = _coerce_tenant_id_for_context(payload["tenant_id"])

    raw_user_id = payload.get("sub") or payload.get("user_id")
    user_id: Optional[UUID | str] = None
    if raw_user_id is not None:
        try:
            user_id = UUID(str(raw_user_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid user_id in JWT claims") from exc

    # L1 Organization (billing entity)
    org_id: Optional[UUID | str] = None
    raw_org = payload.get("org_id")
    if raw_org is not None:
        try:
            org_id = UUID(str(raw_org))
        except (TypeError, ValueError):
            org_id = str(raw_org)

    # L3 Workspace (project boundary)
    workspace_id: Optional[UUID | str] = None
    raw_workspace = payload.get("workspace_id")
    if raw_workspace is not None:
        try:
            workspace_id = UUID(str(raw_workspace))
        except (TypeError, ValueError):
            workspace_id = str(raw_workspace)

    raw_permissions = payload.get("permissions") or []
    if len(raw_permissions) > 1024:
        raise ValueError("Too many permissions in JWT claims")
    # Filter to known Permission enum values only. Unknown strings (including
    # wildcards like "*" or "all") are silently discarded — they must never
    # grant access. This prevents wildcard injection via JWT claims.
    permissions: frozenset[Permission] = frozenset(
        Permission(str(p)) for p in raw_permissions if _is_known_permission(str(p))
    )
    roles = payload.get("roles") or []
    if not roles and payload.get("role"):
        roles = [payload.get("role")]
    if isinstance(roles, str):
        roles = [roles]
    roles = normalize_role_claims(roles)

    return RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        org_id=org_id,
        workspace_id=workspace_id,
        roles=list(roles),
        permissions=permissions,
        source="jwt",
        raw=dict(payload),
        impersonator_id=payload.get("impersonator_id"),
    )


async def lookup_api_key(api_key: str) -> Optional[dict[str, Any]]:
    """Repository-level lookup seam used by tests; production middleware injects a resolver."""
    return None


async def extract_context_from_api_key(api_key: str) -> RequestContext:
    """Build a validated request context from an API-key lookup record."""
    record = lookup_api_key(api_key)
    if inspect.isawaitable(record):
        record = await record
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    try:
        tenant_id = UUID(str(record["tenant_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid tenant_id in API key record") from exc
    permissions = record.get("permissions") or []
    if len(permissions) > 1024:
        raise ValueError("Too many permissions in API key record")
    return RequestContext(
        tenant_id=tenant_id,
        user_id=record.get("user_id"),
        roles=list(record.get("roles") or []),
        api_key_id=record.get("key_id"),
        permissions=frozenset(str(permission) for permission in permissions),
        source="api_key",
        raw={"api_key_lookup": True},
    )


def validate_context_consistency(
    ctx: RequestContext,
    header_tenant_id: Optional[str],
    *,
    route: str = "request_context",
) -> None:
    """Reject conflicting tenant identifiers across trusted and untrusted inputs.

    JWT/API-key tenant claims are authoritative.  A caller-provided
    ``X-Tenant-ID`` may be present for traceability or legacy clients, but it may
    not change tenant scope and must either be a canonical UUID or an explicitly
    allowed legacy test tenant identifier.  Invalid or conflicting headers fail
    closed before downstream layer routes can read raw request headers.
    """
    if not header_tenant_id:
        return
    raw_header = str(header_tenant_id).strip()
    if not raw_header:
        record_inconsistent_tenant_context_access(route=route, source="header_invalid")
        raise ValueError("Invalid tenant_id header")
    try:
        header_value: UUID | str = UUID(raw_header)
    except (TypeError, ValueError) as exc:
        if _allow_legacy_test_tenant_ids() and _LEGACY_TEST_TENANT_ID_RE.fullmatch(
            raw_header
        ):
            header_value = raw_header
        else:
            record_inconsistent_tenant_context_access(
                route=route, source="header_invalid"
            )
            raise ValueError("Invalid tenant_id header") from exc
    if str(ctx.tenant_id) != str(header_value):
        record_inconsistent_tenant_context_access(route=route, source="header")
        raise ValueError(
            "Conflicting tenant_id between authenticated context and header"
        )


def build_context_from_role(
    tenant_id: UUID,
    *,
    user_id: Optional[str],
    roles: list[str],
    api_key_id: Optional[str] = None,
    source: str,
    raw: dict,
    service_account_id: Optional[str] = None,
    service_account_scopes: Optional[list[str]] = None,
) -> RequestContext:
    """Build a RequestContext, computing effective permissions from roles."""
    roles = normalize_role_claims(roles)
    permissions: set[Permission] = set()
    for role_str in roles:
        try:
            role = Role(role_str)
            permissions |= ROLE_PERMISSIONS[role].permissions
        except (ValueError, KeyError):
            logger.debug("Unknown role '%s' in token — skipping", role_str)

    return RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        api_key_id=api_key_id,
        permissions=frozenset(permissions),
        source=source,
        raw=raw,
        service_account_id=service_account_id,
        service_account_scopes=service_account_scopes or [],
    )
