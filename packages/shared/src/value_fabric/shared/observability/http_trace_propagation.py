"""HTTP trace-context propagation helpers for inter-service clients.

Wraps OpenTelemetry's propagator so that synchronous and async HTTP clients
can inject the current trace context into outgoing request headers without
duplicating OTel boilerplate in every adapter.
"""

from __future__ import annotations

from typing import Any


def inject_trace_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Return a headers dict enriched with the current OTel trace context.

    Usage (httpx / requests):
        response = client.post(url, json=payload, headers=inject_trace_headers({"Authorization": "Bearer x"}))
    """
    result: dict[str, str] = dict(headers) if headers else {}
    try:
        from opentelemetry.propagate import inject
        inject(result)
    except Exception:
        # OTel not configured or unavailable — continue without propagation
        pass
    return result


def merge_trace_headers(base_headers: dict[str, str]) -> dict[str, str]:
    """In-place variant: mutate *base_headers* with current trace context.

    Safe to call even when OpenTelemetry is not installed or not active.
    """
    try:
        from opentelemetry.propagate import inject
        inject(base_headers)
    except Exception:
        pass
    return base_headers
