from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from app.core.config import Settings, get_settings

SERVICE_NAME = "fabric_4l_api"

registry = CollectorRegistry()

REQUESTS_TOTAL = Counter(
    "fabric_api_http_requests_total",
    "Total HTTP requests handled by the standalone API.",
    ("method", "path", "status_code"),
    registry=registry,
)

REQUEST_LATENCY_SECONDS = Histogram(
    "fabric_api_http_request_duration_seconds",
    "HTTP request latency for the standalone API.",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry,
)

ERRORS_TOTAL = Counter(
    "fabric_api_http_errors_total",
    "Total HTTP 5xx responses handled by the standalone API.",
    ("method", "path", "status_code"),
    registry=registry,
)

DEPENDENCY_HEALTH = Gauge(
    "fabric_api_dependency_health",
    "Dependency/configuration health for the standalone API; 1 is healthy, 0 is unhealthy.",
    ("dependency",),
    registry=registry,
)

# --- Layer delegation observability (P4) -----------------------------------
# These cover the async reverse-proxy in routers/layer_delegation.py: every
# delegated request is counted by segment/method/status, latency is observed
# per segment, and circuit-open + retry events are surfaced separately so
# dashboards can distinguish "upstream slow" from "breaker tripped".

DELEGATION_REQUESTS_TOTAL = Counter(
    "fabric_api_delegation_requests_total",
    "Total delegated requests by owning-layer segment, method, and status.",
    ("segment", "method", "status_code", "outcome"),
    registry=registry,
)

DELEGATION_LATENCY_SECONDS = Histogram(
    "fabric_api_delegation_latency_seconds",
    "End-to-end latency for a delegated request, including retries.",
    ("segment", "method"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

DELEGATION_CIRCUIT_OPEN_TOTAL = Counter(
    "fabric_api_delegation_circuit_open_total",
    "Delegated requests rejected because the segment breaker was open.",
    ("segment",),
    registry=registry,
)

DELEGATION_RETRY_TOTAL = Counter(
    "fabric_api_delegation_retry_total",
    "Retry attempts issued by the delegation proxy (excludes the first try).",
    ("segment",),
    registry=registry,
)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path or request.url.path)


def update_dependency_health(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    database_healthy = settings.mock_persistence or bool(settings.database_url)
    llm_healthy = settings.llm_provider.lower() != "mock" or not settings.is_production_like
    DEPENDENCY_HEALTH.labels("database").set(1 if database_healthy else 0)
    DEPENDENCY_HEALTH.labels("llm").set(1 if llm_healthy else 0)


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    path = _route_path(request)
    method = request.method
    status_code = "500"
    error_recorded = False
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        ERRORS_TOTAL.labels(method, path, status_code).inc()
        error_recorded = True
        raise
    finally:
        duration = time.perf_counter() - start
        REQUESTS_TOTAL.labels(method, path, status_code).inc()
        REQUEST_LATENCY_SECONDS.labels(method, path).observe(duration)
        if status_code.startswith("5") and not error_recorded:
            ERRORS_TOTAL.labels(method, path, status_code).inc()


def render_metrics() -> Response:
    update_dependency_health()
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
