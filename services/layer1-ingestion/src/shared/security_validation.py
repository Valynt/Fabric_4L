"""Security validation and redaction helpers for connector configuration payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:secret|password|passwd|token|api[_-]?key|private[_-]?key|client[_-]?secret|access[_-]?key|auth|credential)",
    re.IGNORECASE,
)
CREDENTIAL_REF_PATTERN = re.compile(r"^(vault|aws-sm|gcp-sm|azure-kv)://[A-Za-z0-9][A-Za-z0-9._\-/]{2,254}$")
REDACTED = "[REDACTED]"


def is_valid_credential_reference(value: str) -> bool:
    return bool(CREDENTIAL_REF_PATTERN.match(value))


def contains_inline_secret_material(payload: Any) -> bool:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if isinstance(key, str) and SENSITIVE_KEY_PATTERN.search(key):
                if _is_non_empty_secret_value(value):
                    return True
            if contains_inline_secret_material(value):
                return True
        return False
    if isinstance(payload, Sequence) and not isinstance(payload, str | bytes | bytearray):
        return any(contains_inline_secret_material(item) for item in payload)
    return False


def sanitize_for_logging(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        redacted: dict[Any, Any] = {}
        for key, value in payload.items():
            if isinstance(key, str) and SENSITIVE_KEY_PATTERN.search(key):
                redacted[key] = REDACTED
            else:
                redacted[key] = sanitize_for_logging(value)
        return redacted
    if isinstance(payload, list):
        return [sanitize_for_logging(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(sanitize_for_logging(item) for item in payload)
    return payload


def redact_log_event_data(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return sanitize_for_logging(event_dict)


def _is_non_empty_secret_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
