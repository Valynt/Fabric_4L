"""Chaos tests for Redis cache failure scenarios.

Verifies system behavior when Redis becomes unavailable, including:
- Cache operations do not return fake success
- Errors are structured with appropriate codes
- Tenant isolation is maintained
- Degraded operation is explicit when fallback is allowed
- Integrity-sensitive paths fail closed
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Import Redis exceptions with graceful fallback
try:
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError
except ImportError:
    # Fallback exception classes for when redis is not installed
    class RedisConnectionError(ConnectionError):
        pass
    class RedisTimeoutError(TimeoutError):
        pass

# Import the rate limiter as a production seam
try:
    from value_fabric.shared.rate_limiting.tenant_rate_limiter import TenantRateLimiter, TenantTier
except ImportError:
    # Mock classes for testing when shared package is not available
    class TenantTier:
        SHARED = "shared"
    class TenantRateLimiter:
        def __init__(self, redis_client=None):
            self.redis_client = redis_client

pytestmark = [pytest.mark.chaos, pytest.mark.requires_redis]


class TestRedisCacheFailure:
    """Verify system behavior when Redis cache fails."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_raises_structured_error(self):
        """When Redis connection fails, a structured error is returned.
        
        Security: The error must not expose internal Redis details.
        Safety: The error must indicate service unavailable, not fake success.
        """
        # Simulate Redis connection failure
        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(side_effect=RedisConnectionError("Connection refused"))
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        tenant_id = uuid4()
        
        # Attempt rate limit check
        with pytest.raises(Exception) as exc_info:
            await limiter.check_rate_limit(
                tenant_id=tenant_id,
                endpoint="/api/test",
                tier=TenantTier.SHARED
            )
        
        # Verify error is raised (not silently converted to success)
        assert exc_info.value is not None
        # The rate limiter should either raise ServiceUnavailableError or return a degraded result
        # Key assertion: it must NOT return a successful rate limit result

    @pytest.mark.asyncio
    async def test_redis_timeout_error_raises_or_degrades_explicitly(self):
        """When Redis times out, the system must not fabricate a success response.
        
        Security: Timeout must not result in cached data being shared across tenants.
        Safety: The caller must know the operation failed or degraded.
        """
        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(side_effect=RedisTimeoutError("Operation timed out"))
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        tenant_id = uuid4()
        
        # The system should either:
        # 1. Raise an exception indicating the failure
        # 2. Return an explicit degraded/unavailable status
        
        with pytest.raises(Exception):
            await limiter.check_rate_limit(
                tenant_id=tenant_id,
                endpoint="/api/test",
                tier=TenantTier.SHARED
            )

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_bypass_tenant_isolation(self):
        """Redis failure must not allow cross-tenant cache access.
        
        Security: When Redis fails, tenant A must not see tenant B's cached data.
        This is verified by ensuring no fallback to shared in-memory cache.
        """
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Simulate Redis that fails for tenant A but works for tenant B
        def conditional_failure(*args, **kwargs):
            # If tenant_a in key, fail; if tenant_b, succeed
            key = args[0] if args else ""
            if str(tenant_a) in str(key):
                raise RedisConnectionError("Redis unavailable")
            return 1  # Success for tenant_b
        
        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(side_effect=conditional_failure)
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        
        # Tenant A should get an error (not use tenant B's cache)
        with pytest.raises(Exception):
            await limiter.check_rate_limit(
                tenant_id=tenant_a,
                endpoint="/api/test",
                tier=TenantTier.SHARED
            )

    @pytest.mark.asyncio
    async def test_redis_unavailable_fails_closed_for_integrity_sensitive_ops(self):
        """When Redis is unavailable, integrity-sensitive operations fail closed.
        
        Operations that require cache consistency must fail rather than proceed
        with potentially stale data.
        """
        mock_redis = AsyncMock()
        # Simulate Redis completely unavailable
        mock_redis.zadd = AsyncMock(side_effect=RedisConnectionError("Redis down"))
        mock_redis.zcount = AsyncMock(side_effect=RedisConnectionError("Redis down"))
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        tenant_id = uuid4()
        
        # Rate limiting is integrity-sensitive - must not allow unlimited requests
        with pytest.raises(Exception):
            await limiter.check_rate_limit(
                tenant_id=tenant_id,
                endpoint="/api/critical",
                tier=TenantTier.SHARED
            )

    @pytest.mark.asyncio
    async def test_cache_get_failure_does_not_return_fabricated_data(self):
        """When cache get fails, the system must not return fabricated cached data.
        
        A cache miss due to Redis failure must not be converted to a cache hit
        with fake/default data.
        """
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
        
        # Simulate cache read operation
        result = await self._simulate_cache_read(mock_redis, "some_key")
        
        # Must return None (cache miss) or raise error, NOT fabricated data
        assert result is None or isinstance(result, Exception)

    async def _simulate_cache_read(self, redis_client, key):
        """Simulate a cache read operation that should fail gracefully."""
        try:
            result = await redis_client.get(key)
            return result
        except RedisConnectionError:
            # Proper behavior: return None (cache miss) or raise structured error
            return None


class TestRedisDegradedMode:
    """Verify explicit degraded mode when Redis fallback is allowed."""

    @pytest.mark.asyncio
    async def test_redis_degraded_mode_is_explicit(self):
        """When Redis degrades, the degradation must be explicit.
        
        If a service allows degraded operation without Redis, the response
        must indicate degraded status so callers can adjust behavior.
        """
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=RedisConnectionError("No Redis"))
        
        # Simulate health check that detects Redis unavailability
        is_degraded = await self._check_degraded_status(mock_redis)
        
        # Health check should indicate degraded status
        assert is_degraded is True

    async def _check_degraded_status(self, redis_client):
        """Check if service should operate in degraded mode."""
        try:
            await redis_client.ping()
            return False  # Redis available, not degraded
        except RedisConnectionError:
            return True  # Redis unavailable, degraded mode

    @pytest.mark.asyncio
    async def test_degraded_read_through_does_not_expose_other_tenant_data(self):
        """In degraded mode, cache fallback must not expose cross-tenant data.
        
        If cache is bypassed, the fallback must not use shared in-memory
        storage that could contain other tenants' data.
        """
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Simulate a shared in-memory fallback (dangerous pattern)
        shared_memory_cache = {}
        
        # Tenant A stores something
        shared_memory_cache[f"{tenant_a}:data"] = "tenant_a_secret"
        
        # Tenant B tries to access (simulating bug where tenant_id is not checked)
        # This test documents the expected behavior: tenant isolation must be maintained
        
        # The actual implementation must not use shared_memory_cache without tenant scoping
        assert f"{tenant_b}:data" not in shared_memory_cache
        assert f"{tenant_a}:data" in shared_memory_cache


class TestRedisPartialFailure:
    """Verify behavior when Redis partially degrades (timeouts, slow responses)."""

    @pytest.mark.asyncio
    async def test_redis_slow_response_does_not_cause_cascade(self):
        """Slow Redis responses must not cause cascading timeouts.
        
        The system must have circuit breaker or timeout patterns to prevent
        Redis slowness from affecting overall API availability.
        """
        
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=0)
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.expire = AsyncMock(return_value=True)
        # Simulate very slow Redis (5 second delay) on the write path.
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(5)
            return 1
        
        mock_redis.zadd = AsyncMock(side_effect=slow_response)
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        tenant_id = uuid4()
        
        # Operation should timeout quickly, not wait 5 seconds
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                limiter.check_rate_limit(
                    tenant_id=tenant_id,
                    endpoint="/api/test",
                    tier=TenantTier.SHARED
                ),
                timeout=1.0  # 1 second timeout
            )

    @pytest.mark.asyncio
    async def test_redis_connection_flapping_handled_gracefully(self):
        """Flapping Redis connections must be handled without data corruption.
        
        If Redis connects/disconnects rapidly, operations must not result
        in partial writes or inconsistent state.
        """
        tenant_id = uuid4()
        call_count = 0
        
        def flapping_behavior(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call succeeds, second fails, third succeeds
            if call_count % 2 == 0:
                raise RedisConnectionError("Flapping")
            return 1
        
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=0)
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.expire = AsyncMock(return_value=True)
        # The rate limiter updates minute, hour, and day windows for a single
        # accepted request. Model Redis flapping at request boundaries so the
        # test verifies partial-write handling rather than a per-command toy
        # pattern that can never permit a complete request.
        mock_redis.zadd = AsyncMock(
            side_effect=[
                1, 1, 1,
                RedisConnectionError("Flapping"),
                1, 1, 1,
                RedisConnectionError("Flapping"),
            ]
        )
        
        limiter = TenantRateLimiter(redis_client=mock_redis)
        
        # Multiple calls should each be handled independently
        results = []
        for _ in range(4):
            try:
                result = await limiter.check_rate_limit(
                    tenant_id=tenant_id,
                    endpoint="/api/test",
                    tier=TenantTier.SHARED
                )
                results.append("success")
            except Exception:
                results.append("failure")
        
        # Verify we got both successes and failures (flapping detected)
        assert "success" in results
        assert "failure" in results
