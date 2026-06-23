"""Output formatting and secret redaction."""

from __future__ import annotations

import json
import re
from typing import Any

import click

from .context import ExecutionContext
from .errors import CliError

SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(token|api[_-]?key|authorization)(['\"]?\s*[:=]\s*['\"]?)[^,'\"\s}]+"),
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in {"token", "access_token", "refresh_token", "api_key", "authorization"}:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern in SECRET_PATTERNS:
            result = pattern.sub(lambda match: f"{match.group(1)}{match.group(2) if len(match.groups()) > 1 else ''}[REDACTED]", result)
        return result
    return value


def success_envelope(data: Any, *, context: ExecutionContext | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if context is not None:
        meta = {
            "tenant_id": context.tenant_id,
            "environment": context.environment,
            "request_id": context.request_id,
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        }
    return {"ok": True, "data": redact(data), "meta": meta}


def error_envelope(error: CliError, *, request_id: str | None = None) -> dict[str, Any]:
    meta = {"request_id": request_id} if request_id else {}
    return {
        "ok": False,
        "error": {
            "code": error.code,
            "message": redact(error.message),
            "retryable": error.retryable,
        },
        "meta": meta,
    }


def emit_json(payload: dict[str, Any], *, err: bool = False) -> None:
    click.echo(json.dumps(payload, sort_keys=True), err=err)


def emit_human_mapping(mapping: dict[str, Any], *, err: bool = False) -> None:
    for key, value in mapping.items():
        label = key.replace("_", " ").title()
        click.echo(f"{label + ':':<14} {redact(value)}", err=err)
