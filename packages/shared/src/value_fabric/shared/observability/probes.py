from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .correlation import LOG_FIELD_CORRELATION_ID, REQUEST_STATE_CORRELATION_ID_KEY, REQUEST_STATE_TRACE_ID_KEY
from .trace_context import canonical_trace_headers, resolve_trace_context

logger = logging.getLogger("value_fabric.observability")

CorrelationProvider = Callable[[Request], str | None]
ReadinessCheck = Callable[[], bool | Awaitable[bool]]
MetricsProvider = Callable[[], str]


def configure_observability(
    app: FastAPI,
    *,
    service_name: str,
    metrics_provider: MetricsProvider | None = None,
    readiness_check: ReadinessCheck | None = None,
    correlation_header: str = "X-Correlation-ID",
) -> None:
    """Install standardized probes and correlation/error middleware."""

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        trace_context = resolve_trace_context(request.headers)
        correlation_id = trace_context.trace_id
        setattr(request.state, REQUEST_STATE_TRACE_ID_KEY, correlation_id)
        setattr(request.state, REQUEST_STATE_CORRELATION_ID_KEY, correlation_id)
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "unhandled_exception",
                        "service": service_name,
                        "path": request.url.path,
                        "method": request.method,
                        LOG_FIELD_CORRELATION_ID: correlation_id,
                        "error": str(exc),  # ban-str-e-allow: structured-log
                        "exception_type": type(exc).__name__,
                    }
                )
            )
            return JSONResponse(
                status_code=500,
                content={"error": "internal_server_error", "correlation_id": correlation_id},
                headers=canonical_trace_headers(correlation_id),
            )

        for header, value in canonical_trace_headers(correlation_id).items():
            response.headers[header] = value
        return response

    paths = {route.path for route in app.routes if hasattr(route, "path")}

    if "/health" not in paths:
        @app.get("/health")
        async def health():
            return {"status": "ok", "service": service_name, "timestamp": datetime.now(timezone.utc).isoformat()}

    if "/ready" not in paths:
        @app.get("/ready")
        async def ready():
            if readiness_check is None:
                return {"status": "ready", "service": service_name}
            result = readiness_check()
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[assignment]
            if not result:
                return JSONResponse(status_code=503, content={"status": "not_ready", "service": service_name})
            return {"status": "ready", "service": service_name}

    if "/metrics" not in paths:
        @app.get("/metrics")
        async def metrics():
            if metrics_provider is None:
                return Response("Metrics collection is disabled", status_code=503, media_type="text/plain")
            return Response(metrics_provider(), media_type="text/plain; version=0.0.4; charset=utf-8")
