from __future__ import annotations

"""Active regression tests for per-tenant rate limiting.

Validates:
- TENANT scope rate limiting exists
- Per-tenant settings schema remains valid
- Process-local tenant buckets isolate tenants in unit tests
- Middleware consumes tenant-specific rate-limit settings through the shared limiter
"""


import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import (
    GovernanceMiddleware,
    RateLimiterConfigurationError,
    _check_tenant_rate_limit,
    _tenant_rate_limit_buckets,
)
from value_fabric.shared.identity.rate_limiter import RateLimitResult, RedisRateLimiter
from value_fabric.shared.identity.rate_limiting import RateLimitConfig, RateLimitScope
from layer4_agents.tenants.settings_schema import (
    RateLimitSettings,
    TenantSettings,
    get_tenant_rate_limits,
)


class TestTenantRateLimiting(unittest.TestCase):
    """Test per-tenant rate limiting functionality."""

    def setUp(self):
        _tenant_rate_limit_buckets.clear()

    def tearDown(self):
        _tenant_rate_limit_buckets.clear()

    def test_tenant_scope_added_to_enum(self):
        """Verify TENANT scope exists in RateLimitScope enum."""
        self.assertTrue(hasattr(RateLimitScope, "TENANT"))
        self.assertEqual(RateLimitScope.TENANT, "tenant")

    def test_tenant_settings_schema_validation(self):
        """Verify tenant settings schema validates rate limits correctly."""
        settings = {"rate_limits": {"requests_per_minute": 200, "burst": 400}}
        tenant_settings = TenantSettings.from_json(settings)
        self.assertEqual(tenant_settings.rate_limits.requests_per_minute, 200)
        self.assertEqual(tenant_settings.rate_limits.burst, 400)

        with self.assertRaises(ValueError):
            RateLimitSettings(requests_per_minute=200, burst=100)

    def test_tenant_settings_defaults(self):
        """Verify defaults are applied when settings are missing."""
        limits = get_tenant_rate_limits({})
        self.assertEqual(limits.requests_per_minute, 120)
        self.assertEqual(limits.burst, 240)
        self.assertEqual(limits.llm_requests_per_minute, 30)

        limits = get_tenant_rate_limits(None)
        self.assertEqual(limits.requests_per_minute, 120)

    def test_rate_limit_check_validates_positive_rpm(self):
        """Verify rate limit rejects non-positive requests_per_minute."""
        tenant_id = str(uuid4())

        with self.assertRaisesRegex(ValueError, "requests_per_minute must be >= 1"):
            _check_tenant_rate_limit(tenant_id, requests_per_minute=0)

        with self.assertRaisesRegex(ValueError, "requests_per_minute must be >= 1"):
            _check_tenant_rate_limit(tenant_id, requests_per_minute=-1)

    def test_rate_limit_check_allows_under_limit(self):
        """Verify requests under limit are allowed."""
        tenant_id = str(uuid4())

        for _ in range(5):
            allowed, retry_after = _check_tenant_rate_limit(tenant_id, requests_per_minute=10)
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

    def test_rate_limit_check_blocks_over_limit(self):
        """Verify requests over limit are blocked."""
        tenant_id = str(uuid4())
        rpm = 3

        for _ in range(3):
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertTrue(allowed)

        allowed, retry_after = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_tenant_isolation(self):
        """Verify Tenant A cannot consume Tenant B's quota."""
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())
        rpm = 3

        for _ in range(3):
            allowed, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
            self.assertTrue(allowed)

        allowed, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
        self.assertFalse(allowed)

        for _ in range(3):
            allowed, _ = _check_tenant_rate_limit(tenant_b, requests_per_minute=rpm)
            self.assertTrue(allowed)

        allowed, _ = _check_tenant_rate_limit(tenant_b, requests_per_minute=rpm)
        self.assertFalse(allowed)

    def test_rate_limit_window_reset(self):
        """Verify rate limit window resets after 60 seconds."""
        tenant_id = str(uuid4())
        rpm = 2

        start = time.time()
        with patch("value_fabric.shared.identity.middleware.time.time", return_value=start):
            for _ in range(2):
                allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
                self.assertTrue(allowed)
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertFalse(allowed)

        with patch("value_fabric.shared.identity.middleware.time.time", return_value=start + 61):
            allowed, retry_after = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

    def test_tenant_settings_serialization(self):
        """Verify tenant settings can be serialized to JSON."""
        settings = TenantSettings()
        json_data = settings.to_json()

        self.assertIn("rate_limits", json_data)
        self.assertEqual(json_data["rate_limits"]["requests_per_minute"], 120)
        self.assertEqual(json_data["rate_limits"]["burst"], 240)


class FakeRateLimiter:
    """Minimal async limiter that records the key and config passed by middleware."""

    def __init__(self, allowed: bool = True):
        self.allowed = allowed
        self.calls = []

    async def check(self, key, config):
        self.calls.append((key, config))
        return RateLimitResult(
            allowed=self.allowed,
            remaining=0 if not self.allowed else max(config.requests_per_minute - 1, 0),
            reset_at=time.time() + 60,
            retry_after=60 if not self.allowed else None,
        )


def _request(path="/private", method="GET"):
    return SimpleNamespace(
        headers=Headers({}),
        state=SimpleNamespace(),
        method=method,
        url=SimpleNamespace(path=path),
    )


def _context(tenant_id=None):
    return RequestContext(
        tenant_id=tenant_id or uuid4(),
        user_id="user-1",
        api_key_id=None,
        roles=["read_only"],
        source="jwt",
        raw={},
    )


def limiter_config():
    return RateLimitConfig(
        requests_per_minute=10,
        burst_size=10,
        scope=RateLimitScope.TENANT,
    )


class TestRateLimitMiddlewareIntegration(unittest.TestCase):
    """Test rate limiting integration with the current GovernanceMiddleware API.

    NOTE: These integration tests are skipped due to GovernanceMiddleware API changes.
    The core unit tests (TestTenantRateLimiting) cover the essential functionality
    and pass. Track integration test fixes as follow-up implementation work.
    """

    @classmethod
    def setUpClass(cls):
        """Set up for integration tests — previously skipped due to middleware API changes."""
        pass

    def test_middleware_uses_tenant_settings_for_rate_limit(self):
        """Middleware should prefer tenant settings when a resolver is configured."""
        async def scenario():
            tenant_id = uuid4()
            limiter = FakeRateLimiter(allowed=True)
            resolver = AsyncMock(
                return_value={
                    "rate_limits": {
                        "requests_per_minute": 1,
                        "burst_size": 1,
                        "scope": "tenant",
                    }
                }
            )
            middleware = GovernanceMiddleware(
                app=MagicMock(),
                rate_limiter=limiter,
                tenant_settings_resolver=resolver,
            )
            request = _request()
            context = _context(tenant_id)

            result = await middleware._check_rate_limit(request, context)

            self.assertTrue(result.allowed)
            resolver.assert_awaited_once_with(tenant_id)
            self.assertTrue(limiter.calls[0][0].startswith(f"ratelimit:tenant:{tenant_id}:"))
            self.assertEqual(limiter.calls[0][1].requests_per_minute, 1)
            self.assertEqual(limiter.calls[0][1].scope, RateLimitScope.TENANT)
            # request.state.rate_limit_result is set by dispatch(), not _check_rate_limit()
            self.assertEqual(request.state.rate_limit_config.requests_per_minute, 1)

        asyncio.run(scenario())

    def test_middleware_honors_layer4_burst_size_schema_key(self):
        """Middleware should read tenant settings rate_limits.burst_size."""
        async def scenario():
            tenant_id = uuid4()
            limiter = FakeRateLimiter(allowed=True)
            resolver = AsyncMock(
                return_value={
                    "rate_limits": {
                        "requests_per_minute": 25,
                        "burst_size": 50,
                        "scope": "tenant",
                    }
                }
            )
            middleware = GovernanceMiddleware(
                app=MagicMock(),
                rate_limiter=limiter,
                tenant_settings_resolver=resolver,
            )

            result = await middleware._check_rate_limit(_request(), _context(tenant_id))

            self.assertTrue(result.allowed)
            self.assertEqual(limiter.calls[0][1].requests_per_minute, 25)
            self.assertEqual(limiter.calls[0][1].burst_size, 50)

        asyncio.run(scenario())

    def test_middleware_uses_tenant_config_for_429_headers(self):
        """Blocked responses should report the tenant-specific checked limit."""
        async def scenario():
            tenant_id = uuid4()
            limiter = FakeRateLimiter(allowed=False)
            resolver = AsyncMock(
                return_value={
                    "rate_limits": {
                        "requests_per_minute": 7,
                        "burst": 7,
                        "scope": "tenant",
                    }
                }
            )
            middleware = GovernanceMiddleware(
                app=MagicMock(),
                rate_limiter=limiter,
                tenant_settings_resolver=resolver,
            )
            request = _request()
            context = _context(tenant_id)
            middleware._resolve_identity = AsyncMock(return_value=context)

            async def call_next(_request):
                raise AssertionError("handler should not run after rate-limit denial")

            response = await middleware.dispatch(request, call_next)

            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers["X-RateLimit-Limit"], "7")
            self.assertEqual(response.headers["X-RateLimit-Remaining"], "0")
            self.assertEqual(response.headers["Retry-After"], "60")
            self.assertEqual(response.headers["X-RateLimit-Scope"], "tenant")
            self.assertEqual(response.headers["X-RateLimit-Policy"], "tenant_settings")
            self.assertEqual(len(limiter.calls), 1)

        asyncio.run(scenario())

    def test_middleware_does_not_double_consume_allowed_requests(self):
        """Allowed requests should call the shared limiter exactly once."""
        async def scenario():
            tenant_id = uuid4()
            limiter = FakeRateLimiter(allowed=True)
            middleware = GovernanceMiddleware(app=MagicMock(), rate_limiter=limiter)
            request = _request()
            context = _context(tenant_id)
            middleware._resolve_identity = AsyncMock(return_value=context)

            async def call_next(_request):
                return JSONResponse({"ok": True})

            response = await middleware.dispatch(request, call_next)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(limiter.calls), 1)
            self.assertEqual(response.headers["X-RateLimit-Limit"], "30")
            self.assertEqual(response.headers["X-RateLimit-Remaining"], "29")
            self.assertEqual(response.headers["X-RateLimit-Scope"], "tenant")
            self.assertEqual(response.headers["X-RateLimit-Policy"], "role_default")
            self.assertEqual(response.headers["X-Tenant-ID-Resolved"], str(tenant_id))

        asyncio.run(scenario())

    def test_resolver_failure_falls_back_to_role_defaults(self):
        """Tenant settings outages should keep enforcing role defaults."""
        async def scenario():
            tenant_id = uuid4()
            limiter = FakeRateLimiter(allowed=True)
            resolver = AsyncMock(side_effect=RuntimeError("settings unavailable"))
            middleware = GovernanceMiddleware(
                app=MagicMock(),
                rate_limiter=limiter,
                tenant_settings_resolver=resolver,
            )

            result = await middleware._check_rate_limit(_request(), _context(tenant_id))

            self.assertTrue(result.allowed)
            resolver.assert_awaited_once_with(tenant_id)
            self.assertEqual(limiter.calls[0][1].requests_per_minute, 30)
            self.assertEqual(limiter.calls[0][1].scope, RateLimitScope.TENANT)

        asyncio.run(scenario())

    def test_middleware_skips_rate_limit_without_limiter(self):
        """Middleware should skip rate-limit checks when no limiter is configured."""
        async def scenario():
            middleware = GovernanceMiddleware(app=MagicMock(), rate_limiter=None)
            request = _request()
            context = _context()

            result = await middleware._check_rate_limit(request, context)

            self.assertIsNone(result)

        asyncio.run(scenario())

    def test_prod_like_environment_requires_shared_limiter(self):
        """Multi-worker deployments should fail closed without a shared limiter."""
        from value_fabric.shared.identity.middleware import MultiWorkerRateLimitError
        with patch.dict("os.environ", {"ENVIRONMENT": "production", "UVICORN_WORKERS": "2"}, clear=False):
            with self.assertRaises(MultiWorkerRateLimitError):
                GovernanceMiddleware(app=MagicMock(), rate_limiter=None)

    def test_redis_failure_degrades_open_locally(self):
        """Local/test Redis failures are explicit fail-open fallback behavior."""
        async def scenario():
            limiter = RedisRateLimiter(redis_client=MagicMock(), fail_open=True)
            # Simulate Redis connection failure
            limiter._adapter.check = AsyncMock(side_effect=ConnectionError("redis down"))
            result = await limiter.check("ratelimit:tenant:test", limiter_config())

            self.assertTrue(result.allowed)
            self.assertEqual(result.remaining, -1)
            self.assertIsNone(result.retry_after)

        asyncio.run(scenario())

    def test_redis_failure_fails_closed_in_prod_policy(self):
        """Production Redis failures return a denied result with retry guidance."""
        async def scenario():
            limiter = RedisRateLimiter(redis_client=MagicMock(), fail_open=False)
            # Simulate Redis connection failure
            limiter._adapter.check = AsyncMock(side_effect=ConnectionError("redis down"))
            result = await limiter.check("ratelimit:tenant:test", limiter_config())

            self.assertFalse(result.allowed)
            self.assertEqual(result.remaining, 0)
            self.assertEqual(result.retry_after, 60)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
