"""Tracing package initialization — OpenTelemetry-based."""

from ..tracing.middleware import (
    BusinessLogicTracer,
    CacheTracer,
    DatabaseTracer,
    ExternalServiceTracer,
    StreamingResponseTracer,
    TracingMiddleware,
    add_span_attributes,
    add_span_event,
    get_current_span_dependency,
    get_trace_context_dependency,
    get_trace_id_dependency,
)

__all__ = [
    # Middleware
    "TracingMiddleware",
    "StreamingResponseTracer",
    "add_span_attributes",
    "add_span_event",
    # Specialized tracers
    "DatabaseTracer",
    "CacheTracer",
    "ExternalServiceTracer",
    "BusinessLogicTracer",
    # FastAPI dependencies
    "get_current_span_dependency",
    "get_trace_context_dependency",
    "get_trace_id_dependency",
]
