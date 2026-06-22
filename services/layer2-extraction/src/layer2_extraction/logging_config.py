"""Structured logging configuration for Layer 2 extraction."""

from __future__ import annotations

import logging
import sys

import structlog
from value_fabric.shared.security.redaction import install_redaction_filter, redaction_processor


def configure_structured_logging() -> None:
    """Configure JSON structured logs for layer2."""
    install_redaction_filter()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
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
