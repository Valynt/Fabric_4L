"""Common tracing instrumentation contract helpers.

Defines canonical span naming and required attribute keys for all services.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REQUIRED_TRACE_ATTRIBUTES: tuple[str, ...] = (
    "tenant_id",
    "request_id",
    "service",
    "layer",
    "route",
    "error_code",
)


class _NoOpSpan:
    def end(self, *args: object, **kwargs: object) -> None:
        return None

    def set_attribute(self, *args: object, **kwargs: object) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _NoOpTracer:
    def start_span(self, name: str, *args: object, **kwargs: object) -> _NoOpSpan:
        return _NoOpSpan()

    def start_as_current_span(self, name: str, *args: object, **kwargs: object) -> _NoOpSpan:
        return _NoOpSpan()


def get_tracer(module_name: str, *, service: str | None = None) -> object:
    """Return a tracer instance for a module/service. No-op when SDK is missing."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(service or module_name)
    except ImportError:
        return _NoOpTracer()


def span_name(http_method: str, route: str) -> str:
    """Build canonical HTTP span name."""
    return f"{http_method.upper()} {route}"


def build_trace_attributes(
    *,
    tenant_id: str | None,
    request_id: str | None,
    service: str,
    layer: str,
    route: str,
    error_code: str | None = None,
    extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical required tracing attributes with optional extras."""
    attributes: dict[str, Any] = {
        "tenant_id": tenant_id or "unknown",
        "request_id": request_id or "unknown",
        "service": service,
        "layer": layer,
        "route": route,
        "error_code": error_code or "none",
    }
    if extras:
        attributes.update(extras)
    return attributes


def missing_required_attributes(attributes: Mapping[str, Any]) -> list[str]:
    """Return missing required attribute keys."""
    return [key for key in REQUIRED_TRACE_ATTRIBUTES if key not in attributes]


assert_required_attributes = missing_required_attributes
