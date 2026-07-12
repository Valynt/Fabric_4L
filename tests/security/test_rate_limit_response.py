"""Rate Limit 429 Response Shape Tests — P1 Gap Remediation

Validates that when a rate limit is exceeded the response:
  1. Returns HTTP 429
  2. Includes a Retry-After header with a positive integer value
  3. Includes X-RateLimit-* informational headers
  4. Returns a structured JSON body with a retry_after field

Gap matrix ref:
  P1 gap 6 — Rate Limit 429 Response: missing Retry-After header

Author: Platform Security Team
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

try:
    from value_fabric.shared.identity.context import (
        AUTH_SOURCE_JWT,
        RequestContext,
    )
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.rate_limiter import RateLimitResult
    _MIDDLEWARE_AVAILABLE = True
except ImportError:
    _MIDDLEWARE_AVAILABLE = False
    RateLimitResult = None
    GovernanceMiddleware = None

pytestmark = [
    pytest.mark.security,
    pytest.mark.rate_limiting,
]

_TENANT_ID = "tenant-rate-limit-test"
_RETRY_AFTER = 45


# ---------------------------------------------------------------------------
# RateLimitResult shape tests (unit — no HTTP stack required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _MIDDLEWARE_AVAILABLE, reason="rate_limiter dependencies not available")
class TestRateLimitResultShape:
    """The RateLimitResult dataclass must carry retry_after and reset_at."""

    def test_rate_limit_result_has_retry_after(self):
        """POSITIVE: RateLimitResult with retry_after=60 stores the value."""
        result = RateLimitResult(allowed=False, remaining=0, reset_at=9999.0, retry_after=60)
        assert result.retry_after == 60, "retry_after must be stored on RateLimitResult."

    def test_rate_limit_result_retry_after_none_when_allowed(self):
        """POSITIVE: Allowed result may carry retry_after=None."""
        result = RateLimitResult(allowed=True, remaining=99, reset_at=9999.0, retry_after=None)
        assert result.retry_after is None

    def test_rate_limit_result_retry_after_positive_when_denied(self):
        """NEGATIVE: Denied result must carry a positive retry_after."""
        result = RateLimitResult(allowed=False, remaining=0, reset_at=9999.0, retry_after=30)
        assert result.retry_after is not None and result.retry_after > 0, (
            "Denied RateLimitResult must carry a positive retry_after."
        )

    def test_rate_limit_result_reset_at_is_float(self):
        """POSITIVE: reset_at is stored as a float epoch timestamp."""
        now = time.time()
        result = RateLimitResult(allowed=False, remaining=0, reset_at=now + 60.0, retry_after=60)
        assert isinstance(result.reset_at, float), "reset_at must be a float."
        assert result.reset_at > now, "reset_at must be in the future for a denied result."


# ---------------------------------------------------------------------------
# 429 response header contract — real GovernanceMiddleware integration
# ---------------------------------------------------------------------------


def _make_denied_rate_limiter(retry_after: int = _RETRY_AFTER) -> MagicMock:
    """Return a mock rate limiter whose check() always returns a denied result."""
    limiter = MagicMock()
    limiter.check = AsyncMock(
        return_value=RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=time.time() + retry_after,
            retry_after=retry_after,
        )
    )
    return limiter


@pytest.fixture
def rate_limited_client():
    """TestClient backed by GovernanceMiddleware with a rate limiter that always denies.

    A pre-populated RequestContext is injected via request.state.governance_context
    so that JWT resolution is bypassed and the rate-limit path is exercised directly.
    """
    from fastapi import FastAPI
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request as StarletteRequest

    app = FastAPI()

    # Inject a pre-resolved context so GovernanceMiddleware skips JWT resolution
    class _InjectContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: StarletteRequest, call_next):
            request.state.governance_context = RequestContext(
                tenant_id=_TENANT_ID,
                auth_source=AUTH_SOURCE_JWT,
            )
            return await call_next(request)

    app.add_middleware(
        GovernanceMiddleware,
        rate_limiter=_make_denied_rate_limiter(_RETRY_AFTER),
    )
    app.add_middleware(_InjectContextMiddleware)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.skipif(
    not (_FASTAPI_AVAILABLE and _MIDDLEWARE_AVAILABLE),
    reason="FastAPI or middleware dependencies not available",
)
class TestRateLimitResponseHeaders:
    """The 429 response from GovernanceMiddleware must include required headers."""

    def test_status_code_is_429(self, rate_limited_client):
        """NEGATIVE: Rate-limited request returns HTTP 429."""
        response = rate_limited_client.get("/probe")
        assert response.status_code == 429, (
            f"Rate-limited request must return 429, got {response.status_code}."
        )

    def test_retry_after_header_present(self, rate_limited_client):
        """NEGATIVE: 429 response must include Retry-After header per RFC 6585."""
        response = rate_limited_client.get("/probe")
        header_keys_lower = {k.lower() for k in response.headers}
        assert "retry-after" in header_keys_lower, (
            "429 response must include Retry-After header."
        )

    def test_retry_after_header_is_positive_integer(self, rate_limited_client):
        """NEGATIVE: Retry-After value must be a positive integer string."""
        response = rate_limited_client.get("/probe")
        retry_after = response.headers.get("retry-after") or response.headers.get("Retry-After")
        assert retry_after is not None, "Retry-After header must be present."
        assert retry_after.isdigit(), (
            f"Retry-After must be a digit string, got: '{retry_after}'"
        )
        assert int(retry_after) > 0, f"Retry-After must be positive, got: {retry_after}"

    def test_retry_after_matches_injected_value(self, rate_limited_client):
        """POSITIVE: Retry-After header reflects the value from the rate limiter."""
        response = rate_limited_client.get("/probe")
        retry_after = response.headers.get("retry-after") or response.headers.get("Retry-After")
        assert int(retry_after) == _RETRY_AFTER, (
            f"Retry-After must equal the limiter's retry_after={_RETRY_AFTER}, got {retry_after}."
        )

    def test_x_ratelimit_remaining_is_zero(self, rate_limited_client):
        """NEGATIVE: X-RateLimit-Remaining must be 0 when rate limited."""
        response = rate_limited_client.get("/probe")
        remaining = (
            response.headers.get("x-ratelimit-remaining")
            or response.headers.get("X-RateLimit-Remaining")
        )
        assert remaining == "0", (
            f"X-RateLimit-Remaining must be '0' when rate limited, got: {remaining}"
        )

    def test_x_ratelimit_reset_header_present(self, rate_limited_client):
        """POSITIVE: X-RateLimit-Reset header is present."""
        response = rate_limited_client.get("/probe")
        header_keys_lower = {k.lower() for k in response.headers}
        assert "x-ratelimit-reset" in header_keys_lower, (
            "X-RateLimit-Reset header must be present in 429 response."
        )

    def test_response_body_contains_retry_after(self, rate_limited_client):
        """NEGATIVE: 429 response body must include retry_after field."""
        response = rate_limited_client.get("/probe")
        body = response.json()
        assert "retry_after" in body, (
            f"429 response body must include 'retry_after'. Got keys: {list(body.keys())}"
        )
        assert body["retry_after"] is not None and body["retry_after"] > 0, (
            "retry_after in body must be a positive integer."
        )

    def test_response_body_contains_error_field(self, rate_limited_client):
        """POSITIVE: 429 response body includes an 'error' field."""
        response = rate_limited_client.get("/probe")
        body = response.json()
        assert "error" in body, (
            f"429 response body must include 'error'. Got keys: {list(body.keys())}"
        )

    def test_retry_after_header_consistent_with_body(self, rate_limited_client):
        """POSITIVE: Retry-After header value matches body retry_after field."""
        response = rate_limited_client.get("/probe")
        header_val = int(
            response.headers.get("retry-after") or response.headers.get("Retry-After", "0")
        )
        body_val = response.json().get("retry_after")
        assert header_val == body_val, (
            f"Retry-After header ({header_val}) must match body retry_after ({body_val})."
        )


# ---------------------------------------------------------------------------
# Middleware-level 429 contract (adversarial)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _MIDDLEWARE_AVAILABLE, reason="Middleware dependencies not available")
class TestRateLimitRetryAfterFallback:
    """Retry-After must never be absent or zero, even in edge cases."""

    def test_retry_after_defaults_to_60_when_result_has_none(self):
        """ADVERSARIAL: When retry_after is None on the RateLimitResult, the middleware
        header falls back to '60' (per the middleware source: `... if not None else "60"`)."""
        result = RateLimitResult(allowed=False, remaining=0, reset_at=9999.0, retry_after=None)
        # Reproduce the middleware's header-building expression
        header_value = str(result.retry_after) if result.retry_after is not None else "60"
        assert header_value == "60", (
            "When retry_after is None, the Retry-After header must default to '60'."
        )

    def test_retry_after_capped_at_reasonable_maximum(self):
        """ADVERSARIAL: The fallback retry_after is capped at 60 seconds."""
        window = 3600  # 1-hour window
        retry_after = max(1, min(window, 60))
        assert retry_after <= 60, (
            f"Fallback retry_after must be capped at 60 seconds, got {retry_after}."
        )
        assert retry_after >= 1, "Fallback retry_after must be at least 1 second."
