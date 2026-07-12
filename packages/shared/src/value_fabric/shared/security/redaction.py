"""Credential and PII redaction helpers for logs and error messages.

The helpers in this module are intentionally small and dependency-free so they can
be used from any Fabric layer without crossing layer-specific API boundaries.
They are suitable for defensive rendering of exception messages before those
messages are logged, exposed through health details, or asserted by release gates.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED_VALUE = "[REDACTED]"
_SECRET_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth",
    "authorization",
    "client_secret",
    "key",
    "password",
    "secret",
    "token",
}
_SENSITIVE_FIELD_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "card_number",
    "client_secret",
    "cookie",
    "key_hash",
    "password",
    "payment_details",
    "private_key",
    "refresh_token",
    "secret",
    "session_token",
    "set-cookie",
    "token",
    "vf_session",
    "x-api-key",
}
_TOKEN_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9._-]{8,}\b"),
    re.compile(r"\b(?:sk|pk|rk|vf)_(?:live|test)_[A-Za-z0-9][A-Za-z0-9._-]{6,}\b", re.IGNORECASE),
    re.compile(r"\b(?:Bearer|Token)\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE),
    # Base64-encoded JWT tokens (typically 3 parts separated by dots)
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
]
# Pattern to catch KEY=value assignments where KEY is a sensitive field
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    rf"\b({'|'.join(_SECRET_QUERY_KEYS)}|jwt_secret|service_auth_secret|api_key|private_key|client_secret)=[^\s,)]+",
    re.IGNORECASE
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")
_URL_PATTERN = re.compile(r"https?://[^\s)\]}>\"']+")
_LOG_RECORD_BUILTINS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


def is_sensitive_key(key: object) -> bool:
    """Return whether a structured field name should be fully redacted."""

    normalized = str(key).strip().lower().replace("_", "-")
    normalized_underscore = normalized.replace("-", "_")
    return (
        normalized in _SENSITIVE_FIELD_KEYS
        or normalized_underscore in _SENSITIVE_FIELD_KEYS
        or "password" in normalized
        or "secret" in normalized
        or "token" in normalized
        or "private-key" in normalized
        or "api-key" in normalized
    )


def redact_credentials(message: object) -> str:
    """Return ``message`` with obvious credentials and PII redacted.

    The function preserves enough operational context for debugging, including
    host names and non-sensitive path segments, while removing query parameters
    and token-shaped substrings that commonly carry credentials. It also scrubs
    emails, phone numbers, SSNs, and credit card numbers from raw log messages.
    """

    rendered = str(message)
    rendered = _URL_PATTERN.sub(_redact_url_match, rendered)
    rendered = _EMAIL_PATTERN.sub(REDACTED_VALUE, rendered)
    rendered = _SSN_PATTERN.sub(REDACTED_VALUE, rendered)
    rendered = _PHONE_PATTERN.sub(REDACTED_VALUE, rendered)
    rendered = _CREDIT_CARD_PATTERN.sub(REDACTED_VALUE, rendered)
    # Redact secret assignments (e.g., JWT_SECRET=value)
    rendered = _SECRET_ASSIGNMENT_PATTERN.sub(lambda m: f"{m.group(1).split('=')[0]}={REDACTED_VALUE}", rendered)
    for pattern in _TOKEN_PATTERNS:
        rendered = pattern.sub(REDACTED_VALUE, rendered)
    return rendered


def redact_value(value: Any) -> Any:
    """Recursively redact sensitive values while preserving container shape."""

    if isinstance(value, Mapping):
        return {
            key: REDACTED_VALUE if is_sensitive_key(key) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, set):
        return {redact_value(item) for item in value}
    if isinstance(value, str):
        return redact_credentials(value)
    return value


def redaction_processor(_logger: logging.Logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Structlog processor that scrubs sensitive fields and raw message text."""

    redacted = redact_value(event_dict)
    return dict(redacted) if isinstance(redacted, Mapping) else event_dict


class RedactionFilter(logging.Filter):
    """Standard-library logging filter for raw messages, args, and extra fields."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_credentials(record.msg)
        if record.args:
            record.args = redact_value(record.args)

        for key, value in list(record.__dict__.items()):
            if key in _LOG_RECORD_BUILTINS:
                continue
            record.__dict__[key] = REDACTED_VALUE if is_sensitive_key(key) else redact_value(value)
        return True


def install_redaction_filter(logger: logging.Logger | None = None) -> RedactionFilter:
    """Install the shared redaction filter on ``logger`` and its handlers."""

    target = logger or logging.getLogger()
    filter_instance: RedactionFilter | None = None
    for existing in target.filters:
        if isinstance(existing, RedactionFilter):
            filter_instance = existing
            break
    if filter_instance is None:
        filter_instance = RedactionFilter()
        target.addFilter(filter_instance)

    for handler in target.handlers:
        if not any(isinstance(existing, RedactionFilter) for existing in handler.filters):
            handler.addFilter(filter_instance)
    return filter_instance


def _redact_url_match(match: re.Match[str]) -> str:
    return _redact_url(match.group(0))


def _redact_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return url

    if not parts.query:
        return url

    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in _SECRET_QUERY_KEYS:
            query.append((key, REDACTED_VALUE))
        else:
            query.append((key, redact_credentials(value)))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


__all__ = [
    "REDACTED_VALUE",
    "RedactionFilter",
    "install_redaction_filter",
    "is_sensitive_key",
    "redact_credentials",
    "redact_value",
    "redaction_processor",
]
