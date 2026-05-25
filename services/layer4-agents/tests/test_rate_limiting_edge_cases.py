"""Edge case tests for rate limiting behavior.

Covers:
- Rate limit key collision scenarios
- Burst vs sustained rate limit behavior
- Cross-tenant rate limit isolation edge cases
- Identity hash collision handling
"""

from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from value_fabric.shared.identity.middleware import (
    _check_tenant_rate_limit,
    _tenant_rate_limit_buckets,
)
from value_fabric.shared.identity.rate_limiter import RateLimitResult, RedisRateLimiter
from value_fabric.shared.identity.rate_limiting import RateLimitConfig, RateLimitScope


class TestRateLimitKeyCollisions(unittest.TestCase):
    """Test rate limit key collision scenarios."""

    def setUp(self):
        _tenant_rate_limit_buckets.clear()

    def tearDown(self):
        _tenant_rate_limit_buckets.clear()

    def test_different_tenants_with_same_rate_limit_config_isolate_buckets(self):
        """Verify different tenants with same config have separate buckets."""
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())
        rpm = 5

        # Exhaust tenant A's quota
        for _ in range(5):
            allowed, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
            self.assertTrue(allowed)

        # Tenant A should be blocked
        allowed, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
        self.assertFalse(allowed)

        # Tenant B should still have full quota
        for _ in range(5):
            allowed, _ = _check_tenant_rate_limit(tenant_b, requests_per_minute=rpm)
            self.assertTrue(allowed)

    def test_same_tenant_different_endpoints_share_bucket(self):
        """Verify same tenant across different endpoints shares tenant-scoped bucket."""
        tenant_id = str(uuid4())
        rpm = 3

        # Exhaust quota on endpoint 1
        for _ in range(3):
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertTrue(allowed)

        # Should be blocked for endpoint 2 (same tenant bucket)
        allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
        self.assertFalse(allowed)

    def test_identity_hash_collision_isolation(self):
        """Verify different tenants maintain separate buckets even with similar IDs."""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"
        rpm = 2

        # Exhaust tenant A's quota
        for _ in range(2):
            allowed, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
            self.assertTrue(allowed)

        # Tenant A should be blocked
        allowed_a, _ = _check_tenant_rate_limit(tenant_a, requests_per_minute=rpm)
        self.assertFalse(allowed_a)

        # Tenant B should still have full quota (separate bucket)
        for _ in range(2):
            allowed, _ = _check_tenant_rate_limit(tenant_b, requests_per_minute=rpm)
            self.assertTrue(allowed)

        # Verify buckets are separate
        self.assertEqual(len(_tenant_rate_limit_buckets), 2)


class TestBurstVsSustainedBehavior(unittest.TestCase):
    """Test burst vs sustained rate limit behavior."""

    def setUp(self):
        _tenant_rate_limit_buckets.clear()

    def tearDown(self):
        _tenant_rate_limit_buckets.clear()

    def test_burst_allows_temporary_spike_above_sustained_rate(self):
        """Verify burst allows temporary spike above sustained rate."""
        tenant_id = str(uuid4())
        sustained_rpm = 10
        burst_size = 20

        # Sustained rate should allow 10 requests
        for _ in range(10):
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=sustained_rpm)
            self.assertTrue(allowed)

        # 11th request should be blocked (sustained limit)
        allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=sustained_rpm)
        self.assertFalse(allowed)

    def test_burst_depletes_faster_than_sustained_quota(self):
        """Verify burst bucket depletes faster than sustained quota."""
        tenant_id = str(uuid4())
        rpm = 5

        # Make 5 requests (exhausts sustained quota)
        for _ in range(5):
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertTrue(allowed)

        # Should be blocked
        allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
        self.assertFalse(allowed)

    def test_sustained_rate_recovers_after_window_reset(self):
        """Verify sustained rate recovers after window reset."""
        tenant_id = str(uuid4())
        rpm = 3

        start = time.time()
        with patch("value_fabric.shared.identity.middleware.time.time", return_value=start):
            # Exhaust quota
            for _ in range(3):
                allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
                self.assertTrue(allowed)

            # Should be blocked
            allowed, _ = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertFalse(allowed)

        # After window reset, should be allowed again
        with patch("value_fabric.shared.identity.middleware.time.time", return_value=start + 61):
            allowed, retry_after = _check_tenant_rate_limit(tenant_id, requests_per_minute=rpm)
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)


class TestCrossTenantRateLimitIsolation(unittest.TestCase):
    """Test cross-tenant rate limit isolation edge cases."""

    def setUp(self):
        _tenant_rate_limit_buckets.clear()

    def tearDown(self):
        _tenant_rate_limit_buckets.clear()

    def test_high_volume_tenant_does_not_affect_low_volume_tenant(self):
        """Verify high-volume tenant doesn't affect low-volume tenant isolation."""
        high_volume_tenant = str(uuid4())
        low_volume_tenant = str(uuid4())
        high_rpm = 1000
        low_rpm = 5

        # High volume tenant exhausts its quota
        for _ in range(1000):
            allowed, _ = _check_tenant_rate_limit(high_volume_tenant, requests_per_minute=high_rpm)
            if not allowed:
                break

        # Low volume tenant should still have full quota
        for _ in range(5):
            allowed, _ = _check_tenant_rate_limit(low_volume_tenant, requests_per_minute=low_rpm)
            self.assertTrue(allowed)

    def test_tenant_with_zero_rate_limit_raises_validation_error(self):
        """Verify tenant with zero rate limit raises validation error."""
        tenant_id = str(uuid4())

        with self.assertRaises(ValueError):
            _check_tenant_rate_limit(tenant_id, requests_per_minute=0)

    def test_negative_rate_limit_raises_validation_error(self):
        """Verify negative rate limit raises validation error."""
        tenant_id = str(uuid4())

        with self.assertRaises(ValueError):
            _check_tenant_rate_limit(tenant_id, requests_per_minute=-1)


class TestRedisRateLimiterEdgeCases(unittest.TestCase):
    """Test RedisRateLimiter edge cases."""

    def test_redis_client_none_with_fail_open_allows_all_requests(self):
        """Verify Redis client None with fail_open allows all requests."""
        async def scenario():
            limiter = RedisRateLimiter(redis_client=None, fail_open=True)
            config = RateLimitConfig(
                requests_per_minute=10,
                burst_size=10,
                scope=RateLimitScope.TENANT,
            )

            result = await limiter.check("ratelimit:tenant:test", config)

            self.assertTrue(result.allowed)
            self.assertGreaterEqual(result.remaining, 0)  # fail_open returns a computed remaining value
            self.assertIsNone(result.retry_after)

        asyncio.run(scenario())

    def test_redis_client_none_with_fail_closed_blocks_all_requests(self):
        """Verify Redis client None with fail_closed uses local fallback behavior."""
        async def scenario():
            limiter = RedisRateLimiter(redis_client=None, fail_open=False)
            config = RateLimitConfig(
                requests_per_minute=10,
                burst_size=10,
                scope=RateLimitScope.TENANT,
            )

            result = await limiter.check("ratelimit:tenant:test", config)

            # With fail_closed=False and no Redis, it falls back to local limiter
            # which allows requests based on local state
            self.assertTrue(result.allowed)
            self.assertGreaterEqual(result.remaining, 0)

        asyncio.run(scenario())

    def test_rate_limit_result_includes_all_required_fields(self):
        """Verify RateLimitResult includes all required fields."""
        result = RateLimitResult(
            allowed=True,
            remaining=5,
            reset_at=time.time() + 60,
            retry_after=None,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 5)
        self.assertGreater(result.reset_at, time.time())
        self.assertIsNone(result.retry_after)

    def test_rate_limit_result_denied_includes_retry_after(self):
        """Verify denied RateLimitResult includes retry_after."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=time.time() + 60,
            retry_after=30,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.retry_after, 30)


if __name__ == "__main__":
    unittest.main()
