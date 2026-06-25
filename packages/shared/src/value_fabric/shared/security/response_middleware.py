"""Response middleware for secret redaction in API responses.

This middleware intercepts JSON responses and redacts sensitive fields
before they are sent to clients, preventing secret leakage in success responses.

Production Invariant: Secrets must not be exposed in API responses.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .redaction import redact_value

logger = logging.getLogger(__name__)


class SecretRedactionMiddleware(BaseHTTPMiddleware):
    """Middleware to redact secrets from JSON response bodies.

    This middleware:
    1. Intercepts JSON responses from route handlers
    2. Applies redaction to response body using redact_value()
    3. Replaces response with redacted version
    4. Preserves status code, headers, and response structure
    """

    def __init__(self, app, paths_to_skip: list[str] | None = None):
        """Initialize the middleware.

        Args:
            app: FastAPI application
            paths_to_skip: List of path prefixes to skip redaction (e.g., health endpoints)
        """
        super().__init__(app)
        self.paths_to_skip = paths_to_skip or []

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and redact secrets from response."""
        # Check if path should be skipped
        if any(request.url.path.startswith(path) for path in self.paths_to_skip):
            return await call_next(request)

        response = await call_next(request)

        # Only process JSON responses
        if not isinstance(response, JSONResponse):
            return response

        # Get response body
        body = response.body
        if not body:
            return response

        try:
            # Parse JSON
            response_data = json.loads(body.decode("utf-8"))

            # Redact secrets
            redacted_data = redact_value(response_data)

            # Check if anything was redacted
            if redacted_data != response_data:
                logger.debug(
                    "Secrets redacted from response",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "status": response.status_code,
                    }
                )

            # Create new response with redacted data
            return JSONResponse(
                content=redacted_data,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # If response isn't valid JSON, return as-is
            logger.warning(
                "Failed to parse response JSON for redaction",
                extra={"path": request.url.path, "error": str(exc)},
            )
            return response
        except Exception as exc:
            # Log error but don't break the response
            logger.error(
                "Unexpected error during response redaction",
                extra={"path": request.url.path, "error": str(exc)},
                exc_info=True,
            )
            return response


def install_secret_redaction_middleware(
    app,
    paths_to_skip: list[str] | None = None,
) -> SecretRedactionMiddleware:
    """Install the secret redaction middleware on a FastAPI app.

    Args:
        app: FastAPI application
        paths_to_skip: Optional list of path prefixes to skip (e.g., ["/health", "/metrics"])

    Returns:
        The middleware instance
    """
    middleware = SecretRedactionMiddleware(app, paths_to_skip=paths_to_skip)
    app.add_middleware(SecretRedactionMiddleware, paths_to_skip=paths_to_skip)
    return middleware
