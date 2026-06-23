"""OpenTelemetry instrumentation for PlaywrightCrawler.

Provides distributed tracing for crawl operations, following the patterns
established in Layer 4 agent tracing (per AGENTS.md).
"""

from collections.abc import Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace import Span, Status, StatusCode
from value_fabric.shared.models.typed_dict import TypedDictModel


class CrawlMetrics_to_dictResult(TypedDictModel):
    avg_duration_ms: Any
    blocked_resources: Any
    count: Any
    error_rate: Any
    errors: Any
    rate_limit_delays: Any

logger = structlog.get_logger()

# Global tracer provider
trace_provider: TracerProvider | None = None
_tracer = None


def init_telemetry(
    service_name: str = "layer1-crawler",
    service_version: str = "1.0.0",
    attributes: dict | None = None,
) -> TracerProvider:
    """Initialize OpenTelemetry tracer provider.

    Args:
        service_name: Name of the service for traces
        service_version: Service version
        attributes: Additional resource attributes

    Returns:
        Configured TracerProvider
    """
    global trace_provider, _tracer

    resource_attrs = {
        "service.name": service_name,
        "service.version": service_version,
    }
    if attributes:
        resource_attrs.update(attributes)

    resource = Resource.create(resource_attrs)

    # Use OTLP exporter when OTEL_EXPORTER_OTLP_ENDPOINT is configured.
    # Fall back to ConsoleSpanExporter in development/test environments only.
    # A misconfigured production pod (missing endpoint) will log a warning so
    # the gap is visible in logs rather than silently dropping traces.
    import os as _os
    sample_ratio = float(_os.getenv("OTEL_SAMPLE_RATIO", "0.01"))
    sampler = ParentBasedTraceIdRatio(sample_ratio)
    provider = TracerProvider(resource=resource, sampler=sampler)
    otlp_endpoint = _os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        logger.info(
            "Telemetry using OTLP exporter",
            service=service_name,
            endpoint=otlp_endpoint,
        )
    else:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        exporter = ConsoleSpanExporter()
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set — traces written to stdout only. "
            "Set this variable in production to send traces to an OTel collector.",
            service=service_name,
        )

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    trace_provider = provider
    _tracer = trace.get_tracer(__name__)

    logger.info("Telemetry initialized", service=service_name, version=service_version)
    return provider


def get_tracer():
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


@contextmanager
def start_crawl_span(
    url: str, operation: str = "crawl_url", parent_context: trace.SpanContext | None = None
) -> Generator[Span, None, None]:
    """Context manager for crawl operation tracing.

    Args:
        url: URL being crawled
        operation: Operation name for the span
        parent_context: Optional parent span context for distributed tracing

    Yields:
        Active Span instance
    """
    tracer = get_tracer()

    # Extract domain for additional context
    from urllib.parse import urlparse

    domain = urlparse(url).netloc

    with tracer.start_as_current_span(
        name=operation,
        context=parent_context,
        attributes={
            "crawl.url": url,
            "crawl.domain": domain,
            "crawl.operation": operation,
        },
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, "CRAWL_OPERATION_ERROR"))
            span.record_exception(e)
            raise


@contextmanager
def start_batch_span(url_count: int, operation: str = "crawl_urls") -> Generator[Span, None, None]:
    """Context manager for batch crawl operation tracing.

    Args:
        url_count: Number of URLs in the batch
        operation: Operation name for the span

    Yields:
        Active Span instance
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(
        name=operation,
        attributes={
            "crawl.batch_size": url_count,
            "crawl.operation": operation,
        },
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, "CRAWL_OPERATION_ERROR"))
            span.record_exception(e)
            raise


def trace_method(operation_name: str | None = None):
    """Decorator to add tracing to async methods.

    Args:
        operation_name: Custom operation name (defaults to method name)

    Usage:
        @trace_method("custom_operation")
        async def my_method(self, url: str):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            tracer = get_tracer()

            with tracer.start_as_current_span(name) as span:
                # Add self attributes if available
                if args and hasattr(args[0], "__class__"):
                    span.set_attribute("method.class", args[0].__class__.__name__)
                span.set_attribute("method.name", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, "METHOD_ERROR"))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


class CrawlMetrics:
    """Metrics collector for crawler operations.

    Tracks key metrics: duration, blocked resources, scroll effectiveness,
    rate limit triggers, and success/failure rates.
    """

    def __init__(self):
        self._crawl_count = 0
        self._error_count = 0
        self._total_duration_ms = 0
        self._rate_limit_delays = 0
        self._blocked_resources_count = 0

    def record_crawl(
        self,
        duration_ms: int,
        success: bool,
        blocked_resources: int = 0,
        rate_limited: bool = False,
        scroll_triggered: bool = False,
    ):
        """Record a completed crawl operation."""
        self._crawl_count += 1
        self._total_duration_ms += duration_ms

        if not success:
            self._error_count += 1
        if rate_limited:
            self._rate_limit_delays += 1
        self._blocked_resources_count += blocked_resources

        # Log structured metrics
        logger.info(
            "crawl_completed",
            duration_ms=duration_ms,
            success=success,
            blocked_resources=blocked_resources,
            rate_limited=rate_limited,
            scroll_triggered=scroll_triggered,
        )

    @property
    def crawl_count(self) -> int:
        return self._crawl_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def error_rate(self) -> float:
        if self._crawl_count == 0:
            return 0.0
        return self._error_count / self._crawl_count

    @property
    def avg_duration_ms(self) -> float:
        if self._crawl_count == 0:
            return 0.0
        return self._total_duration_ms / self._crawl_count

    @property
    def rate_limit_rate(self) -> float:
        if self._crawl_count == 0:
            return 0.0
        return self._rate_limit_delays / self._crawl_count

    def to_dict(self) -> dict:
        """Export metrics as dictionary for telemetry."""
        return CrawlMetrics_to_dictResult.model_validate({
            "count": self._crawl_count,
            "errors": self._error_count,
            "error_rate": self.error_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "rate_limit_delays": self._rate_limit_delays,
            "blocked_resources": self._blocked_resources_count,
        }).model_dump()


