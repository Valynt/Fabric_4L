"""Audit logging middleware for state-changing and sensitive read actions.

Logs every POST, PUT, PATCH, DELETE with:
- timestamp
- actor_id (sub from JWT)
- tenant_id
- impersonator_id (if applicable)
- ip_address
- method, path, status_code

Also logs GET requests to SENSITIVE_READ_PATHS (F-20): endpoints that expose
user lists, audit logs, or configuration data. These reads must be traceable
for SOC 2 CC7.2 compliance.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from value_fabric.shared.identity.context import get_request_context

logger = logging.getLogger("fabric.audit")

# State-changing HTTP methods
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths to skip audit logging
AUDIT_SKIP_PATHS = {
    "/health",
    "/health/detailed",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# GET paths that expose sensitive data and must be audit-logged (F-20).
# Reads of user lists, audit logs, and configuration are traceable for SOC 2 CC7.2.
SENSITIVE_READ_PATHS: frozenset[str] = frozenset({
    "/v1/users",
    "/v1/accounts",
    "/governance/audit-log",
    "/governance/review-queue",
    "/governance/gates",
    "/auth/me",
})

# Path prefixes that trigger sensitive-read logging regardless of exact path.
SENSITIVE_READ_PREFIXES: tuple[str, ...] = (
    "/v1/users/",
    "/v1/accounts/",
)


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every state-changing request with identity and tenant context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        if request.url.path in AUDIT_SKIP_PATHS or request.url.path.startswith(("/docs", "/redoc")):
            return response

        method = request.method.upper()
        path = request.url.path
        is_mutating = method in MUTATING_METHODS
        is_sensitive_read = (
            method == "GET"
            and (
                path in SENSITIVE_READ_PATHS
                or path.startswith(SENSITIVE_READ_PREFIXES)
            )
        )

        # Log mutating requests and sensitive reads; skip everything else.
        if not is_mutating and not is_sensitive_read:
            return response

        ctx = get_request_context()

        actor_id = str(ctx.user_id) if ctx and ctx.user_id else None
        tenant_id = str(ctx.tenant_id) if ctx and ctx.tenant_id else None
        impersonator_id = ctx.impersonator_id if ctx else None
        request_id = request.headers.get("X-Request-ID") or (ctx.request_id if ctx else None)

        # Extract client IP with proxy awareness
        forwarded = request.headers.get("X-Forwarded-For")
        real_ip = request.headers.get("X-Real-IP")
        client_ip = (
            forwarded.split(",")[0].strip() if forwarded
            else real_ip if real_ip
            else request.client.host if request.client
            else None
        )

        event_type = "sensitive_read" if is_sensitive_read else "state_change"
        audit_entry: dict[str, Any] = {
            "event": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "impersonator_id": impersonator_id,
            "ip_address": client_ip,
            "method": method,
            "path": request.url.path,
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Security events: always log at WARNING
        if response.status_code in (401, 403):
            audit_entry["event"] = "access_denied"
            logger.warning("access_denied", extra=audit_entry)
        elif response.status_code >= 500:
            audit_entry["event"] = "server_error"
            logger.error("server_error", extra=audit_entry)
        else:
            logger.info(event_type, extra=audit_entry)

        return response
