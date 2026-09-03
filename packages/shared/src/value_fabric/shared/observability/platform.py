"""Shared observability platform client.

Services import this module instead of initializing OpenTelemetry themselves.
Missing OTLP endpoint or SDK is a no-op — startup must not crash.
"""

from __future__ import annotations

import math
import os
from contextvars import ContextVar
from dataclasses import dataclass

SERVICE_NAMESPACE = "fabric4l"


@dataclass(frozen=True)
class ObservabilityContext:
    request_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    tenant_id: str | None = None


DEFAULT_SAMPLE_RATIO = 0.01


@dataclass(frozen=True)
class PlatformTelemetry:
    provider: object | None
    service_name: str
    layer: str | None = None
    sample_ratio: float | None = None


_context: ContextVar[ObservabilityContext | None] = ContextVar(
    "observability_platform_context",
    default=None,
)


def bind_context(
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    tenant_id: str | None = None,
) -> ObservabilityContext:
    """Bind request/trace identifiers for logs, metrics labels, and audit."""
    ctx = ObservabilityContext(
        request_id=request_id,
        trace_id=trace_id,
        span_id=span_id,
        tenant_id=tenant_id,
    )
    _context.set(ctx)
    return ctx


def clear_context() -> None:
    _context.set(None)


def get_context() -> ObservabilityContext:
    return _context.get() or ObservabilityContext()


def _span_ids() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        span_ctx = span.get_span_context()
        if span_ctx is None or not getattr(span_ctx, "is_valid", False):
            return None, None
        return format(span_ctx.trace_id, "032x"), format(span_ctx.span_id, "016x")
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return None, None


def correlation_fields() -> dict[str, str]:
    """Stable, low-cardinality identifiers for logs and audit details."""
    bound = get_context()
    span_trace_id, span_span_id = _span_ids()
    fields: dict[str, str] = {}
    request_id = bound.request_id or bound.trace_id or span_trace_id
    trace_id = bound.trace_id or span_trace_id
    span_id = bound.span_id or span_span_id
    if request_id:
        fields["request_id"] = request_id
    if trace_id:
        fields["trace_id"] = trace_id
    if span_id:
        fields["span_id"] = span_id
    if bound.tenant_id:
        fields["tenant_id"] = bound.tenant_id
    return fields


def _shutdown_provider(provider: object | None) -> None:
    shutdown = getattr(provider, "shutdown", None)
    if not callable(shutdown):
        return
    try:
        shutdown()
    except Exception:  # noqa: BLE001 — fail-closed shutdown
        return


def _otlp_traces_endpoint(raw: str | None) -> str:
    endpoint = (raw or "").strip().rstrip("/")
    if endpoint.endswith("/v1/traces"):
        return endpoint
    return f"{endpoint}/v1/traces"


def _parse_sample_ratio() -> float:
    raw = os.getenv("OTEL_SAMPLE_RATIO", str(DEFAULT_SAMPLE_RATIO))
    try:
        ratio = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_SAMPLE_RATIO
    if math.isnan(ratio) or ratio < 0.0 or ratio > 1.0:
        return DEFAULT_SAMPLE_RATIO
    return ratio


def configure_platform(
    service_name: str,
    *,
    service_version: str | None = None,
    layer: str | None = None,
    endpoint: str | None = None,
) -> PlatformTelemetry:
    """Install the process TracerProvider once. No-op when export is unavailable."""
    raw_endpoint = endpoint if endpoint is not None else os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_endpoint = (raw_endpoint or "").strip()

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
    except ImportError:
        return PlatformTelemetry(provider=None, service_name=service_name, layer=layer)

    sample_ratio = _parse_sample_ratio()
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        return PlatformTelemetry(
            provider=current,
            service_name=service_name,
            layer=layer,
            sample_ratio=sample_ratio,
        )

    if not otel_endpoint:
        return PlatformTelemetry(provider=None, service_name=service_name, layer=layer)

    provider: TracerProvider | None = None
    try:
        attributes: dict[str, str] = {
            SERVICE_NAME: service_name,
            "service.namespace": SERVICE_NAMESPACE,
        }
        if layer:
            attributes["service.layer"] = layer
        if service_version:
            attributes["service.version"] = service_version
        environment = os.getenv("DEPLOYMENT_ENVIRONMENT") or os.getenv("ENVIRONMENT")
        if environment:
            attributes["deployment.environment"] = environment

        resource = Resource.create(attributes)
        sampler = ParentBasedTraceIdRatio(sample_ratio)
        provider = TracerProvider(resource=resource, sampler=sampler)
        exporter = OTLPSpanExporter(endpoint=_otlp_traces_endpoint(otel_endpoint))
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        installed = trace.get_tracer_provider()
        if installed is not provider:
            _shutdown_provider(provider)
            return PlatformTelemetry(
                provider=installed if isinstance(installed, TracerProvider) else None,
                service_name=service_name,
                layer=layer,
                sample_ratio=sample_ratio,
            )
        return PlatformTelemetry(
            provider=provider,
            service_name=service_name,
            layer=layer,
            sample_ratio=sample_ratio,
        )
    except Exception:  # noqa: BLE001 — startup must not crash on exporter/SDK errors
        _shutdown_provider(provider)
        return PlatformTelemetry(
            provider=None,
            service_name=service_name,
            layer=layer,
            sample_ratio=sample_ratio,
        )


def instrument_fastapi_app(app: object, *, enabled: bool) -> bool:
    if not enabled:
        return False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # noqa: BLE001 — instrumentation is optional at startup
        return False
    return True
