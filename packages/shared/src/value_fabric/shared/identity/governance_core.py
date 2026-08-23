"""Governance core - runtime-agnostic tenant resolution and governance logic.

This module provides the shared governance logic used by both async and sync
middleware adapters. It handles:
- Identity resolution from JWT, API keys, and headers
- Tenant context construction
- Audit payload creation
- Access policy validation

The goal is to have one governance contract with multiple runtime adapters.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol
from uuid import UUID

from .context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_JWT,
    AUTH_SOURCE_SERVICE_ACCOUNT,
    ISOLATION_TIER_SHARED,
    RequestContext,
)
from .jwt import decode_jwt
from value_fabric.shared.models.typed_dict import TypedDictModel


class GovernanceCore_create_audit_payloadResult(TypedDictModel):
    api_key_id: Any
    auth_method: Any
    failure_reason: Any
    has_org_id: bool
    is_super_admin: Any
    isolation_tier: Any
    org_id: Any
    outcome: Any
    request_method: Any
    request_path: Any
    resolution_source: Any
    resolved_tenant_id: Any
    roles: list[str]
    service_account_id: Any
    tenant_role: Any
    user_id: Any


logger = logging.getLogger(__name__)


class APIKeyResolver(Protocol):
    """Protocol for API key resolution."""

    async def __call__(self, raw_key: str) -> dict | None: ...


class TenantSettingsResolver(Protocol):
    """Protocol for tenant settings resolution."""

    async def __call__(self, tenant_id: UUID) -> dict | None: ...


class GovernanceCore:
    """Runtime-agnostic governance logic for tenant resolution and access control.

    This class contains the core logic for identity resolution and tenant
    context construction. It is used by both async and sync middleware adapters.

    Usage:
        core = GovernanceCore(api_key_resolver=my_resolver)
        ctx = await core.resolve_identity(
            auth_header="Bearer <token>",
            api_key_header=None,
            x_tenant_header=None,
        )
    """

    def __init__(
        self,
        *,
        api_key_resolver: APIKeyResolver | None = None,
        tenant_settings_resolver: TenantSettingsResolver | None = None,
        jwt_secret: str | None = None,
        allow_query_param: bool = False,
    ) -> None:
        """Initialize governance core.

        Args:
            api_key_resolver: Optional async callable to resolve API keys
            tenant_settings_resolver: Optional async callable for tenant settings
            jwt_secret: Secret for JWT verification (defaults to env var)
            allow_query_param: Whether to allow tenant_id in query params (dev/test only)
        """
        self._api_key_resolver = api_key_resolver
        self._tenant_settings_resolver = tenant_settings_resolver
        self._jwt_secret = jwt_secret or os.getenv("JWT_SECRET", "")
        # P0 FIX: Query param tenant authentication removed entirely
        self._allow_query_param = False

    async def resolve_identity(
        self,
        *,
        auth_header: str | None = None,
        api_key_header: str | None = None,
        x_tenant_header: str | None = None,
        query_params: dict[str, Any] | None = None,
        request_path: str | None = None,
        request_method: str | None = None,
    ) -> RequestContext | None:
        """Resolve identity and tenant context from request metadata.

        Resolution order (first match wins):
        1. Bearer JWT - extracts tenant_id, user_id, roles from claims
        2. X-API-Key header - looks up key in database
        3. X-Tenant-ID header - service-to-service calls (system role)
        4. Query param tenant_id - dev/test fallback only

        Args:
            auth_header: Authorization header value (e.g., "Bearer <token>")
            api_key_header: X-API-Key header value
            x_tenant_header: X-Tenant-ID header value
            query_params: Query parameters dict (may contain tenant_id)
            request_path: Request path for audit logging
            request_method: HTTP method for audit logging

        Returns:
            RequestContext if identity resolved, None otherwise
        """
        # 1. Bearer JWT
        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            # Skip if it looks like an API key
            if not token_str.startswith("vf_"):
                try:
                    payload = decode_jwt(token_str, self._jwt_secret)
                    if payload:
                        return self._build_context_from_jwt(payload)
                except Exception as e:
                    logger.debug("JWT resolution failed: %s", e)
                    return None

        # 2. X-API-Key header
        if api_key_header and self._api_key_resolver:
            try:
                record = await self._api_key_resolver(api_key_header)
                if record and record.get("enabled", True):
                    return self._build_context_from_api_key(record)
            except Exception as e:
                logger.debug("API key resolution failed: %s", e)

        # 3. X-Tenant-ID (service-to-service)
        # P0 FIX: Require SERVICE_AUTH_SECRET to prevent header spoofing
        if x_tenant_header:
            expected_secret = os.getenv("SERVICE_AUTH_SECRET", "")
            if not expected_secret:
                logger.warning(
                    "X-Tenant-ID rejected: SERVICE_AUTH_SECRET not configured"
                )
                return None
            provided_secret = (
                query_params.get("x_service_auth") if query_params else None
            )
            if not provided_secret:
                provided_secret = ""
            import hmac

            if not hmac.compare_digest(provided_secret, expected_secret):
                logger.warning("X-Tenant-ID rejected: invalid service auth secret")
                return None
            try:
                tenant_id = UUID(x_tenant_header)
                return RequestContext(
                    tenant_id=tenant_id,
                    user_id="service",
                    roles=["system"],
                    auth_source=AUTH_SOURCE_JWT,  # Internal service auth
                    request_id=None,
                )
            except ValueError:
                logger.debug("Invalid X-Tenant-ID: %s", x_tenant_header)

        # P0 FIX: Query param tenant authentication removed entirely — never trust client-supplied identity

        return None

    def _build_context_from_jwt(self, payload: dict[str, Any]) -> RequestContext:
        """Build RequestContext from JWT payload."""
        from uuid import UUID

        tenant_id = UUID(payload.get("tenant_id")) if payload.get("tenant_id") else None
        user_id = UUID(payload.get("sub")) if payload.get("sub") else None
        org_id = UUID(payload.get("org_id")) if payload.get("org_id") else None

        # Service account detection
        service_account_id = None
        service_account_scopes = []
        auth_source = payload.get("auth_source", AUTH_SOURCE_JWT)

        svc_id = payload.get("service_account_id")
        if svc_id:
            service_account_id = UUID(svc_id)
            service_account_scopes = payload.get("scopes", [])
            auth_source = AUTH_SOURCE_SERVICE_ACCOUNT

        # Derive permissions from roles
        roles = payload.get("roles", [])
        permissions = self._derive_permissions(roles)

        return RequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            org_id=org_id,
            tenant_role=payload.get("tenant_role"),
            isolation_tier=payload.get("isolation_tier", ISOLATION_TIER_SHARED),
            roles=roles,
            permissions=permissions,
            auth_source=auth_source,
            service_account_id=service_account_id,
            service_account_scopes=service_account_scopes,
            request_id=None,  # Set by caller
        )

    def _build_context_from_api_key(self, record: dict[str, Any]) -> RequestContext:
        """Build RequestContext from API key record."""
        from uuid import UUID

        tenant_id = UUID(str(record["tenant_id"])) if record.get("tenant_id") else None
        user_id = UUID(str(record["user_id"])) if record.get("user_id") else None

        role = record.get("role", "read_only")
        roles = [role]

        # Get permissions from role + custom perms
        permissions = self._derive_permissions(roles)
        custom_perms = record.get("permissions", [])
        if custom_perms:
            permissions = list(set(permissions + custom_perms))

        return RequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            api_key_id=record.get("key_id"),
            roles=roles,
            permissions=permissions,
            auth_source=AUTH_SOURCE_API_KEY,
            request_id=None,
        )

    def _derive_permissions(self, roles: list[str]) -> list[str]:
        """Derive permissions from roles."""
        # Import here to avoid circular dependency
        try:
            from .permissions import get_permissions_for_role

            perms = []
            for role in roles:
                perms.extend(get_permissions_for_role(role))
            return list(set(perms))
        except ImportError:
            return []

    def check_access_policy(
        self,
        context: RequestContext,
        required_roles: list[str] | None = None,
        required_permissions: list[str] | None = None,
    ) -> tuple[bool, str | None]:
        """Check if context meets access policy requirements.

        Args:
            context: The request context to check
            required_roles: List of roles, any of which grants access
            required_permissions: List of permissions, all required

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        if required_roles:
            if not context.roles:
                return False, "No roles assigned"
            if not any(r in context.roles for r in required_roles):
                return False, f"Required one of roles: {required_roles}"

        if required_permissions:
            if not context.permissions:
                return False, "No permissions assigned"
            missing = [p for p in required_permissions if not context.has_permission(p)]
            if missing:
                return False, f"Missing permissions: {missing}"

        return True, None

    def create_audit_payload(
        self,
        context: RequestContext,
        source: str,
        *,
        request_path: str | None = None,
        request_method: str | None = None,
        outcome: str = "success",
        failure_reason: str | None = None,
    ) -> dict[str, Any]:
        """Create standardized audit payload for tenant resolution.

        Args:
            context: The resolved request context
            source: How the identity was resolved
            request_path: API path being accessed
            request_method: HTTP method
            outcome: "success" | "failure"
            failure_reason: Reason for failure if applicable

        Returns:
            Dictionary suitable for audit event details
        """
        return GovernanceCore_create_audit_payloadResult.model_validate(
            {
                "resolution_source": source,
                "resolved_tenant_id": (
                    str(context.tenant_id) if context.tenant_id else None
                ),
                "user_id": str(context.user_id) if context.user_id else None,
                "api_key_id": str(context.api_key_id) if context.api_key_id else None,
                "service_account_id": (
                    str(context.service_account_id)
                    if context.service_account_id
                    else None
                ),
                "auth_method": context.auth_source,
                "has_org_id": context.org_id is not None,
                "org_id": str(context.org_id) if context.org_id else None,
                "tenant_role": context.tenant_role,
                "isolation_tier": context.isolation_tier,
                "roles": context.roles or [],
                "is_super_admin": context.is_super_admin(),
                "outcome": outcome,
                "failure_reason": failure_reason,
                "request_path": request_path,
                "request_method": request_method,
            }
        )
