"""Middleware for request correlation ID handling."""

import time
from typing import Callable

from value_fabric.shared.observability.correlation import (
    REQUEST_STATE_CORRELATION_ID_KEY,
    REQUEST_STATE_TRACE_ID_KEY,
)
from value_fabric.shared.observability.trace_context import (
    ALL_TRACE_HEADERS,
    CANONICAL_TRACE_HEADER,
    canonical_trace_headers,
    resolve_trace_context,
    sanitize_trace_id,
)
from value_fabric.shared.observability.request_context import LoggingContext, clear_logging_context, set_logging_context

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation IDs to all requests.

    This middleware:
    1. Reads X-Request-ID from incoming request headers (if present)
    2. Generates a new UUID if no request ID is provided
    3. Stores the request ID in request state for access in handlers
    4. Adds X-Request-ID to all response headers
    5. Makes request ID available for logging correlation
    """

    def __init__(
        self,
        app,
        header_name: str = CANONICAL_TRACE_HEADER,
        generator: Callable[[], str] | None = None,
    ):
        """Initialize the middleware.

        Args:
            app: FastAPI application
            header_name: Header name for request ID (default: X-Request-ID)
            generator: Optional custom ID generator function
        """
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add correlation ID."""
        # Get and validate request ID from header, or generate new one
        trace_context = resolve_trace_context(request.headers)
        request_id = sanitize_trace_id(trace_context.trace_id, generator=self.generator)
        correlation_id = sanitize_trace_id(request.headers.get("X-Correlation-ID"), generator=self.generator)

        # Store in request state for access in route handlers
        setattr(request.state, REQUEST_STATE_TRACE_ID_KEY, request_id)
        setattr(request.state, REQUEST_STATE_CORRELATION_ID_KEY, correlation_id)

        # Legacy alias used by some services/tests.
        setattr(request.state, "request_id", request_id)

        tenant_id = getattr(request.state, "tenant_id", None)

        # Set initial context so logs emitted during request handling are enriched.
        set_logging_context(
            LoggingContext(
                request_id=request_id,
                correlation_id=correlation_id,
                tenant_id=tenant_id,
                route=request.url.path,
                method=request.method,
                status=0,
                latency_ms=0.0,
            )
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)

            # Update context with response metadata for any post-handler logging.
            set_logging_context(
                LoggingContext(
                    request_id=request_id,
                    correlation_id=correlation_id,
                    tenant_id=tenant_id,
                    route=request.url.path,
                    method=request.method,
                    status=response.status_code,
                    latency_ms=elapsed_ms,
                )
            )

            # Add trace headers to response
            for header, value in canonical_trace_headers(request_id).items():
                response.headers[header] = value
            response.headers["X-Correlation-ID"] = correlation_id

            return response
        finally:
            clear_logging_context()


def get_request_id(request: Request) -> str:
    """Get the request ID from a request object.

    Usage in route handlers:
        @app.get("/example")
        async def example(request: Request):
            trace_id = get_request_id(request)
            return dict(trace_id=trace_id)
    """
    # Try to get from request state (set by middleware)
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return str(trace_id)

    # Fall back to header
    for header in ALL_TRACE_HEADERS:
        value = request.headers.get(header)
        if value:
            return value
    return "unknown"
