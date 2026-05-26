"""Layer 5 structured logging helpers aligned to platform contract."""

from __future__ import annotations

import contextvars
import logging
import sys
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request

_tenant_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)
_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def _add_request_context(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    if (tenant_id := _tenant_id_ctx.get()):
        event_dict.setdefault("tenant_id", tenant_id)
    if (request_id := _request_id_ctx.get()):
        event_dict.setdefault("request_id", request_id)
        event_dict.setdefault("correlation_id", request_id)
    return event_dict


def configure_structured_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


def set_request_log_context(request: Request) -> None:
    request_id = getattr(request.state, "trace_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    tenant_id = request.headers.get("X-Tenant-ID") or getattr(getattr(request.state, "governance_context", None), "tenant_id", None)
    _request_id_ctx.set(str(request_id))
    _tenant_id_ctx.set(str(tenant_id) if tenant_id else None)


def clear_request_log_context() -> None:
    _request_id_ctx.set(None)
    _tenant_id_ctx.set(None)


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
