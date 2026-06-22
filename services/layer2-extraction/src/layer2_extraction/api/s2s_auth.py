"""Service-to-service authentication guard for Layer 2 internal routes."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

S2S_INTERNAL_PATHS: frozenset[str] = frozenset(
    {
        "/v1/extract",
        "/v1/extract-and-ingest",
        "/v1/extract/batch",
    }
)
S2S_EXPECTED_SUB = "layer1-ingestion"
S2S_EXPECTED_AUD = "layer2-extraction"


def _requires_s2s_auth(request: Request) -> bool:
    return request.method == "POST" and request.url.path in S2S_INTERNAL_PATHS


def _s2s_error(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


async def enforce_s2s_auth_guard(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    *,
    is_strict_runtime: Callable[[], bool],
) -> Response:
    """Enforce inbound Layer 1 S2S JWTs on Layer 2 internal extraction routes."""
    if not _requires_s2s_auth(request):
        return await call_next(request)

    service_auth_secret = os.getenv("SERVICE_AUTH_SECRET", "").strip()
    if not service_auth_secret:
        if is_strict_runtime():
            return _s2s_error(
                503,
                "S2S authentication not configured in strict environment",
                "s2s_misconfiguration",
            )
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return _s2s_error(
            401,
            "S2S Bearer token required for internal extraction routes",
            "s2s_token_required",
        )

    token = auth_header[7:]
    try:
        from value_fabric.shared.identity.jwt import decode_service_jwt

        claims: Any = decode_service_jwt(token, expected_audience=S2S_EXPECTED_AUD)
    except Exception:
        claims = None

    if claims is None:
        return _s2s_error(
            401,
            "Invalid or expired S2S token for internal extraction route",
            "s2s_token_invalid",
        )

    if claims.sub != S2S_EXPECTED_SUB:
        return _s2s_error(
            403,
            f"Unexpected service caller: {claims.sub!r}",
            "s2s_caller_forbidden",
        )

    return await call_next(request)
