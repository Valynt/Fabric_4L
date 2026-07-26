"""Identity resolution strategies for the governance middleware.

Each strategy attempts to resolve a ``RequestContext`` from a different
credential source (Bearer JWT, session cookie, API key, service-to-service
header). The orchestrator tries them in priority order.
"""

from __future__ import annotations

import asyncio
import hmac
import inspect
import logging
import os
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status

from .constants import (
    ERR_AUTH_CONTEXT_INVALID,
    ERR_AUTH_INVALID_TOKEN,
    ERR_AUTH_SERVICE_UNAVAILABLE,
    MIN_SERVICE_SECRET_LENGTH,
    SERVICE_AUTH_HEADER,
    SESSION_COOKIE_NAME,
    TENANT_ID_HEADER,
    _LEGACY_TEST_TENANT_ID_RE,
)
from .context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
)
from .context_builders import (
    _allow_legacy_test_tenant_ids,
    build_context_from_role,
    extract_context_from_jwt,
    validate_context_consistency,
)
from .jwt_wrapper import decode_jwt
from .logging_helpers import _request_log_context
from .permissions import ROLE_PERMISSIONS, Permission, Role

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

logger = logging.getLogger(__name__)


async def resolve_bearer_jwt(request: Request) -> Optional[RequestContext]:
    """Resolve identity from Bearer JWT token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token_str = auth_header[7:]
    try:
        claims = await asyncio.to_thread(decode_jwt, token_str)
    except HTTPException:
        # ExpiredSignatureError → propagate 401 to client
        raise
    except Exception as exc:
        if jwt is not None and isinstance(exc, jwt.InvalidTokenError):
            logger.warning(
                "jwt_validation_failed",
                extra={
                    "event": "jwt_validation_failed",
                    "error_code": ERR_AUTH_INVALID_TOKEN,
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ERR_AUTH_INVALID_TOKEN,
                    "message": "Invalid token.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        logger.exception(
            "jwt_decode_failed_closed",
            extra={
                "event": "jwt_decode_failed_closed",
                "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                **_request_log_context(request),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                "message": "Authentication failed.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims is None:
        # Try service-to-service JWT before rejecting
        s2s_ctx = await resolve_s2s_jwt(token_str, request)
        if s2s_ctx is not None:
            return s2s_ctx
        logger.warning("JWT decode returned None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return build_context_from_claims(claims, request)


async def resolve_s2s_jwt(
    token_str: str, request: Request
) -> Optional[RequestContext]:
    """Try to resolve as service-to-service JWT."""
    try:
        from value_fabric.shared.identity.jwt import decode_service_jwt as _decode_service_jwt

        expected_audience = os.getenv("S2S_AUDIENCE", "").strip() or None
        s2s_claims = await asyncio.to_thread(
            _decode_service_jwt, token_str, expected_audience=expected_audience
        )
    except Exception as exc:
        if jwt is not None and isinstance(exc, jwt.ExpiredSignatureError):
            logger.debug("s2s_jwt_expired", extra={**_request_log_context(request)})
        else:
            logger.debug(
                "s2s_jwt_decode_failed",
                extra={"error": str(exc), **_request_log_context(request)},
            )
        return None

    if s2s_claims is None:
        return None

    try:
        tenant_id = UUID(str(s2s_claims.tenant_id))
    except ValueError:
        logger.warning(
            "s2s_jwt_invalid_tenant_id",
            extra={
                "tenant_id": s2s_claims.tenant_id,
                **_request_log_context(request),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid S2S token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return build_context_from_role(
        tenant_id,
        user_id=s2s_claims.sub,
        roles=[Role.SYSTEM.value],
        source=AUTH_SOURCE_SERVICE_ACCOUNT,
        raw={"aud": s2s_claims.aud, "sub": s2s_claims.sub},
        service_account_id=s2s_claims.sub,
        service_account_scopes=["tenant:seed", "system:internal", "s2s:invoke"],
    )


async def resolve_session_cookie(
    request: Request,
) -> Optional[RequestContext]:
    """Resolve identity from session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    try:
        claims = await asyncio.to_thread(decode_jwt, session_token)
    except HTTPException:
        raise
    except Exception as exc:
        if jwt is not None and isinstance(exc, jwt.InvalidTokenError):
            logger.warning(
                "session_jwt_validation_failed",
                extra={
                    "event": "session_jwt_validation_failed",
                    "error_code": ERR_AUTH_INVALID_TOKEN,
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ERR_AUTH_INVALID_TOKEN,
                    "message": "Invalid session.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        logger.exception(
            "session_jwt_decode_failed_closed",
            extra={
                "event": "session_jwt_decode_failed_closed",
                "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                **_request_log_context(request),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                "message": "Authentication failed.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims is None:
        logger.warning("Session cookie JWT decode returned None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return build_context_from_claims(claims, request)


async def resolve_api_key(
    request: Request,
    api_key_resolver: Optional[Callable],
) -> Optional[RequestContext]:
    """Resolve identity from X-API-Key header."""
    raw_api_key = request.headers.get("X-API-Key")
    if not raw_api_key or api_key_resolver is None:
        return None

    if inspect.iscoroutinefunction(api_key_resolver):
        record = await api_key_resolver(raw_api_key)
    else:
        record = api_key_resolver(raw_api_key)

    if not record or not record.get("enabled", True):
        return None

    try:
        tenant_id = UUID(str(record["tenant_id"]))
    except (ValueError, KeyError):
        logger.warning(
            "API key record has invalid tenant_id: %r", record.get("tenant_id")
        )
        return None

    role_str: str = record.get("role", Role.READ_ONLY.value)
    roles = [role_str]

    # Allow explicit per-key permission overrides stored in DB
    custom_perms: list[str] = record.get("permissions") or []
    if custom_perms:
        extra: set[Permission] = set()
        for p in custom_perms:
            try:
                extra.add(Permission(p))
            except ValueError:
                logger.warning(
                    "api_key_permission_ignored",
                    extra={
                        "event": "api_key_permission_ignored",
                        "error": str(p),
                        **_request_log_context(request),
                    },
                )
        role = Role(role_str)
        permissions = frozenset(ROLE_PERMISSIONS[role].permissions | extra)
    else:
        try:
            permissions = ROLE_PERMISSIONS[Role(role_str)].permissions
        except (ValueError, KeyError):
            permissions = frozenset()

    request.state.api_key_record = record
    return RequestContext(
        tenant_id=tenant_id,
        user_id=record.get("user_id"),
        roles=roles,
        api_key_id=record.get("key_id"),
        permissions=permissions,
        source="api_key",
        raw={"rate_limit_per_minute": record.get("rate_limit_per_minute")},
    )


async def resolve_service_to_service(
    request: Request,
) -> Optional[RequestContext]:
    """Resolve identity from X-Tenant-ID header with X-Service-Auth."""
    x_tenant = request.headers.get(TENANT_ID_HEADER)
    if not x_tenant:
        return None

    expected_secret = os.getenv("SERVICE_AUTH_SECRET")
    if not expected_secret:
        logger.warning("X-Tenant-ID rejected: SERVICE_AUTH_SECRET not configured")
        return None

    if len(expected_secret) < MIN_SERVICE_SECRET_LENGTH:
        logger.error(
            "SERVICE_AUTH_SECRET too short (%d chars, min %d)",
            len(expected_secret),
            MIN_SERVICE_SECRET_LENGTH,
        )
        return None

    provided_secret = request.headers.get(SERVICE_AUTH_HEADER, "")
    if not hmac.compare_digest(provided_secret, expected_secret):
        logger.warning("X-Tenant-ID rejected: invalid X-Service-Auth")
        return None

    try:
        tenant_id = UUID(x_tenant)
    except ValueError:
        logger.debug("Invalid X-Tenant-ID header: %r", x_tenant)
        return None

    return build_context_from_role(
        tenant_id,
        user_id="service",
        roles=[Role.SYSTEM.value],
        source=AUTH_SOURCE_SERVICE_ACCOUNT,
        raw={},
        service_account_id="service-auth-header",
        service_account_scopes=["tenant:seed", "system:internal"],
    )


def build_context_from_claims(
    claims: Any, request: Request
) -> RequestContext:
    """Build RequestContext from JWT claims with validation."""
    try:
        if isinstance(claims, dict):
            ctx = extract_context_from_jwt(claims)
        else:
            ctx = build_context_from_role(
                claims.tenant_id,
                user_id=getattr(claims, "user_id", None)
                or getattr(claims, "sub", None),
                roles=list(getattr(claims, "roles", []) or []),
                api_key_id=getattr(claims, "api_key_id", None),
                source="jwt",
                raw=getattr(claims, "extra_claims", {}) or {},
            )
        validate_context_consistency(
            ctx,
            request.headers.get(TENANT_ID_HEADER),
            route=request.url.path,
        )
        return ctx
    except ValueError as exc:
        logger.warning(
            "jwt_context_rejected",
            extra={
                "event": "jwt_context_rejected",
                "error_code": ERR_AUTH_CONTEXT_INVALID,
                "error": str(exc),
                **_request_log_context(request),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": ERR_AUTH_CONTEXT_INVALID,
                "message": "Tenant context mismatch.",
            },
        ) from exc


async def resolve_identity(
    request: Request,
    api_key_resolver: Optional[Callable] = None,
) -> Optional[RequestContext]:
    """Try each resolution strategy in priority order."""

    prepopulated_context = getattr(request.state, "governance_context", None)
    if isinstance(prepopulated_context, RequestContext):
        # Validate tenant_id format. Allow legacy test identifiers only when
        # explicitly permitted by environment (mirrors JWT claim coercion).
        if prepopulated_context.tenant_id is not None:
            try:
                UUID(str(prepopulated_context.tenant_id))
            except (TypeError, ValueError):
                if not _allow_legacy_test_tenant_ids():
                    logger.warning(
                        "prepopulated_context_invalid_tenant_id",
                        extra={
                            "tenant_id": str(prepopulated_context.tenant_id),
                            **_request_log_context(request),
                        },
                    )
                    return None
        return prepopulated_context

    # Reject malformed tenant identifiers early, before any resolver runs.
    raw_tenant_header = request.headers.get(TENANT_ID_HEADER)
    if raw_tenant_header is not None:
        try:
            UUID(raw_tenant_header)
        except ValueError:
            logger.debug("Invalid X-Tenant-ID header: %r", raw_tenant_header)
            return None

    # 1. Bearer JWT
    ctx = await resolve_bearer_jwt(request)
    if ctx is not None:
        return ctx

    # 2. Browser session cookie
    ctx = await resolve_session_cookie(request)
    if ctx is not None:
        return ctx

    # 3. X-API-Key header
    ctx = await resolve_api_key(request, api_key_resolver)
    if ctx is not None:
        return ctx

    # 4. X-Tenant-ID (service-to-service)
    ctx = await resolve_service_to_service(request)
    if ctx is not None:
        return ctx

    # No valid identity found
    return None
