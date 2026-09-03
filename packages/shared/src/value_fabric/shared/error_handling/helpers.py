"""Shared helper utilities for API error payloads."""

from __future__ import annotations

import re
from typing import Any

# Matches URL userinfo like ``scheme://user:pass@host`` or ``scheme://user@host``
# so broker/database credentials embedded in connection errors are never logged.
_URL_USERINFO_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s]*@")


def sanitize_log_error(error: BaseException | str, /) -> str:
    """Remove potential secrets from error strings before logging.

    Scrubbable patterns:
      - Bearer tokens
      - access_token / refresh_token
      - api_key
    """
    redacted = repr(error) if isinstance(error, BaseException) else error  # ban-str-e-allow: sanitization-helper
    lowered = redacted.lower()
    for pattern, label in (
        ("bearer ", "bearer"),
        ("access_token", "access_token"),
        ("refresh_token", "refresh_token"),
        ("api_key", "api_key"),
    ):
        if pattern in lowered:
            return f"[REDACTED: contains {label}]"
    return _URL_USERINFO_RE.sub(r"\1***@", redacted)


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


