"""FastAPI dependency wiring for Clerk-based authentication.

Activated only when ``AUTH_PROVIDER=clerk``. Until then, routes continue
to use the legacy ``require_authenticated`` from :mod:`app.core.security`.

This module deliberately does NOT modify legacy auth in any way — flipping
``AUTH_PROVIDER=clerk`` swaps the dependency at the route layer without
touching unrelated code paths. That keeps the rollout surgical.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.identity.fabric_auth import AuthContext

from .auth_context_builder import (
    MembershipNotActiveError,
    TenantResolutionError,
    UserNotProvisionedError,
    build_auth_context,
)
from .auth_directory import get_auth_directory
from .auth_telemetry import (
    record_auth_failure,
    record_auth_success,
    record_clock_skew,
)
from .clerk_config import (
    AUTH_PROVIDER_CLERK,
    get_auth_settings,
)
from .clerk_verifier import (
    ClerkAuthorizedPartyError,
    ClerkTokenError,
    ClerkTokenExpired,
    ClerkVerifier,
)

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_CLERK_SETTINGS_MISSING = "Clerk verifier requested but Clerk settings are missing"


@lru_cache
def _get_verifier() -> ClerkVerifier:
    settings = get_auth_settings()
    if settings.clerk is None:
        raise RuntimeError(_CLERK_SETTINGS_MISSING)
    return ClerkVerifier(settings.clerk)


def reset_clerk_verifier_cache() -> None:
    _get_verifier.cache_clear()


async def require_clerk_authenticated(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> AuthContext:
    """FastAPI dependency: verify the Clerk Bearer token + build AuthContext.

    On success, the AuthContext is also stored on ``request.state.auth``.
    Failures map to 401 (token issues) or 403 (authorization issues), both
    with sanitized public messages. Detailed reasons are logged only.
    """
    settings = get_auth_settings()
    if settings.provider != AUTH_PROVIDER_CLERK:
        # Defensive: the route should only depend on this if Clerk is active.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "auth.misconfigured",
                "message": "Clerk auth is not enabled.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    if credentials is None:
        # Fall back to manual extraction so existing OpenAPI tooling still works.
        creds_dependency = await _bearer_scheme(request)
        credentials = creds_dependency  # type: ignore[assignment]

    if credentials is None or not credentials.credentials:
        record_auth_failure(
            provider="clerk",
            reason="token_missing",
            latency_seconds=time.perf_counter() - start_time,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_TOKEN_MISSING,
                "message": "Authentication required.",
                "request_id": request.headers.get("X-Request-ID"),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier = _get_verifier()
    try:
        claims = verifier.verify(credentials.credentials)
    except ClerkTokenExpired as exc:
        record_auth_failure(
            provider="clerk",
            reason="expired",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.info("clerk token expired: %s", exc.log_detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ClerkAuthorizedPartyError as exc:
        record_auth_failure(
            provider="clerk",
            reason="azp_mismatch",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.warning("clerk azp check failed: %s", exc.log_detail)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
        ) from exc
    except ClerkTokenError as exc:
        record_auth_failure(
            provider="clerk",
            reason="token_invalid",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.warning("clerk token rejected: %s", exc.log_detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_TOKEN_INVALID,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims.iat is not None:
        skew = abs(time.time() - float(claims.iat))
        record_clock_skew("clerk", skew)

    # Check session denylist and user revocation
    directory = get_auth_directory()
    sid = claims.raw.get("sid")
    if isinstance(sid, str) and directory.is_session_revoked(sid):
        record_auth_failure(
            provider="clerk",
            reason="session_revoked",
            latency_seconds=time.perf_counter() - start_time,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_TOKEN_INVALID,
                "message": "Session has been revoked.",
                "request_id": request.headers.get("X-Request-ID"),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if directory.is_user_session_revoked(claims.sub, token_iat=claims.iat):
        record_auth_failure(
            provider="clerk",
            reason="session_revoked",
            latency_seconds=time.perf_counter() - start_time,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_TOKEN_INVALID,
                "message": "All user sessions have been revoked.",
                "request_id": request.headers.get("X-Request-ID"),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if settings.envelope is None:
        record_auth_failure(
            provider="clerk",
            reason="envelope_misconfigured",
            latency_seconds=time.perf_counter() - start_time,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "auth.envelope_misconfigured",
                "message": "Authentication required.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    try:
        auth = build_auth_context(
            claims=claims,
            directory=get_auth_directory(),
            envelope_settings=settings.envelope,
            request_id=request.headers.get("X-Request-ID"),
        )
    except TenantResolutionError as exc:
        record_auth_failure(
            provider="clerk",
            reason="tenant_unresolved",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.warning("auth context build failed (tenant unresolved): %s", exc.log_detail)
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
        ) from exc
    except MembershipNotActiveError as exc:
        record_auth_failure(
            provider="clerk",
            reason="membership_inactive",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.warning("auth context build failed (membership inactive): %s", exc.log_detail)
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
        ) from exc
    except UserNotProvisionedError as exc:
        record_auth_failure(
            provider="clerk",
            reason="user_not_provisioned",
            latency_seconds=time.perf_counter() - start_time,
        )
        logger.warning("auth context build failed (user not provisioned): %s", exc.log_detail)
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": request.headers.get("X-Request-ID"),
            },
        ) from exc

    duration = time.perf_counter() - start_time
    record_auth_success(provider="clerk", tenant_id=auth.tenant_id, latency_seconds=duration)

    request.state.auth = auth
    # Preserve verified external claims for endpoints that must bind output to
    # the exact Clerk session. These claims are never accepted from headers.
    request.state.clerk_claims = claims.raw
    return auth
