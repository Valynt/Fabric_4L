"""Structured logging configuration for API Gateway."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from value_fabric.shared.security.redaction import install_redaction_filter, redaction_processor


def _merge_request_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Merge per-request logging context (request_id, tenant_id, etc.) into event dict."""
    try:
        from value_fabric.shared.observability.request_context import (
            logging_context_dict,
        )

        event_dict.update(logging_context_dict())
    except Exception:  # noqa: BLE001
        pass
    return event_dict


def configure_structured_logging() -> None:
    """Configure JSON structured logs for API gateway."""
    install_redaction_filter()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _merge_request_context,
            redaction_processor,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    install_redaction_filter()
