from __future__ import annotations

"""Layer 5 structured logging helpers aligned to platform contract."""


import contextvars
import logging
import sys
import uuid
from typing import Any

import structlog
from fastapi import Request
from value_fabric.shared.security.redaction import (
    install_redaction_filter,
    redaction_processor,
)

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
    install_redaction_filter()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_context,
            redaction_processor,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
    install_redaction_filter()


def set_request_log_context(request: Request) -> None:
    request_id = getattr(request.state, "trace_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    ctx = getattr(request.state, "governance_context", None) or getattr(request.state, "context", None)
    tenant_id = getattr(ctx, "tenant_id", None)
    _request_id_ctx.set(str(request_id))
    _tenant_id_ctx.set(str(tenant_id) if tenant_id else None)


def clear_request_log_context() -> None:
    _request_id_ctx.set(None)
    _tenant_id_ctx.set(None)


class _LoggerCompat:
    """Accept legacy log calls that pass both positional and keyword event."""

    def __init__(self, logger: Any) -> None:
        self._logger = logger

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._logger, name)
        if name not in {"debug", "info", "warning", "error", "critical", "exception"}:
            return attr

        def _log(*args: Any, **kwargs: Any) -> Any:
            if args and "event" in kwargs:
                kwargs = dict(kwargs)
                kwargs.pop("event", None)
            return attr(*args, **kwargs)

        return _log


def get_logger(name: str) -> Any:
    return _LoggerCompat(structlog.get_logger(name))
