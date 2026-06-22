"""Service-to-service authentication guard for Layer 2 internal routes."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class S2SAuthFailure:
    status_code: int
    detail: str
    code: str


def _requires_s2s_auth(request: Request) -> bool:
    return request.method == "POST" and request.url.path in S2S_INTERNAL_PATHS


def _service_auth_secret_configured() -> bool:
    return bool(os.getenv("SERVICE_AUTH_SECRET", "").strip())


def _extract_bearer_token(auth_header: str) -> str | None:
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _decode_s2s_claims(token: str) -> Any | None:
    try:
        from value_fabric.shared.identity.jwt import decode_service_jwt

        return decode_service_jwt(token, expected_audience=S2S_EXPECTED_AUD)
    except Exception:
        return None


def validate_s2s_request(request: Request) -> S2SAuthFailure | None:
    """Return an auth failure for protected S2S requests, otherwise None."""
    auth_header = request.headers.get("Authorization", "")
    token = _extract_bearer_token(auth_header)
    if token is None:
        return S2SAuthFailure(
            401,
            "S2S Bearer token required for internal extraction routes",
            "s2s_token_required",
        )

    claims = _decode_s2s_claims(token)
    if claims is None:
        return S2SAuthFailure(
            401,
            "Invalid or expired S2S token for internal extraction route",
            "s2s_token_invalid",
        )

    if claims.sub != S2S_EXPECTED_SUB:
        return S2SAuthFailure(
            403,
            f"Unexpected service caller: {claims.sub!r}",
            "s2s_caller_forbidden",
        )

    return None


def _s2s_error(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


def _s2s_failure_response(failure: S2SAuthFailure) -> JSONResponse:
    return _s2s_error(failure.status_code, failure.detail, failure.code)


async def enforce_s2s_auth_guard(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    *,
    is_strict_runtime: Callable[[], bool],
) -> Response:
    """Enforce inbound Layer 1 S2S JWTs on Layer 2 internal extraction routes."""
    if not _requires_s2s_auth(request):
        return await call_next(request)

    if not _service_auth_secret_configured():
        if is_strict_runtime():
            return _s2s_error(
                503,
                "S2S authentication not configured in strict environment",
                "s2s_misconfiguration",
            )
        return await call_next(request)

    failure = validate_s2s_request(request)
    if failure is not None:
        return _s2s_failure_response(failure)

    return await call_next(request)
