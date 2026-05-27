"""Smoke test for Layer 2 structured logging configuration."""

import structlog

from layer2_extraction.logging_config import configure_structured_logging


def test_configure_structured_logging_does_not_raise():
    """Configuring structured logging must not raise."""
    configure_structured_logging()


def test_structured_logger_emits_event():
    """A configured logger must accept event keyword arguments."""
    configure_structured_logging()
    logger = structlog.get_logger("layer2.test")
    # Should not raise; output destination depends on pytest capture.
    logger.info("layer2_log_smoke", tenant_id="tenant-1", request_id="req-1")
