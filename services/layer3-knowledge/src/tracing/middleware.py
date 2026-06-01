"""FastAPI tracing middleware and integration.

This module uses the OpenTelemetry SDK directly for distributed tracing.
It integrates with the platform-wide OTel infrastructure (Jaeger, Tempo,
OTLP receivers) and correlates with L1/L4 spans in a standard OTel backend.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from opentelemetry import propagate, trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import SpanContext as OTelSpanContext
from opentelemetry.trace import SpanKind as OTelSpanKind
from opentelemetry.trace import Status, StatusCode, TraceFlags
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from value_fabric.shared.observability.trace_context import canonical_trace_headers
from value_fabric.shared.observability.tracing_contract import (
    build_trace_attributes,
    span_name,
)

from logging_config import get_logger

logger = get_logger(__name__)

_otel_tracer = trace.get_tracer(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add distributed tracing to FastAPI requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing."""
        parent_ctx = propagate.extract(dict(request.headers))
        token = attach(parent_ctx)

        request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
        correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID")

        attributes = build_trace_attributes(
            tenant_id=getattr(request.state, "tenant_id", None),
            request_id=request_id,
            service="layer3-knowledge",
            layer="L3",
            route=request.url.path,
            extras={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.path": request.url.path,
                "http.query": request.url.query,
                "http.user_agent": request.headers.get("User-Agent", ""),
                "http.remote_addr": request.client.host if request.client else "",
            },
        )
        if request.url.port is not None:
            attributes["http.port"] = request.url.port
        if request_id:
            attributes["http.request_id"] = request_id
        if correlation_id:
            attributes["http.correlation_id"] = correlation_id

        span = _otel_tracer.start_span(
            name=span_name(request.method, request.url.path),
            context=parent_ctx,
            attributes=attributes,
        )

        request.state.span = span
        request.state.trace_context = span.get_span_context()
        logger.info(
            "request_tracing_started",
            extra={"request_id": request_id, "correlation_id": correlation_id},
        )

        try:
            # Process request
            response = await call_next(request)

            # Record response attributes
            span.set_attributes(
                {
                    "http.status_code": response.status_code,
                    "http.response_size": len(response.body)
                    if hasattr(response, "body")
                    else 0,
                }
            )

            # Set span status based on response
            if response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                span.set_attribute("error_code", f"http_{response.status_code}")
            else:
                span.set_status(Status(StatusCode.OK))

            # Add trace headers to response
            self._add_trace_headers(response, span.get_span_context())

            return response

        except Exception as exc:
            # Record exception
            span.record_exception(exc)
            span.set_attributes(
                {
                    "error.type": type(exc).__name__,
                    "error.message": "request_failed",
                    "error_code": type(exc).__name__,
                }
            )
            span.set_status(Status(StatusCode.ERROR, "request_failed"))

            # Re-raise the exception
            raise

        finally:
            # End the span
            span.end()
            detach(token)
            logger.info(
                "request_tracing_finished",
                extra={"request_id": request_id, "correlation_id": correlation_id},
            )

    def _add_trace_headers(self, response: Response, trace_context: OTelSpanContext) -> None:
        """Add trace context headers to response.

        Args:
            response: HTTP response
            trace_context: Trace context
        """
        headers = response.headers
        trace_id = format(trace_context.trace_id, "032x")
        for header, value in canonical_trace_headers(trace_id).items():
            headers[header] = value
        headers["X-Span-Id"] = format(trace_context.span_id, "016x")
        headers["X-Trace-Sampled"] = str(bool(trace_context.trace_flags & TraceFlags.SAMPLED)).lower()


class StreamingResponseTracer:
    """Helper for tracing streaming responses."""

    @staticmethod
    def trace_streaming_response(
        response: StreamingResponse, span: trace.Span, total_size: int | None = None
    ) -> StreamingResponse:
        """Wrap streaming response to add tracing.

        Args:
            response: Streaming response
            span: Current OTel span
            total_size: Expected total size

        Returns:
            Traced streaming response
        """
        original_stream = response.body_iterator

        async def traced_stream():
            bytes_sent = 0
            try:
                async for chunk in original_stream():
                    bytes_sent += len(chunk)
                    yield chunk
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            finally:
                span.set_attributes(
                    {
                        "http.response_size": bytes_sent,
                        "http.stream_complete": True,
                    }
                )

                if total_size:
                    span.set_attributes(
                        {
                            "http.expected_size": total_size,
                            "http.size_ratio": bytes_sent / total_size
                            if total_size > 0
                            else 0,
                        }
                    )

        response.body_iterator = traced_stream()
        return response


def add_span_attributes(attributes: dict[str, Any]) -> Callable:
    """Decorator to add attributes to current OTel span.

    Args:
        attributes: Attributes to add

    Returns:
        Decorated function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            span = trace.get_current_span()
            if span:
                span.set_attributes(attributes)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> Callable:
    """Decorator to add event to current OTel span.

    Args:
        name: Event name
        attributes: Event attributes

    Returns:
        Decorated function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            span = trace.get_current_span()
            if span:
                span.add_event(name, attributes)
            return func(*args, **kwargs)

        return wrapper

    return decorator


class DatabaseTracer:
    """Helper for tracing database operations using OpenTelemetry."""

    @staticmethod
    def trace_query(
        query: str,
        database: str,
        operation: str = "query",
    ) -> trace.Span:
        """Trace a database query.

        Args:
            query: Database query
            database: Database name
            operation: Operation type

        Returns:
            OTel span (caller must end it)
        """
        sanitized_query = query[:200] + "..." if len(query) > 200 else query
        return _otel_tracer.start_span(
            name=f"{database}.{operation}",
            kind=OTelSpanKind.CLIENT,
            attributes={
                "db.system": database,
                "db.operation": operation,
                "db.statement": sanitized_query,
                "db.query_type": operation.upper(),
            },
        )

    @staticmethod
    def trace_query_result(span: trace.Span, result_count: int, duration_ms: float) -> None:
        """Record query result in span.

        Args:
            span: Query span
            result_count: Number of results
            duration_ms: Query duration in milliseconds
        """
        span.set_attributes(
            {
                "db.rows_affected": result_count,
                "db.duration_ms": duration_ms,
                "db.success": True,
            }
        )

    @staticmethod
    def trace_query_error(span: trace.Span, error: Exception) -> None:
        """Record query error in span.

        Args:
            span: Query span
            error: Exception that occurred
        """
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.set_attributes(
            {
                "db.success": False,
                "db.error_type": type(error).__name__,
            }
        )
        span.end()


class CacheTracer:
    """Helper for tracing cache operations using OpenTelemetry."""

    @staticmethod
    def trace_cache_operation(
        operation: str,
        cache_type: str,
        key: str,
    ) -> trace.Span:
        """Trace a cache operation.

        Args:
            operation: Operation type (get, set, delete)
            cache_type: Cache type (redis, memory)
            key: Cache key

        Returns:
            OTel span (caller must end it)
        """
        return _otel_tracer.start_span(
            name=f"cache.{operation}",
            kind=OTelSpanKind.CLIENT,
            attributes={
                "cache.system": cache_type,
                "cache.operation": operation,
                "cache.key": key[:100] + "..." if len(key) > 100 else key,
            },
        )

    @staticmethod
    def trace_cache_hit(span: trace.Span, hit: bool) -> None:
        """Record cache hit/miss in span.

        Args:
            span: Cache span
            hit: Whether cache hit occurred
        """
        span.set_attributes(
            {
                "cache.hit": hit,
                "cache.miss": not hit,
            }
        )

    @staticmethod
    def trace_cache_size(span: trace.Span, size_bytes: int) -> None:
        """Record cache size in span.

        Args:
            span: Cache span
            size_bytes: Cache size in bytes
        """
        span.set_attributes(
            {
                "cache.size_bytes": size_bytes,
            }
        )


class ExternalServiceTracer:
    """Helper for tracing external service calls using OpenTelemetry."""

    @staticmethod
    def trace_http_request(
        method: str,
        url: str,
        service_name: str,
    ) -> trace.Span:
        """Trace an HTTP request to external service.

        Args:
            method: HTTP method
            url: Request URL
            service_name: Target service name

        Returns:
            OTel span (caller must end it)
        """
        return _otel_tracer.start_span(
            name=f"{service_name}.{method.lower()}",
            kind=OTelSpanKind.CLIENT,
            attributes={
                "http.method": method,
                "http.url": url,
                "http.scheme": url.split("://")[0] if "://" in url else "",
                "http.target": url.split("://")[-1] if "://" in url else url,
                "peer.service": service_name,
                "peer.address": url,
            },
        )

    @staticmethod
    def trace_http_response(span: trace.Span, status_code: int, response_size: int) -> None:
        """Record HTTP response in span.

        Args:
            span: HTTP span
            status_code: Response status code
            response_size: Response size in bytes
        """
        span.set_attributes(
            {
                "http.status_code": status_code,
                "http.response_size": response_size,
            }
        )

        if status_code >= 400:
            span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end()


class BusinessLogicTracer:
    """Helper for tracing business logic operations using OpenTelemetry."""

    @staticmethod
    def trace_search_operation(
        query: str,
        search_type: str,
        result_count: int,
        duration_ms: float,
    ) -> trace.Span:
        """Trace a search operation.

        Args:
            query: Search query
            search_type: Type of search
            result_count: Number of results
            duration_ms: Operation duration

        Returns:
            OTel span (already ended)
        """
        with _otel_tracer.start_as_current_span(
            name=f"search.{search_type}",
            kind=OTelSpanKind.INTERNAL,
            attributes={
                "search.query": query[:100] + "..." if len(query) > 100 else query,
                "search.type": search_type,
                "search.result_count": result_count,
                "search.duration_ms": duration_ms,
            },
        ) as span:
            return span

    @staticmethod
    def trace_ingestion_operation(
        source_id: str,
        entities_processed: int,
        relationships_processed: int,
        duration_ms: float,
    ) -> trace.Span:
        """Trace an ingestion operation.

        Args:
            source_id: Source document ID
            entities_processed: Number of entities processed
            relationships_processed: Number of relationships processed
            duration_ms: Operation duration

        Returns:
            OTel span (already ended)
        """
        with _otel_tracer.start_as_current_span(
            name="ingestion.process",
            kind=OTelSpanKind.INTERNAL,
            attributes={
                "ingestion.source_id": source_id,
                "ingestion.entities_processed": entities_processed,
                "ingestion.relationships_processed": relationships_processed,
                "ingestion.duration_ms": duration_ms,
                "ingestion.total_items": entities_processed + relationships_processed,
            },
        ) as span:
            return span


# FastAPI dependencies
def get_current_span_dependency():
    """FastAPI dependency to get current span.

    Returns:
        Current OTel span or None
    """

    def dependency(request: Request) -> trace.Span | None:
        return getattr(request.state, "span", None)

    return dependency


def get_trace_context_dependency():
    """FastAPI dependency to get current trace context.

    Returns:
        Current OTel span context or None
    """

    def dependency(request: Request) -> OTelSpanContext | None:
        return getattr(request.state, "trace_context", None)

    return dependency


def get_trace_id_dependency():
    """FastAPI dependency to get current trace ID.

    Returns:
        Current trace ID hex string or None
    """

    def dependency(request: Request) -> str | None:
        span = getattr(request.state, "span", None)
        if span is None:
            return None
        sc = span.get_span_context()
        return format(sc.trace_id, "032x") if sc.is_valid else None

    return dependency
