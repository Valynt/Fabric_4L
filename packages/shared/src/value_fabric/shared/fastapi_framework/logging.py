"""Structured logging configuration helper.

The shared framework exposes a single ``configure_structlog`` entrypoint so
services do not duplicate processor chains. When the ``structlog`` package is
unavailable in the runtime, this becomes a no-op (callers may still rely on
the standard library logger). This keeps PR1 backward compatible with services
that have not yet installed the dependency.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from value_fabric.shared.security.redaction import (
    REDACTED_VALUE,
    install_redaction_filter,
    is_sensitive_key,
    redaction_processor,
)


DEFAULT_REDACT_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "x-api-key",
        "api_key",
        "password",
        "secret",
        "token",
        "set-cookie",
        "cookie",
    }
)


@dataclass(frozen=True)
class StructuredLoggingConfig:
    """Configuration for structlog-based JSON logging.

    Defaults are conservative; enabling is opt-in per service to avoid silent
    log format changes during rollout.
    """

    enabled: bool = False
    level: str = "INFO"
    json_output: bool = True
    redact_keys: frozenset[str] = field(default_factory=lambda: DEFAULT_REDACT_KEYS)
    extra_processors: tuple[Any, ...] = ()
    service_name: str | None = None

    @classmethod
    def from_env(cls, *, service_name: str | None = None) -> StructuredLoggingConfig:
        enabled = os.getenv("FABRIC_STRUCTLOG_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        level = os.getenv("FABRIC_LOG_LEVEL", "INFO").upper()
        return cls(enabled=enabled, level=level, service_name=service_name)


def _redact_processor(redact_keys: Iterable[str]) -> Any:
    lowered = {k.lower() for k in redact_keys}

    def processor(_logger: logging.Logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        for key in list(event_dict.keys()):
            if key.lower() in lowered or is_sensitive_key(key):
                event_dict[key] = REDACTED_VALUE
        return redaction_processor(_logger, _method_name, event_dict)

    return processor


def configure_structlog(config: StructuredLoggingConfig) -> bool:
    """Apply structlog configuration if the dependency is installed.

    Returns ``True`` when configuration was applied, ``False`` when structlog
    is unavailable (callers should treat this as a soft failure).
    """

    if not config.enabled:
        return False

    try:
        import structlog
    except ImportError:
        return False

    level = getattr(logging, config.level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    install_redaction_filter()

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_processor(config.redact_keys),
    ]
    processors.extend(config.extra_processors)

    if config.service_name is not None:
        def _add_service(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
            event_dict.setdefault("service", config.service_name)
            return event_dict

        processors.append(_add_service)

    if config.json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    return True
