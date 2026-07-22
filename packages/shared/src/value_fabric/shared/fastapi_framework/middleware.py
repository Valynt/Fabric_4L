"""Reusable FastAPI middleware assembly helpers.

These helpers keep service entrypoints focused on composition while preserving
the established middleware ordering choices in each layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from value_fabric.shared.error_handling import RequestIDMiddleware
from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
from value_fabric.shared.identity.audit import audit_protected_routes
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.security import SecurityConfig, add_security_middleware
from value_fabric.shared.security.config import is_strict_environment

_EXPLICIT_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_EXPLICIT_CORS_HEADERS = ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"]


@dataclass(frozen=True)
class CorsPolicy:
    """Normalized CORS settings for service entrypoints."""

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]

    def as_kwargs(self) -> dict[str, Any]:
        return {
            "allow_origins": self.allow_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
        }


def resolve_cors_policy(
    *,
    environment: str | None = None,
    origins_env: str | None = None,
) -> CorsPolicy:
    """Build a fail-safe CORS policy.

    Unknown/custom environments are treated as production-like so security
    controls are never accidentally relaxed.
    """
    environment_name = environment or os.getenv("ENVIRONMENT", "development")
    raw_origins = origins_env if origins_env is not None else os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    is_strict = is_strict_environment(environment_name)

    if is_strict and not origins:
        raise RuntimeError(
            "FATAL: CORS_ORIGINS environment variable must be set in production-like environments. "
            "Use 'https://yourdomain.com' or comma-separated list of allowed origins."
        )

    allow_origins = origins or ["*"]

    if is_strict:
        if "*" in allow_origins:
            raise RuntimeError(
                "FATAL: wildcard CORS origins are not permitted in production-like environments."
            )
        for origin in allow_origins:
            if "*" in origin:
                raise RuntimeError(
                    f"FATAL: CORS origin '{origin}' contains a wildcard. "
                    "Specify exact allowed origins."
                )

    return CorsPolicy(
        allow_origins=allow_origins,
        allow_credentials="*" not in allow_origins,
        allow_methods=_EXPLICIT_CORS_METHODS,
        allow_headers=_EXPLICIT_CORS_HEADERS,
    )


def add_request_id_middleware(app: FastAPI, *, enabled: bool = True) -> None:
    if enabled:
        app.add_middleware(RequestIDMiddleware)


def add_security_validation_middleware(
    app: FastAPI,
    *,
    skip_validation_paths: Iterable[str],
    strict_mode: bool = True,
) -> SecurityConfig:
    config = SecurityConfig.from_env(
        skip_validation_paths=frozenset(skip_validation_paths),
        strict_mode=strict_mode,
    )
    add_security_middleware(app, config=config)
    return config


def add_governance_middleware(app: FastAPI, *, rate_limiter: Any | None = None) -> None:
    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=reject_api_key_unsupported,
        rate_limiter=rate_limiter,
    )

    @app.on_event("startup")
    async def _audit_auth_routes() -> None:
        audit_protected_routes(app)


def add_cors_middleware(app: FastAPI, policy: CorsPolicy) -> None:
    app.add_middleware(CORSMiddleware, **policy.as_kwargs())


def add_rate_limit_middleware(
    app: FastAPI,
    *,
    rate_limiter_factory: Any,
    mode: Any,
    exempt_paths: list[str],
) -> None:
    """Install the shared tenant rate-limit middleware.

    ``rate_limiter_factory`` is a zero-arg callable that returns a
    :class:`TenantRateLimiter`. Instantiation is deferred so importing this
    module never forces a Redis connection.
    """

    from value_fabric.shared.fastapi_framework.app import EnforcementMode

    if mode == EnforcementMode.OFF:
        return

    try:
        from value_fabric.shared.rate_limiting import TenantRateLimitMiddleware
    except ImportError:
        return

    rate_limiter = rate_limiter_factory()
    app.add_middleware(
        TenantRateLimitMiddleware,
        rate_limiter=rate_limiter,
        exempt_paths=list(exempt_paths),
    )
    app.state.rate_limiter = rate_limiter


def add_idempotency_middleware(
    app: FastAPI,
    *,
    service_factory: Any,
    mode: Any,
    methods: frozenset[str],
    header_name: str = "Idempotency-Key",
) -> None:
    """Install a framework-level idempotency middleware.

    The middleware short-circuits replayed requests by ``Idempotency-Key`` and
    deduplicates against the shared :class:`IdempotencyService`. In AUDIT
    mode, conflicts are logged but the request continues; in ENFORCE mode the
    middleware returns ``409 Conflict``.
    """

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    from value_fabric.shared.fastapi_framework.app import (
        EnforcementMode,
        record_enforcement_decision,
    )
    from value_fabric.shared.idempotency import (
        IdempotencyConflictError,
        IdempotencyRequest,
        build_request_fingerprint,
    )

    if mode == EnforcementMode.OFF:
        return

    service = service_factory()
    methods_upper = {m.upper() for m in methods}

    class _IdempotencyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.method.upper() not in methods_upper:
                return await call_next(request)
            idem_key = request.headers.get(header_name)
            if not idem_key:
                return await call_next(request)

            from value_fabric.shared.boundaries.tenant_boundary import get_tenant_context

            ctx = get_tenant_context()
            tenant_id = str(ctx.tenant_id) if ctx and ctx.tenant_id else "anonymous"

            try:
                body_bytes = await request.body()
            except Exception:  # noqa: BLE001 — client disconnect or unreadable body
                return await call_next(request)

            try:
                import json as _json

                body = _json.loads(body_bytes) if body_bytes else {}
                if not isinstance(body, dict):
                    body = {"_raw": body}
            except Exception:  # noqa: BLE001
                body = {"_raw_len": len(body_bytes)}

            fingerprint = build_request_fingerprint(request.method, request.url.path, body)
            idem_request = IdempotencyRequest(
                tenant_id=tenant_id,
                endpoint_key=f"{request.method.upper()} {request.url.path}",
                idempotency_key=idem_key,
                request_fingerprint=fingerprint,
            )

            try:
                replay = service.check_replay(idem_request)
                if replay is not None:
                    return JSONResponse(
                        status_code=replay.status_code,
                        content=replay.body,
                        headers={**replay.headers, "Idempotent-Replay": "true"},
                    )
            except IdempotencyConflictError:
                allowed = record_enforcement_decision(
                    app,
                    control="idempotency",
                    violation="key_replay_fingerprint_mismatch",
                    route=request.url.path,
                    tenant_id=tenant_id,
                    actor_id=None,
                )
                if not allowed:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "error": "idempotency_conflict",
                            "message": "Idempotency key replayed with different payload.",
                        },
                    )

            # Re-inject the consumed body so downstream handlers can read it.
            async def _receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request._receive = _receive  # type: ignore[attr-defined]
            request.state.idempotency_request = idem_request
            request.state.idempotency_service = service

            return await call_next(request)

    app.add_middleware(_IdempotencyMiddleware)
    app.state.idempotency_service = service


def add_tenant_enforcement_middleware(app: FastAPI) -> None:
    """Install a middleware that audits/blocks requests missing tenant context.

    ``GovernanceMiddleware`` is the primary central fail-closed auth and tenant
    gate for non-public service routes. This rollout middleware remains as a
    defense-in-depth/audit control and explicitly skips the same external-auth
    bootstrap allowlist so probes and documentation never depend on middleware
    ordering.
    """

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    from value_fabric.shared.fastapi_framework.app import record_enforcement_decision
    from value_fabric.shared.identity.constants import _is_external_auth_bootstrap_path
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    class _TenantEnforcementMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            path = request.url.path
            if _is_external_auth_bootstrap_path(path):
                return await call_next(request)

            if any(middleware.cls is GovernanceMiddleware for middleware in app.user_middleware):
                return await call_next(request)

            from value_fabric.shared.boundaries.tenant_boundary import get_tenant_context

            ctx = get_tenant_context()
            tenant_id = str(ctx.tenant_id) if ctx and ctx.tenant_id else None

            if tenant_id is None:
                allowed = record_enforcement_decision(
                    app,
                    control="tenant_enforcement",
                    violation="missing_tenant_context",
                    route=path,
                    tenant_id=None,
                    actor_id=None,
                )
                if not allowed:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "tenant_context_required",
                            "message": "Request did not establish a tenant context.",
                        },
                    )

            return await call_next(request)

    app.add_middleware(_TenantEnforcementMiddleware)
