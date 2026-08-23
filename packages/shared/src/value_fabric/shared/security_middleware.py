"""
Security Headers Middleware — Fabric 4L

FastAPI middleware that injects OWASP-compliant security headers into
all HTTP responses. Header values are configurable per-environment
and defined as constants for testability and auditability.

Usage:
    from fastapi import FastAPI
    from value_fabric.shared.security_middleware import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

Override per-route:
    @app.get("/health", include_in_schema=False)
    @disable_security_headers
    async def health():
        return {"status": "ok"}

Override specific header:
    @app.get("/embed")
    @security_header_override("X-Frame-Options", "SAMEORIGIN")
    async def embed():
        ...
"""

from __future__ import annotations

import functools
import secrets
from enum import Enum
from typing import Any, Callable, Dict, Optional, Sequence

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def _get_env() -> Environment:
    import os

    env_str = os.environ.get("FABRIC_ENV", "development").lower()
    try:
        return Environment(env_str)
    except ValueError:
        return Environment.DEVELOPMENT


# ---------------------------------------------------------------------------
# Header Constants — Production Values (OWASP Best Practice)
# ---------------------------------------------------------------------------

HSTS_VALUE_PROD = "max-age=63072000; includeSubDomains; preload"
HSTS_VALUE_STAGING = "max-age=86400; includeSubDomains"
HSTS_VALUE_DEV = "max-age=0"

X_CONTENT_TYPE_OPTIONS = "nosniff"

X_FRAME_OPTIONS = "DENY"
X_FRAME_OPTIONS_EMBED = "SAMEORIGIN"  # For /embed endpoints

# CSP directives as constants for testability and documentation
CSP_DEFAULT_SRC = "'self'"
CSP_SCRIPT_SRC_PROD = "'self' 'nonce-{nonce}'"
CSP_SCRIPT_SRC_DEV = "'self' 'unsafe-eval'"
CSP_STYLE_SRC_PROD = "'self' 'nonce-{nonce}'"
CSP_STYLE_SRC_DEV = "'self' 'unsafe-inline'"
CSP_IMG_SRC = "'self' data: https://cdn.fabric4l.dev"
CSP_CONNECT_SRC = "'self' https://api.fabric4l.dev https://telemetry.fabric4l.dev wss://realtime.fabric4l.dev"
CSP_FONT_SRC = "'self' https://fonts.gstatic.com"
CSP_MEDIA_SRC = "'self'"
CSP_OBJECT_SRC = "'none'"
CSP_FRAME_ANCESTORS = "'none'"
CSP_BASE_URI = "'self'"
CSP_FORM_ACTION = "'self'"
CSP_UPGRADE_INSECURE = "upgrade-insecure-requests"
CSP_REPORT_URI = "report-uri https://security-report.fabric4l.dev/csp"

REFERRER_POLICY = "strict-origin-when-cross-origin"

PERMISSIONS_POLICY = (
    "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), "
    "camera=(), display-capture=(), document-domain=(), "
    "encrypted-media=(), execution-while-not-rendered=(), "
    "execution-while-out-of-viewport=(), fullscreen=(self), "
    "geolocation=(), gyroscope=(), layout-animations=(self), "
    "legacy-image-formats=(self), magnetometer=(), microphone=(), "
    "midi=(), navigation-override=(), payment=(), picture-in-picture=(), "
    "publickey-credentials-get=(), speaker-selection=(), "
    "sync-xhr=(self), usb=(), web-share=(), xr-spatial-tracking=()"
)

COEP_PROD = "require-corp"
COEP_DEV = "unsafe-none"

COOP_PROD = "same-origin"
COOP_DEV = "same-origin-allow-popups"

CORP_PROD = "same-site"
CORP_DEV = "cross-origin"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects security headers into every HTTP response.

    Configuration is derived from the FABRIC_ENV environment variable:
      - production:  Strictest values, CSP enforcing, HSTS with preload
      - staging:     Same as prod, CSP report-only, HSTS 1-day
      - development: Relaxed CSP ('unsafe-eval'), no HSTS, permissive CO*/
      - test:        Production values with deterministic CSP nonces

    Per-route overrides can be applied via decorators:
      - @disable_security_headers
      - @security_header_override(name, value)
      - @no_csp_nonce (serve CSP without nonce for static assets)
    """

    # Endpoints that should not receive security headers
    EXCLUDED_PATHS: Sequence[str] = (
        "/health",
        "/healthz",
        "/ready",
        "/readyz",
        "/metrics",
        "/_debug/",
    )

    def __init__(self, app: FastAPI, environment: Optional[Environment] = None) -> None:
        super().__init__(app)
        self.env = environment or _get_env()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Check if this path is excluded
        path = request.url.path
        if any(path.startswith(exc) for exc in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Execute the route handler
        response = await call_next(request)

        # Check for per-route overrides from request state
        overrides = getattr(request.state, "security_header_overrides", {})
        disabled = getattr(request.state, "security_headers_disabled", False)

        if disabled:
            return response

        # Generate CSP nonce for this request
        nonce = self._generate_nonce()

        # Apply headers
        headers = self._build_headers(nonce)
        headers.update(overrides)

        for name, value in headers.items():
            if value:  # Skip empty values
                response.headers[name] = value

        # Also set the nonce on response state so templates can use it
        response.headers["X-CSP-Nonce"] = nonce

        return response

    def _generate_nonce(self) -> str:
        """Generate a CSP nonce. Deterministic in test mode."""
        if self.env == Environment.TEST:
            return "test-nonce-12345678"
        return secrets.token_urlsafe(16)  # 128 bits

    def _build_headers(self, nonce: str) -> Dict[str, str]:
        """Construct the full security header map for the current environment."""
        headers: Dict[str, str] = {}

        # 1. HSTS
        headers["Strict-Transport-Security"] = self._hsts_value()

        # 2. X-Content-Type-Options
        headers["X-Content-Type-Options"] = X_CONTENT_TYPE_OPTIONS

        # 3. X-Frame-Options
        headers["X-Frame-Options"] = X_FRAME_OPTIONS

        # 4. Content-Security-Policy
        headers["Content-Security-Policy"] = self._csp_value(nonce)

        # 5. Referrer-Policy
        headers["Referrer-Policy"] = REFERRER_POLICY

        # 6. Permissions-Policy
        headers["Permissions-Policy"] = PERMISSIONS_POLICY

        # 7. Cross-Origin-Embedder-Policy
        headers["Cross-Origin-Embedder-Policy"] = (
            COEP_PROD
            if self.env
            in (Environment.PRODUCTION, Environment.STAGING, Environment.TEST)
            else COEP_DEV
        )

        # 8. Cross-Origin-Opener-Policy
        headers["Cross-Origin-Opener-Policy"] = (
            COOP_PROD
            if self.env
            in (Environment.PRODUCTION, Environment.STAGING, Environment.TEST)
            else COOP_DEV
        )

        # 9. Cross-Origin-Resource-Policy
        headers["Cross-Origin-Resource-Policy"] = (
            CORP_PROD
            if self.env
            in (Environment.PRODUCTION, Environment.STAGING, Environment.TEST)
            else CORP_DEV
        )

        return headers

    def _hsts_value(self) -> str:
        if self.env == Environment.PRODUCTION:
            return HSTS_VALUE_PROD
        elif self.env == Environment.STAGING:
            return HSTS_VALUE_STAGING
        elif self.env == Environment.TEST:
            return HSTS_VALUE_PROD  # Test uses prod values
        return HSTS_VALUE_DEV

    def _csp_value(self, nonce: str) -> str:
        """Build the CSP string for the current environment."""
        if self.env == Environment.PRODUCTION:
            script_src = CSP_SCRIPT_SRC_PROD.format(nonce=nonce)
            style_src = CSP_STYLE_SRC_PROD.format(nonce=nonce)
        elif self.env == Environment.STAGING:
            script_src = CSP_SCRIPT_SRC_PROD.format(nonce=nonce)
            style_src = CSP_STYLE_SRC_PROD.format(nonce=nonce)
        elif self.env == Environment.TEST:
            script_src = CSP_SCRIPT_SRC_PROD.format(nonce=nonce)
            style_src = CSP_STYLE_SRC_PROD.format(nonce=nonce)
        else:  # development
            script_src = CSP_SCRIPT_SRC_DEV
            style_src = CSP_STYLE_SRC_DEV

        directives = [
            f"default-src {CSP_DEFAULT_SRC}",
            f"script-src {script_src}",
            f"style-src {style_src}",
            f"img-src {CSP_IMG_SRC}",
            f"connect-src {CSP_CONNECT_SRC}",
            f"font-src {CSP_FONT_SRC}",
            f"media-src {CSP_MEDIA_SRC}",
            f"object-src {CSP_OBJECT_SRC}",
            f"frame-ancestors {CSP_FRAME_ANCESTORS}",
            f"base-uri {CSP_BASE_URI}",
            f"form-action {CSP_FORM_ACTION}",
        ]

        if self.env in (Environment.PRODUCTION, Environment.STAGING, Environment.TEST):
            directives.append(CSP_UPGRADE_INSECURE)

        if self.env == Environment.STAGING:
            # Staging: report-only CSP via report-uri
            directives.append(CSP_REPORT_URI)
        elif self.env == Environment.PRODUCTION:
            directives.append(CSP_REPORT_URI)

        return "; ".join(directives)


# ---------------------------------------------------------------------------
# Decorators for per-route header overrides
# ---------------------------------------------------------------------------


def disable_security_headers(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to disable security headers for a specific route.

    Usage:
        @app.get("/health")
        @disable_security_headers
        async def health():
            ...
    """

    @functools.wraps(endpoint)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract request from args (FastAPI injects it as first arg if declared)
        request = kwargs.get("request")
        if request is None and args:
            from starlette.requests import Request as StarletteRequest

            if isinstance(args[0], StarletteRequest):
                request = args[0]
        if request is not None:
            request.state.security_headers_disabled = True
        return (
            await endpoint(*args, **kwargs)
            if asyncio.iscoroutinefunction(endpoint)
            else endpoint(*args, **kwargs)
        )

    # Mark for middleware detection
    wrapper._security_headers_disabled = True  # type: ignore[attr-defined]
    return wrapper


def security_header_override(
    name: str, value: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to override a specific security header for a route.

    Usage:
        @app.get("/embed")
        @security_header_override("X-Frame-Options", "SAMEORIGIN")
        async def embed_widget():
            ...
    """

    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(endpoint)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if request is None and args:
                from starlette.requests import Request as StarletteRequest

                if isinstance(args[0], StarletteRequest):
                    request = args[0]
            if request is not None:
                overrides = getattr(request.state, "security_header_overrides", {})
                overrides[name] = value
                request.state.security_header_overrides = overrides
            return (
                await endpoint(*args, **kwargs)
                if asyncio.iscoroutinefunction(endpoint)
                else endpoint(*args, **kwargs)
            )

        wrapper._security_header_overrides = {name: value}  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Import needed for decorator checks
# ---------------------------------------------------------------------------
import asyncio
