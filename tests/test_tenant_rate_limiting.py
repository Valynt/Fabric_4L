"""
Tests for tenant-scoped rate limiting (Task 5).

Verifies:
- Tenant tier-based limits
- Sliding window algorithm
- Burst allowance
- Custom limits
- Admin API
- Middleware integration
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from value_fabric.shared.rate_limiting.admin_api import get_tenant_quota
from value_fabric.shared.rate_limiting.tenant_rate_limiter import (
    RateLimitConfig,
    RateLimitResult,
    TenantRateLimiter,
    TenantTier,
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)
    redis.zrange = AsyncMock(return_value=[])
    redis.zadd = AsyncMock()
    redis.expire = AsyncMock()
    redis.zcount = AsyncMock(return_value=0)
    redis.scan_iter = AsyncMock(return_value=iter([]))
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create tenant rate limiter with mock Redis."""
    return TenantRateLimiter(redis_client=mock_redis)


class TestTenantRateLimiter:
    """Tests for TenantRateLimiter core functionality."""
    
    @pytest.mark.asyncio
    async def test_allows_request_within_limit(self, rate_limiter, mock_redis):
        """Verify requests within limit are allowed."""
        tenant_id = uuid4()
        
        # Mock: 0 requests in window
        mock_redis.zcard.return_value = 0
        
        result = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        assert result.allowed is True
        assert result.remaining > 0
    
    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self, rate_limiter, mock_redis):
        """Verify requests over limit are blocked."""
        tenant_id = uuid4()
        
        # Mock: 120 requests in minute window (limit is 100 + 20 burst)
        mock_redis.zcard.return_value = 120
        
        result = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds is not None
    
    @pytest.mark.asyncio
    async def test_different_limits_per_tier(self, rate_limiter):
        """Verify different tiers have different limits."""
        from value_fabric.shared.rate_limiting.tenant_rate_limiter import DEFAULT_TENANT_LIMITS
        
        shared_limits = DEFAULT_TENANT_LIMITS[TenantTier.SHARED]
        enterprise_limits = DEFAULT_TENANT_LIMITS[TenantTier.ENTERPRISE]
        
        assert enterprise_limits.requests_per_minute > shared_limits.requests_per_minute
        assert enterprise_limits.requests_per_hour > shared_limits.requests_per_hour
    
    @pytest.mark.asyncio
    async def test_burst_allowance(self, rate_limiter, mock_redis):
        """Verify burst allowance allows temporary spikes."""
        tenant_id = uuid4()
        
        # Mock: 110 requests (over base limit of 100, but within burst)
        mock_redis.zcard.return_value = 110
        
        result = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        # Should still be allowed (100 + 20 burst = 120 total)
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_sliding_window_removes_old_requests(self, rate_limiter, mock_redis):
        """Verify sliding window removes requests outside window."""
        tenant_id = uuid4()
        
        await rate_limiter._check_window(
            tenant_id=tenant_id,
            endpoint="/v1/entities",
            window_seconds=60,
            limit=100,
        )
        
        # Verify old entries were removed
        assert mock_redis.zremrangebyscore.called
    
    @pytest.mark.asyncio
    async def test_custom_limits_override_tier_defaults(self, rate_limiter):
        """Verify custom limits override tier defaults."""
        tenant_id = uuid4()
        
        custom_config = RateLimitConfig(
            requests_per_minute=5000,
            requests_per_hour=200000,
            requests_per_day=5000000,
            burst_allowance=1000,
        )
        
        await rate_limiter.set_custom_limit(tenant_id, custom_config)
        
        config = rate_limiter._get_limit_config(tenant_id, TenantTier.SHARED)
        
        assert config.requests_per_minute == 5000
        assert config != rate_limiter._get_limit_config(uuid4(), TenantTier.SHARED)
    
    @pytest.mark.asyncio
    async def test_reset_tenant_limits(self, rate_limiter, mock_redis):
        """Verify resetting tenant limits deletes all keys."""
        tenant_id = uuid4()
        
        # Mock: 3 keys exist for tenant
        mock_redis.scan_iter.return_value = iter([
            b"ratelimit:tenant:xxx:endpoint:yyy:window:60",
            b"ratelimit:tenant:xxx:endpoint:yyy:window:3600",
            b"ratelimit:tenant:xxx:endpoint:yyy:window:86400",
        ])
        
        deleted = await rate_limiter.reset_tenant_limits(tenant_id)
        
        assert deleted == 3
        assert mock_redis.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_tenant_usage(self, rate_limiter, mock_redis):
        """Verify getting tenant usage statistics."""
        tenant_id = uuid4()
        
        # Mock: keys exist
        mock_redis.scan_iter.return_value = iter([
            b"ratelimit:tenant:xxx:endpoint:/v1/entities:window:60",
        ])
        mock_redis.zcount.return_value = 45
        
        usage = await rate_limiter.get_tenant_usage(tenant_id)
        
        assert usage["tenant_id"] == str(tenant_id)
        assert "windows" in usage
    
    @pytest.mark.asyncio
    async def test_multiple_windows_checked(self, rate_limiter, mock_redis):
        """Verify all time windows are checked."""
        tenant_id = uuid4()
        
        # Mock: under minute limit, but over hour limit
        mock_redis.zcard.side_effect = [50, 6000, 0]  # minute, hour, day
        
        result = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        # Should be blocked by hour limit
        assert result.allowed is False


class TestRateLimitConfig:
    """Tests for RateLimitConfig model."""
    
    def test_creates_with_all_fields(self):
        """Verify config can be created with all fields."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=5000,
            requests_per_day=100000,
            burst_allowance=20,
        )
        
        assert config.requests_per_minute == 100
        assert config.burst_allowance == 20
    
    def test_burst_allowance_defaults_to_zero(self):
        """Verify burst allowance defaults to 0."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=5000,
            requests_per_day=100000,
        )
        
        assert config.burst_allowance == 0


class TestRateLimitResult:
    """Tests for RateLimitResult model."""
    
    def test_creates_allowed_result(self):
        """Verify allowed result creation."""
        result = RateLimitResult(
            allowed=True,
            limit=100,
            remaining=50,
            reset_at=datetime.utcnow(),
        )
        
        assert result.allowed is True
        assert result.retry_after_seconds is None
    
    def test_creates_blocked_result(self):
        """Verify blocked result creation."""
        result = RateLimitResult(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=datetime.utcnow(),
            retry_after_seconds=30,
        )
        
        assert result.allowed is False
        assert result.retry_after_seconds == 30


    
    @pytest.mark.asyncio
    async def test_normalizes_endpoint_paths(self):
        """Verify endpoint normalization groups similar requests."""
        from value_fabric.shared.rate_limiting.middleware import TenantRateLimitMiddleware
        
        middleware = TenantRateLimitMiddleware(app=None, rate_limiter=None)
        
        # UUIDs should be normalized
        assert middleware._normalize_endpoint("/v1/entities/123e4567-e89b-12d3-a456-426614174000") == "/v1/entities/{id}"
        
        # Numeric IDs should be normalized
        assert middleware._normalize_endpoint("/v1/entities/12345") == "/v1/entities/{id}"
        
        # Regular paths unchanged
        assert middleware._normalize_endpoint("/v1/entities") == "/v1/entities"


class TestTenantRateLimitMiddleware:
    """Regression tests for TenantRateLimitMiddleware dispatch safety."""

    @pytest.mark.asyncio
    async def test_dispatch_with_requestcontext_missing_tenant_tier(self):
        """Middleware must not crash when tenant context lacks tenant_tier.

        Regression: ``RequestContext`` carries ``isolation_tier`` but not
        ``tenant_tier``.  The middleware used to access
        ``tenant_context.tenant_tier`` directly, raising ``AttributeError``.
        """
        from unittest.mock import AsyncMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from value_fabric.shared.rate_limiting.middleware import TenantRateLimitMiddleware

        app = FastAPI()
        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(
            return_value=MagicMock(
                allowed=True,
                limit=100,
                remaining=99,
                reset_at=datetime.utcnow(),
            )
        )
        app.add_middleware(
            TenantRateLimitMiddleware,
            rate_limiter=mock_limiter,
            exempt_paths=[],
        )

        @app.get("/api/v1/entities")
        def entities():
            return {"items": []}

        client = TestClient(app)

        # Patch get_tenant_context to return a minimal RequestContext
        # that does NOT have tenant_tier (matching production behavior).
        with patch(
            "value_fabric.shared.boundaries.tenant_boundary.get_tenant_context"
        ) as mock_ctx:
            mock_ctx.return_value = MagicMock(
                tenant_id="tenant-a",
                user_id="user-1",
                # Intentionally omit tenant_tier to trigger the regression
            )
            response = client.get("/api/v1/entities")

        assert response.status_code == 200
        mock_limiter.check_rate_limit.assert_awaited_once()
        # Verify it defaulted to SHARED tier
        call_kwargs = mock_limiter.check_rate_limit.await_args.kwargs
        assert call_kwargs["tenant_tier"].value == "shared"

    @pytest.mark.asyncio
    async def test_backend_unavailable_fails_closed_in_production(self):
        """When the rate-limit backend is unavailable, production-like environments
        must fail CLOSED with a controlled 503 — never an unhandled 500 that would
        also mask the route's authn/authz verdict.

        Regression for Core GA blocker: RBAC returned 500 (RuntimeError
        ``tenant_rate_limit_unavailable``) when Redis was down.
        """
        from unittest.mock import AsyncMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from value_fabric.shared.rate_limiting.middleware import TenantRateLimitMiddleware

        app = FastAPI()
        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(
            side_effect=RuntimeError("tenant_rate_limit_unavailable")
        )
        app.add_middleware(
            TenantRateLimitMiddleware,
            rate_limiter=mock_limiter,
            exempt_paths=[],
        )

        @app.get("/api/v1/entities")
        def entities():
            return {"items": []}

        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "value_fabric.shared.boundaries.tenant_boundary.get_tenant_context"
        ) as mock_ctx, patch(
            "value_fabric.shared.environment.is_production_like_environment",
            return_value=True,
        ):
            mock_ctx.return_value = MagicMock(tenant_id="tenant-a", user_id="user-1")
            response = client.get("/api/v1/entities")

        assert response.status_code == 503
        assert response.json()["error"] == "rate_limit_unavailable"

    @pytest.mark.asyncio
    async def test_backend_unavailable_fails_open_in_non_production(self):
        """When the rate-limit backend is unavailable in a non-production environment,
        the request must proceed to the route handler (where authn/authz are enforced)
        rather than surfacing a 500.
        """
        from unittest.mock import AsyncMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from value_fabric.shared.rate_limiting.middleware import TenantRateLimitMiddleware

        app = FastAPI()
        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(
            side_effect=RuntimeError("tenant_rate_limit_unavailable")
        )
        app.add_middleware(
            TenantRateLimitMiddleware,
            rate_limiter=mock_limiter,
            exempt_paths=[],
        )

        @app.get("/api/v1/entities")
        def entities():
            return {"items": []}

        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "value_fabric.shared.boundaries.tenant_boundary.get_tenant_context"
        ) as mock_ctx, patch(
            "value_fabric.shared.environment.is_production_like_environment",
            return_value=False,
        ):
            mock_ctx.return_value = MagicMock(tenant_id="tenant-a", user_id="user-1")
            response = client.get("/api/v1/entities")

        assert response.status_code == 200
        assert response.json() == {"items": []}


class TestRateLimitAdminAPI:
    """Tests for rate limit admin API."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("resolved_tier", [TenantTier.SHARED, TenantTier.DEDICATED, TenantTier.ENTERPRISE])
    async def test_get_tenant_quota_uses_resolved_tier(self, resolved_tier):
        """Verify quota lookup uses the resolved tenant tier from metadata provider."""
        tenant_id = uuid4()
        context = SimpleNamespace(user_id=uuid4(), roles=["super_admin"])

        mock_rate_limiter = AsyncMock()
        mock_rate_limiter.get_tenant_quota_status = AsyncMock(return_value={
            "tenant_id": str(tenant_id),
            "tier": resolved_tier.value,
            "limits": {"requests_per_minute": 100},
            "usage": {"minute": 1},
            "custom_limits": False,
        })

        metadata_provider = AsyncMock()
        metadata_provider.get_tenant_tier = AsyncMock(return_value=resolved_tier)

        response = await get_tenant_quota(
            tenant_id=tenant_id,
            context=context,
            rate_limiter=mock_rate_limiter,
            tenant_metadata_provider=metadata_provider,
        )

        assert response.tier == resolved_tier.value
        mock_rate_limiter.get_tenant_quota_status.assert_awaited_once_with(
            tenant_id=tenant_id,
            tenant_tier=resolved_tier,
        )

    @pytest.mark.asyncio
    async def test_get_tenant_quota_returns_404_when_tenant_not_found(self):
        """Verify unknown tenant IDs return 404 instead of defaulting to SHARED."""
        from fastapi import HTTPException

        tenant_id = uuid4()
        context = SimpleNamespace(user_id=uuid4(), roles=["super_admin"])
        mock_rate_limiter = AsyncMock()
        metadata_provider = AsyncMock()
        metadata_provider.get_tenant_tier = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_quota(
                tenant_id=tenant_id,
                context=context,
                rate_limiter=mock_rate_limiter,
                tenant_metadata_provider=metadata_provider,
            )

        assert exc_info.value.status_code == 404
        mock_rate_limiter.get_tenant_quota_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_tenant_quota_prevents_tier_mismatch_from_rate_limiter_response(self):
        """Verify response tier follows resolved metadata tier even if backend returns mismatched tier."""
        tenant_id = uuid4()
        resolved_tier = TenantTier.DEDICATED
        context = SimpleNamespace(user_id=uuid4(), roles=["super_admin"])

        mock_rate_limiter = AsyncMock()
        mock_rate_limiter.get_tenant_quota_status = AsyncMock(return_value={
            "tenant_id": str(tenant_id),
            "tier": TenantTier.SHARED.value,
            "limits": {"requests_per_minute": 100},
            "usage": {"minute": 1},
            "custom_limits": False,
        })

        metadata_provider = AsyncMock()
        metadata_provider.get_tenant_tier = AsyncMock(return_value=resolved_tier)

        response = await get_tenant_quota(
            tenant_id=tenant_id,
            context=context,
            rate_limiter=mock_rate_limiter,
            tenant_metadata_provider=metadata_provider,
        )

        assert response.tier == resolved_tier.value
        mock_rate_limiter.get_tenant_quota_status.assert_awaited_once_with(
            tenant_id=tenant_id,
            tenant_tier=resolved_tier,
        )


class TestRateLimitingIntegration:
    """Integration tests for rate limiting scenarios."""
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_in_rate_limits(self, rate_limiter, mock_redis):
        """Verify rate limits are isolated per tenant."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Tenant A makes 100 requests
        mock_redis.zcard.return_value = 100
        result_a = await rate_limiter.check_rate_limit(
            tenant_id=tenant_a,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        # Tenant B should still be allowed (separate counter)
        mock_redis.zcard.return_value = 0
        result_b = await rate_limiter.check_rate_limit(
            tenant_id=tenant_b,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        assert result_b.allowed is True
    
    @pytest.mark.asyncio
    async def test_endpoint_isolation_in_rate_limits(self, rate_limiter, mock_redis):
        """Verify rate limits are isolated per endpoint."""
        tenant_id = uuid4()
        
        # Endpoint A at limit
        mock_redis.zcard.return_value = 120
        result_a = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/entities",
        )
        
        # Endpoint B should still be allowed (separate counter)
        mock_redis.zcard.return_value = 0
        result_b = await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/formulas",
        )
        
        assert result_a.allowed is False
        assert result_b.allowed is True

    @pytest.mark.asyncio
    async def test_burst_abuse_does_not_starve_other_tenants(self, rate_limiter, mock_redis):
        """A noisy tenant should not consume another tenant's budget."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_redis.zcard.side_effect = [120, 120, 120, 0, 0, 0]
        blocked = await rate_limiter.check_rate_limit(
            tenant_id=tenant_a,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/agents/execute",
            route_group="agent_execution",
        )
        allowed = await rate_limiter.check_rate_limit(
            tenant_id=tenant_b,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/agents/execute",
            route_group="agent_execution",
        )

        assert blocked.allowed is False
        assert allowed.allowed is True

    @pytest.mark.asyncio
    async def test_redis_key_includes_tenant_principal_and_route_group(self, rate_limiter, mock_redis):
        tenant_id = uuid4()
        user_id = uuid4()
        mock_redis.zcard.return_value = 0

        await rate_limiter.check_rate_limit(
            tenant_id=tenant_id,
            tenant_tier=TenantTier.SHARED,
            endpoint="/v1/extract",
            user_id=user_id,
            route_group="extraction",
        )

        key = mock_redis.zremrangebyscore.await_args.args[0]
        assert f"tenant:{tenant_id}" in key
        assert f"user:{user_id}" in key
        assert "route_group:extraction" in key
