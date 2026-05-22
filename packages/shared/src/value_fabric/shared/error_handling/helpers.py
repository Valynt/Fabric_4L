"""Shared helper utilities for API error payloads."""

from __future__ import annotations

from typing import Any


def build_error_detail(
    *,
    message: str,
    error_code: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable error detail envelope for HTTPException payloads."""
    payload: dict[str, Any] = {
        "message": message,
        "error_code": error_code,
        "request_id": request_id,
        "correlation_id": correlation_id or request_id,
    }
    if extra:
        payload.update(extra)
    return payload
