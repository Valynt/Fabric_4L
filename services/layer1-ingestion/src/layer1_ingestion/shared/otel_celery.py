"""OpenTelemetry trace-context propagation for Celery tasks.

Manually injects/extracts trace context because opentelemetry-instrumentation-celery
is not installed.  Keeps the dependency surface minimal while preserving distributed
trace continuity across L1 pipeline stages and L1→L2 dispatches.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind

_TRACER = trace.get_tracer(__name__)
_OTEL_CONTEXT_KEY = "__otel_trace_context"


def get_trace_headers() -> dict[str, str]:
    """Return current OTel trace context as a serialisable carrier dict."""
    carrier: dict[str, str] = {}
    inject(carrier)
    return carrier


def build_celery_options() -> dict[str, Any]:
    """Build Celery ``apply_async`` options dict with injected trace context.

    Typical usage at dispatch time (inside a FastAPI request handler):

        process_scraping_job.apply_async(
            args=[str(job.id), str(job.tenant_id)],
            **build_celery_options(),
        )
    """
    carrier = get_trace_headers()
    if carrier:
        return {"headers": {_OTEL_CONTEXT_KEY: carrier}}
    return {}


def _extract_from_celery_task(task: Any) -> Any:
    """Extract OTel context from a bound Celery task's request headers."""
    request = getattr(task, "request", None)
    if request is None:
        return None
    headers = getattr(request, "headers", None) or {}
    carrier = headers.get(_OTEL_CONTEXT_KEY)
    if carrier:
        return extract(carrier)
    return None


@contextlib.contextmanager
def start_celery_span(
    task: Any,
    name: str,
    *,
    kind: SpanKind = SpanKind.CONSUMER,
    attributes: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Start a span parenting the trace context carried in a Celery task request.

    Typical usage at the top of a Celery task:

        @celery_app.task(bind=True)
        def my_task(self, job_id, tenant_id):
            with start_celery_span(self, "l1.pipeline.compliance_check") as span:
                span.set_attribute("job_id", job_id)
                ...
    """
    parent_context = _extract_from_celery_task(task)
    with _TRACER.start_as_current_span(
        name,
        context=parent_context,
        kind=kind,
        attributes=attributes,
    ) as span:
        yield span
