from __future__ import annotations

from typing import Any


class CRMError(Exception):
    """Base class for all CRM-boundary errors."""


class TransientError(CRMError):
    """Retryable failure: network blip, rate limit, 5xx, timeout."""


class AuthError(CRMError):
    """Credential failure or expired token (401 / invalid_grant)."""


class PermissionError_(CRMError):
    """Authorized identity lacks permission (403)."""


class MappingError(CRMError):
    """Provider response could not be mapped to the canonical shape."""


class PermanentError(CRMError):
    """Non-retryable failure: bad request, malformed ID, not found, validation."""


class IntegrityGateOpenError(CRMError):
    """Raised when CRM sync precondition integrity checks fail."""

    def __init__(self, detail: dict[str, Any]):
        super().__init__(detail.get("message", "INTEGRITY_GATE_OPEN"))
        self.detail = detail


def classify_http_status(status_code: int, message: str = "") -> CRMError:
    """Map an HTTP status code to the CRM error taxonomy.

    This is a pure classification helper; it does not raise. Callers decide
    whether to propagate, retry, or surface the returned error.
    """
    text = message[:200]
    if status_code == 401:
        return AuthError(text)
    if status_code == 403:
        return PermissionError_(text)
    if status_code in (400, 404, 422):
        return PermanentError(text)
    # 429, 5xx, and any other HTTP failure are treated as transient.
    return TransientError(text)


def classify_httpx_exception(exc: Exception) -> CRMError:
    """Translate an httpx (or httpx-like) exception into the CRM error taxonomy.

    This is a pure classification helper; it does not raise. Callers decide
    whether to propagate, retry, or surface the returned error.
    """
    try:
        import httpx
    except ImportError:  # pragma: no cover - defensive for unusual import contexts
        return TransientError(str(exc))

    if isinstance(exc, httpx.HTTPStatusError):
        response = getattr(exc, "response", None)
        status = response.status_code if response is not None else 0
        return classify_http_status(status, str(exc))

    if isinstance(exc, httpx.TimeoutException):
        return TransientError(str(exc))

    if isinstance(exc, httpx.RequestError):
        return TransientError(str(exc))

    return PermanentError(str(exc))
