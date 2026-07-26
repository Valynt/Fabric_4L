"""Request logging context helpers for the governance middleware."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from .constants import TENANT_ID_HEADER


def _request_log_context(request: Request) -> dict[str, Any]:
    request_id = request.headers.get("X-Request-ID") or request.headers.get(
        "X-Correlation-ID"
    )
    return {
        "request_id": request_id,
        "correlation_id": request.headers.get("X-Correlation-ID"),
        "tenant_hint": request.headers.get(TENANT_ID_HEADER),
        "path": request.url.path,
        "method": request.method,
    }
