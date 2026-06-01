"""FastAPI middleware that enforces the Fabric4L internal AuthContext envelope.

Used by L1–L6. The gateway (services/api) does NOT use this middleware
for inbound external requests (those carry raw Clerk JWTs); the gateway
uses it only for internal service-to-service calls if/when they exist.

Modes:
    - ``enforce`` (default): missing/invalid envelope -> 401/403.
    - ``observe``: log + tag request.state.auth if present, but allow
      legacy auth to continue. Used during the rollout window.

Public-path allowlist:
    Health/metrics endpoints are always allowed; everything else is
    gated. Override via ``public_paths``.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .context import AuthContext, DEFAULT_AUDIENCE, DEFAULT_ISSUER
from .errors import (
    EnvelopeMissingError,
    FabricAuthError,
    TenantMismatchError,
)
from .signer import KeySet, verify_envelope

logger = logging.getLogger(__name__)

ENVELOPE_HEADER = "X-Fabric-Auth"
TENANT_HINT_HEADER = "X-Tenant-ID"
REQUEST_ID_HEADER = "X-Request-ID"

DEFAULT_PUBLIC_PATHS: tuple[str, ...] = (
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/live",
    "/livez",
    "/openapi.json",
    "/docs",
    "/redoc",
)

_AUTH_CONTEXT: ContextVar[AuthContext | None] = ContextVar(
    "fabric_auth_context", default=None
)


def get_auth_context() -> AuthContext | None:
    """Return the current request's :class:`AuthContext`, if any."""
    return _AUTH_CONTEXT.get()


def require_auth_context() -> AuthContext:
    """FastAPI dependency: assert an envelope was verified for this request."""
    auth = _AUTH_CONTEXT.get()
    if auth is None:
        raise EnvelopeMissingError(log_detail="no AuthContext on request")
    return auth


class FabricAuthMiddleware(BaseHTTPMiddleware):
    """Verify the ``X-Fabric-Auth`` envelope on every request.

    Args:
        key_set: verification keys indexed by ``kid``.
        expected_issuer: must equal envelope ``iss``.
        expected_audience: must equal envelope ``aud``.
        mode: ``"enforce"`` or ``"observe"``.
        public_paths: prefix paths excluded from auth.
        tenant_hint_must_match: when True (default), reject requests whose
            ``X-Tenant-ID`` header does not equal the envelope tenant.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        key_set: KeySet,
        expected_issuer: str = DEFAULT_ISSUER,
        expected_audience: str = DEFAULT_AUDIENCE,
        mode: str = "enforce",
        public_paths: Iterable[str] = DEFAULT_PUBLIC_PATHS,
        tenant_hint_must_match: bool = True,
    ) -> None:
        super().__init__(app)
        if mode not in {"enforce", "observe"}:
            raise ValueError(f"invalid mode: {mode!r}")
        self._key_set = key_set
        self._issuer = expected_issuer
        self._audience = expected_audience
        self._mode = mode
        self._public_paths = tuple(public_paths)
        self._tenant_hint_must_match = tenant_hint_must_match

    def _is_public(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self._public_paths)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if self._is_public(request.url.path):
            return await call_next(request)

        token = request.headers.get(ENVELOPE_HEADER)
        token_value = token.strip() if token else ""
        # Tolerate "Bearer <jwt>" form even though we recommend bare token.
        if token_value.lower().startswith("bearer "):
            token_value = token_value[7:].strip()

        auth: AuthContext | None = None
        failure: FabricAuthError | None = None

        if not token_value:
            failure = EnvelopeMissingError()
        else:
            try:
                auth = verify_envelope(
                    token_value,
                    key_set=self._key_set,
                    expected_issuer=self._issuer,
                    expected_audience=self._audience,
                )
            except FabricAuthError as exc:
                failure = exc

        if auth is not None and self._tenant_hint_must_match:
            hint = request.headers.get(TENANT_HINT_HEADER)
            if hint and hint != auth.tenant_id:
                failure = TenantMismatchError(
                    log_detail=(
                        f"X-Tenant-ID hint={hint!r} != envelope={auth.tenant_id!r}"
                    )
                )
                auth = None

        if failure is not None:
            logger.warning(
                "fabric_auth %s code=%s path=%s detail=%s",
                "rejected" if self._mode == "enforce" else "observed",
                failure.code,
                request.url.path,
                failure.log_detail,
            )
            if self._mode == "enforce":
                return JSONResponse(
                    status_code=failure.http_status,
                    content={
                        "code": failure.code,
                        "message": failure.public_message,
                        "request_id": request.headers.get(REQUEST_ID_HEADER),
                    },
                )
            # observe mode: continue without an auth context
            request.state.auth = None
            return await call_next(request)

        assert auth is not None  # for type checkers
        token_var = _AUTH_CONTEXT.set(auth)
        try:
            request.state.auth = auth
            response: Response = await call_next(request)
        finally:
            _AUTH_CONTEXT.reset(token_var)

        if REQUEST_ID_HEADER not in response.headers and auth.request_id:
            response.headers[REQUEST_ID_HEADER] = auth.request_id
        return response
