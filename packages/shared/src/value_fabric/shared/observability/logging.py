"""Shared structured logging compatibility helpers."""

from __future__ import annotations

import structlog

from value_fabric.shared.observability.correlation import (
    LOG_FIELD_CORRELATION_ID,
    LOG_FIELD_TRACE_ID,
)

_STRUCTLOG_CONFIGURED = False


def enrich_event_with_request_context(_, __, event_dict: dict) -> dict:
    """Ensure canonical request context fields are present on every event."""
    event_dict.setdefault(LOG_FIELD_TRACE_ID, None)
    event_dict.setdefault(LOG_FIELD_CORRELATION_ID, event_dict.get(LOG_FIELD_TRACE_ID))
    return event_dict


def configure_structlog() -> None:
    global _STRUCTLOG_CONFIGURED
    if _STRUCTLOG_CONFIGURED:
        return
    structlog.configure(
        processors=[
            enrich_event_with_request_context,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
    _STRUCTLOG_CONFIGURED = True


def get_logger(name: str | None = None):
    """Return a structlog logger using the repository-standard logging facade."""
    configure_structlog()
    return structlog.get_logger(name) if name else structlog.get_logger()
