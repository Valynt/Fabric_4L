"""Shared observability utilities (path normalization, probes, middleware).

These helpers are reused across all layers (L1–L6) to avoid drift in metric
cardinality controls and `/metrics` endpoint authorization.
"""

from .correlation import (
    CANONICAL_CORRELATION_HEADERS,
    CORRELATION_ID_HEADER,
    LOG_FIELD_CORRELATION_ID,
    LOG_FIELD_TRACE_ID,
    REQUEST_ID_HEADER,
    REQUEST_STATE_CORRELATION_ID_KEY,
    REQUEST_STATE_TRACE_ID_KEY,
)
from .metrics_access import is_internal_ip, verify_metrics_access
from .path_normalization import PathNormalizer
from .platform import (
    ObservabilityContext,
    PlatformTelemetry,
    bind_context,
    clear_context,
    configure_platform,
    correlation_fields,
    get_context,
    instrument_fastapi_app,
)
from .probes import configure_observability
from .sentry_init import init_sentry
from .trace_context import (
    ALL_TRACE_HEADERS,
    CANONICAL_TRACE_HEADER,
    TRACE_HEADER_ALIASES,
    canonical_trace_headers,
    resolve_trace_context,
)
from .tracing_contract import (
    REQUIRED_TRACE_ATTRIBUTES,
    build_trace_attributes,
    get_tracer,
    span_name,
)

__all__ = [
    "ALL_TRACE_HEADERS",
    "CANONICAL_CORRELATION_HEADERS",
    "CANONICAL_TRACE_HEADER",
    "CORRELATION_ID_HEADER",
    "LOG_FIELD_CORRELATION_ID",
    "LOG_FIELD_TRACE_ID",
    "REQUEST_ID_HEADER",
    "REQUEST_STATE_CORRELATION_ID_KEY",
    "REQUEST_STATE_TRACE_ID_KEY",
    "REQUIRED_TRACE_ATTRIBUTES",
    "TRACE_HEADER_ALIASES",
    "ObservabilityContext",
    "PathNormalizer",
    "PlatformTelemetry",
    "bind_context",
    "build_trace_attributes",
    "canonical_trace_headers",
    "clear_context",
    "configure_observability",
    "configure_platform",
    "correlation_fields",
    "get_context",
    "get_tracer",
    "init_sentry",
    "instrument_fastapi_app",
    "is_internal_ip",
    "resolve_trace_context",
    "span_name",
    "verify_metrics_access",
]
