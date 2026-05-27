"""Shared structured logging compatibility helpers."""

from __future__ import annotations

import structlog
from value_fabric.shared.observability.request_context import logging_context_dict


def get_logger(name: str | None = None):
    """Return a structlog logger using the repository-standard logging facade."""
    return structlog.get_logger(name) if name else structlog.get_logger()


def enrich_event_with_logging_context(_, __, event_dict: dict) -> dict:
    """Attach shared request/correlation context fields when available."""
    for key, value in logging_context_dict().items():
        event_dict.setdefault(key, value)
    return event_dict
