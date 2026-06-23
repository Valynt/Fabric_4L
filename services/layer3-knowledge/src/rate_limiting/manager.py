"""Comprehensive API rate limiting and throttling system with advanced policies and user quotas."""

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, cast

import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel

from .types import (
    BucketState,
    LeakyBucketState,
    MetricsMap,
    RateLimitRuleMetadata,
    StringCountMap,
    TokenBucketState,
)


class RateLimitManager_get_metricsResult(TypedDictModel):
    disabled_rules: Any
    enabled_rules: Any
    metrics: dict[str, Any]
    rules_by_scope: dict[str, Any]
    rules_by_type: dict[str, Any]
    store_connected: bool
    total_rules: Any

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Rate limiting algorithm types."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class RateLimitScope(str, Enum):
    """Rate limiting scope."""

    GLOBAL = "global"
    USER = "user"
    API_KEY = "api_key"
    IP = "ip"
    ENDPOINT = "endpoint"
    TENANT = "tenant"  # Task 84: Per-tenant rate limiting
    CUSTOM = "custom"


class RateLimitAction(str, Enum):
    """Action when rate limit is exceeded."""

    REJECT = "reject"
    THROTTLE = "throttle"
    QUEUE = "queue"
    DEGRADE = "degrade"


@dataclass
class RateLimitRule:
    """Rate limiting rule definition."""

    id: str
    name: str
    scope: RateLimitScope
    type: RateLimitType
    limit: int
    window_seconds: int
    burst_size: int | None = None
    action: RateLimitAction = RateLimitAction.REJECT
    priority: int = 0
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: RateLimitRuleMetadata = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation."""
        if self.burst_size is None:
            self.burst_size = self.limit // 10 or 1


class RateLimitRequest(BaseModel):
    """Rate limit check request."""

    identifier: str = Field(
        ..., description="Unique identifier (user ID, API key, IP, etc.)"
    )
    scope: RateLimitScope = Field(..., description="Rate limiting scope")
    endpoint: str | None = Field(None, description="API endpoint")
    method: str | None = Field(None, description="HTTP method")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class RateLimitResponse(BaseModel):
    """Rate limit check response."""

    allowed: bool = Field(..., description="Whether request is allowed")
    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: datetime = Field(..., description="When limit resets")
    retry_after: int | None = Field(None, description="Seconds to wait before retry")
    rule_id: str | None = Field(None, description="Applied rule ID")
    action: RateLimitAction | None = Field(None, description="Action taken")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = Field(default=True, description="Enable rate limiting")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    default_limits: list[RateLimitRule] = Field(
        default_factory=list, description="Default rate limits"
    )
    custom_limits: list[RateLimitRule] = Field(
        default_factory=list, description="Custom rate limits"
    )
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cleanup_interval: int = Field(
        default=300, description="Cleanup interval in seconds"
    )
    max_requests_per_window: int = Field(
        default=10000, description="Max requests per window"
    )
    tracking_enabled: bool = Field(default=True, description="Enable request tracking")
    analytics_enabled: bool = Field(default=True, description="Enable analytics")

    model_config = ConfigDict(use_enum_values=True)


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Bucket capacity
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed
        """
        now = time.time()

        # Refill tokens
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_refill(self, tokens: int = 1) -> float:
        """Get time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens are available
        """
        if self.tokens >= tokens:
            return 0.0

        needed = tokens - self.tokens
        return needed / self.refill_rate


class SlidingWindow:
    """Sliding window rate limiter."""

    def __init__(self, limit: int, window_seconds: int):
        """Initialize sliding window.

        Args:
            limit: Request limit
            window_seconds: Window size in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = deque()

    def is_allowed(self) -> bool:
        """Check if request is allowed.

        Returns:
            True if request is allowed
        """
        now = time.time()

        # Remove old requests
        while self.requests and self.requests[0] <= now - self.window_seconds:
            self.requests.popleft()

        if len(self.requests) < self.limit:
            self.requests.append(now)
            return True

        return False

    def time_until_reset(self) -> float:
        """Get time until window resets.

        Returns:
            Seconds until reset
        """
        if not self.requests:
            return 0.0

        oldest_request = self.requests[0]
        reset_time = oldest_request + self.window_seconds
        return max(0.0, reset_time - time.time())


class FixedWindow:
    """Fixed window rate limiter."""

    def __init__(self, limit: int, window_seconds: int):
        """Initialize fixed window.

        Args:
            limit: Request limit
            window_seconds: Window size in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.count = 0
        self.window_start = time.time()

    def is_allowed(self) -> bool:
        """Check if request is allowed.

        Returns:
            True if request is allowed
        """
        now = time.time()

        # Reset window if expired
        if now - self.window_start >= self.window_seconds:
            self.count = 0
            self.window_start = now

        if self.count < self.limit:
            self.count += 1
            return True

        return False

    def time_until_reset(self) -> float:
        """Get time until window resets.

        Returns:
            Seconds until reset
        """
        now = time.time()
        reset_time = self.window_start + self.window_seconds
        return max(0.0, reset_time - now)


class LeakyBucket:
    """Leaky bucket rate limiter."""

    def __init__(self, capacity: int, leak_rate: float):
        """Initialize leaky bucket.

        Args:
            capacity: Bucket capacity
            leak_rate: Requests per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.queue = deque()
        self.last_leak = time.time()

    def is_allowed(self) -> bool:
        """Check if request is allowed.

        Returns:
            True if request is allowed
        """
        now = time.time()

        # Leak requests
        elapsed = now - self.last_leak
        leak_count = int(elapsed * self.leak_rate)

        for _ in range(min(leak_count, len(self.queue))):
            self.queue.popleft()

        self.last_leak = now

        if len(self.queue) < self.capacity:
            self.queue.append(now)
            return True

        return False

    def time_until_allowed(self) -> float:
        """Get time until next request is allowed.

        Returns:
            Seconds until allowed
        """
        if len(self.queue) < self.capacity:
            return 0.0

        # Time for enough requests to leak
        needed = len(self.queue) - self.capacity + 1
        return needed / self.leak_rate


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load."""

    def __init__(self, base_limit: int, window_seconds: int):
        """Initialize adaptive rate limiter.

        Args:
            base_limit: Base request limit
            window_seconds: Window size in seconds
        """
        self.base_limit = base_limit
        self.window_seconds = window_seconds
        self.current_limit = base_limit
        self.system_load = 0.0
        self.error_rate = 0.0
        self.last_adjustment = time.time()

    def update_metrics(self, system_load: float, error_rate: float):
        """Update system metrics.

        Args:
            system_load: System load (0.0-1.0)
            error_rate: Error rate (0.0-1.0)
        """
        self.system_load = system_load
        self.error_rate = error_rate

        # Adjust limit every minute
        now = time.time()
        if now - self.last_adjustment >= 60:
            self._adjust_limit()
            self.last_adjustment = now

    def _adjust_limit(self):
        """Adjust rate limit based on metrics."""
        # Reduce limit if high load or error rate
        if self.system_load > 0.8 or self.error_rate > 0.1:
            self.current_limit = max(1, int(self.current_limit * 0.8))
        # Increase limit if low load and error rate
        elif self.system_load < 0.5 and self.error_rate < 0.05:
            self.current_limit = min(self.base_limit, int(self.current_limit * 1.1))

    def is_allowed(self, window: SlidingWindow) -> bool:
        """Check if request is allowed.

        Args:
            window: Sliding window limiter

        Returns:
            True if request is allowed
        """
        # Temporarily adjust window limit
        original_limit = window.limit
        window.limit = self.current_limit

        try:
            return window.is_allowed()
        finally:
            window.limit = original_limit


class RateLimitStore:
    """Rate limit data storage backend."""

    def __init__(self, redis_url: str):
        """Initialize rate limit store.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def get_bucket_state(self, key: str) -> BucketState | None:
        """Get bucket state from Redis.

        Args:
            key: Bucket key

        Returns:
            Bucket state or None
        """
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get bucket state: {e}")
            return None

    async def set_bucket_state(self, key: str, state: BucketState, ttl: int = 3600):
        """Set bucket state in Redis.

        Args:
            key: Bucket key
            state: Bucket state
            ttl: Time to live
        """
        if not self.redis_client:
            return

        try:
            await self.redis_client.setex(key, ttl, json.dumps(state))
        except Exception as e:
            logger.error(f"Failed to set bucket state: {e}")

    async def increment_counter(self, key: str, window_seconds: int) -> int:
        """Increment counter with expiration.

        Args:
            key: Counter key
            window_seconds: Window size

        Returns:
            Current count
        """
        if not self.redis_client:
            return 0

        try:
            # Use Redis atomic increment with expiration
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Failed to increment counter: {e}")
            return 0

    async def get_counter(self, key: str) -> int:
        """Get counter value.

        Args:
            key: Counter key

        Returns:
            Counter value
        """
        if not self.redis_client:
            return 0

        try:
            value = await self.redis_client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Failed to get counter: {e}")
            return 0

    async def cleanup_expired_keys(self):
        """Clean up expired keys."""
        if not self.redis_client:
            return

        try:
            # Redis automatically handles expiration, but we can clean up any manually set keys
            pattern = "rate_limit:*"
            keys = await self.redis_client.keys(pattern)

            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # Key without expiration
                    await self.redis_client.expire(key, 3600)  # Set default expiration

            logger.info(f"Cleaned up {len(keys)} rate limit keys")
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")


class RateLimitManager:
    """Manages rate limiting rules and enforcement."""

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limit manager.

        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.store = RateLimitStore(config.redis_url)
        self.rules: list[RateLimitRule] = []
        self.limiters: dict[str, Any] = {}  # Cache of limiters
        self.metrics: MetricsMap = defaultdict(int)

        # Combine default and custom rules
        self.rules = config.default_limits + config.custom_limits

        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    async def start(self):
        """Start rate limit manager."""
        await self.store.connect()
        logger.info("Rate limit manager started")

    async def stop(self):
        """Stop rate limit manager."""
        await self.store.disconnect()
        logger.info("Rate limit manager stopped")

    async def check_rate_limit(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check if request is allowed based on rate limits.

        Args:
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        if not self.config.enabled:
            return RateLimitResponse(
                allowed=True,
                limit=0,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=60),
                metadata={"message": "Rate limiting disabled"},
            )

        # Find applicable rules
        applicable_rules = self._find_applicable_rules(request)

        if not applicable_rules:
            return RateLimitResponse(
                allowed=True,
                limit=0,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=60),
                metadata={"message": "No applicable rate limits"},
            )

        # Check each rule (highest priority first)
        for rule in applicable_rules:
            if not rule.enabled:
                continue

            response = await self._check_rule(rule, request)

            if not response.allowed:
                # Rate limit exceeded
                self.metrics[f"rate_limit_exceeded_{rule.scope.value}"] += 1
                return response

        # All rules passed
        return RateLimitResponse(
            allowed=True,
            limit=0,
            remaining=0,
            reset_time=datetime.utcnow() + timedelta(seconds=60),
            metadata={"message": "Request allowed"},
        )

    def _find_applicable_rules(self, request: RateLimitRequest) -> list[RateLimitRule]:
        """Find applicable rules for request.

        Args:
            request: Rate limit check request

        Returns:
            List of applicable rules
        """
        applicable = []

        for rule in self.rules:
            # Check scope
            if rule.scope != request.scope:
                continue

            # Check conditions
            if self._match_conditions(rule.conditions, request):
                applicable.append(rule)

        return applicable

    def _match_conditions(
        self, conditions: dict[str, Any], request: RateLimitRequest
    ) -> bool:
        """Check if request matches rule conditions.

        Args:
            conditions: Rule conditions
            request: Rate limit check request

        Returns:
            True if conditions match
        """
        for key, value in conditions.items():
            if key == "endpoint" and request.endpoint:
                if isinstance(value, list):
                    if request.endpoint not in value:
                        return False
                elif request.endpoint != value:
                    return False
            elif key == "method" and request.method:
                if isinstance(value, list):
                    if request.method.upper() not in [v.upper() for v in value]:
                        return False
                elif request.method.upper() != value.upper():
                    return False
            elif key in request.metadata:
                if request.metadata[key] != value:
                    return False

        return True

    async def _check_rule(
        self, rule: RateLimitRule, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check specific rule.

        Args:
            rule: Rate limit rule
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # Generate unique key for this rule and identifier
        key = self._generate_key(rule, request)

        if rule.type == RateLimitType.TOKEN_BUCKET:
            return await self._check_token_bucket(rule, key, request)
        elif rule.type == RateLimitType.SLIDING_WINDOW:
            return await self._check_sliding_window(rule, key, request)
        elif rule.type == RateLimitType.FIXED_WINDOW:
            return await self._check_fixed_window(rule, key, request)
        elif rule.type == RateLimitType.LEAKY_BUCKET:
            return await self._check_leaky_bucket(rule, key, request)
        elif rule.type == RateLimitType.ADAPTIVE:
            return await self._check_adaptive(rule, key, request)
        else:
            raise ValueError(f"Unsupported rate limit type: {rule.type}")

    def _generate_key(self, rule: RateLimitRule, request: RateLimitRequest) -> str:
        """Generate unique key for rate limiting.

        Args:
            rule: Rate limit rule
            request: Rate limit check request

        Returns:
            Unique key
        """
        parts = ["rate_limit", rule.scope.value, rule.id, request.identifier]

        if request.endpoint:
            parts.append(request.endpoint)

        if request.method:
            parts.append(request.method.upper())

        return ":".join(parts)

    async def _check_token_bucket(
        self, rule: RateLimitRule, key: str, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check token bucket rate limit.

        Args:
            rule: Rate limit rule
            key: Rate limit key
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # Get or create bucket state
        state = await self.store.get_bucket_state(key)

        if not state:
            state = cast(
                TokenBucketState,
                {
                    "tokens": float(rule.limit),
                    "last_refill": time.time(),
                    "created_at": time.time(),
                },
            )

        # Calculate refill rate
        refill_rate = rule.limit / rule.window_seconds

        # Refill tokens
        now = time.time()
        elapsed = now - state["last_refill"]
        state["tokens"] = min(rule.limit, state["tokens"] + elapsed * refill_rate)
        state["last_refill"] = now

        # Check if request is allowed
        if state["tokens"] >= 1:
            state["tokens"] -= 1
            await self.store.set_bucket_state(key, state, rule.window_seconds)

            return RateLimitResponse(
                allowed=True,
                limit=rule.limit,
                remaining=int(state["tokens"]),
                reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds),
                rule_id=rule.id,
                metadata={"bucket_tokens": state["tokens"]},
            )
        else:
            # Calculate retry after
            retry_after = int(1.0 / refill_rate)

            return RateLimitResponse(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=retry_after),
                retry_after=retry_after,
                rule_id=rule.id,
                action=rule.action,
                metadata={"bucket_tokens": state["tokens"]},
            )

    async def _check_sliding_window(
        self, rule: RateLimitRule, key: str, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check sliding window rate limit.

        Args:
            rule: Rate limit rule
            key: Rate limit key
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # Increment counter with expiration
        count = await self.store.increment_counter(key, rule.window_seconds)

        if count <= rule.limit:
            return RateLimitResponse(
                allowed=True,
                limit=rule.limit,
                remaining=rule.limit - count,
                reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds),
                rule_id=rule.id,
                metadata={"window_count": count},
            )
        else:
            # Get TTL for retry after
            ttl = (
                await self.store.redis_client.ttl(key)
                if self.store.redis_client
                else rule.window_seconds
            )

            return RateLimitResponse(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=ttl),
                retry_after=ttl,
                rule_id=rule.id,
                action=rule.action,
                metadata={"window_count": count},
            )

    async def _check_fixed_window(
        self, rule: RateLimitRule, key: str, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check fixed window rate limit.

        Args:
            rule: Rate limit rule
            key: Rate limit key
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # Get current window start
        now = time.time()
        window_start = int(now // rule.window_seconds) * rule.window_seconds
        window_key = f"{key}:{window_start}"

        # Increment counter for this window
        count = await self.store.increment_counter(window_key, rule.window_seconds)

        if count <= rule.limit:
            return RateLimitResponse(
                allowed=True,
                limit=rule.limit,
                remaining=rule.limit - count,
                reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds),
                rule_id=rule.id,
                metadata={"window_count": count},
            )
        else:
            retry_after = rule.window_seconds - (now - window_start)

            return RateLimitResponse(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=retry_after),
                retry_after=int(retry_after),
                rule_id=rule.id,
                action=rule.action,
                metadata={"window_count": count},
            )

    async def _check_leaky_bucket(
        self, rule: RateLimitRule, key: str, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check leaky bucket rate limit.

        Args:
            rule: Rate limit rule
            key: Rate limit key
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # Get or create bucket state
        state = await self.store.get_bucket_state(key)

        if not state:
            state = cast(
                LeakyBucketState,
                {
                    "queue_size": 0,
                    "last_leak": time.time(),
                    "created_at": time.time(),
                },
            )

        # Calculate leak rate
        leak_rate = rule.limit / rule.window_seconds

        # Leak requests
        now = time.time()
        elapsed = now - state["last_leak"]
        leak_count = int(elapsed * leak_rate)
        state["queue_size"] = max(0, state["queue_size"] - leak_count)
        state["last_leak"] = now

        # Check if request is allowed
        if state["queue_size"] < rule.limit:
            state["queue_size"] += 1
            await self.store.set_bucket_state(key, state, rule.window_seconds)

            return RateLimitResponse(
                allowed=True,
                limit=rule.limit,
                remaining=rule.limit - state["queue_size"],
                reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds),
                rule_id=rule.id,
                metadata={"queue_size": state["queue_size"]},
            )
        else:
            # Calculate retry after
            retry_after = int((state["queue_size"] - rule.limit + 1) / leak_rate)

            return RateLimitResponse(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=retry_after),
                retry_after=retry_after,
                rule_id=rule.id,
                action=rule.action,
                metadata={"queue_size": state["queue_size"]},
            )

    async def _check_adaptive(
        self, rule: RateLimitRule, key: str, request: RateLimitRequest
    ) -> RateLimitResponse:
        """Check adaptive rate limit.

        Args:
            rule: Rate limit rule
            key: Rate limit key
            request: Rate limit check request

        Returns:
            Rate limit response
        """
        # For now, use sliding window as base
        # In production, this would integrate with system metrics
        return await self._check_sliding_window(rule, key, request)

    async def add_rule(self, rule: RateLimitRule):
        """Add a new rate limit rule.

        Args:
            rule: Rate limit rule to add
        """
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added rate limit rule: {rule.name}")

    async def remove_rule(self, rule_id: str) -> bool:
        """Remove a rate limit rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]

        if len(self.rules) < original_count:
            logger.info(f"Removed rate limit rule: {rule_id}")
            return True

        return False

    async def update_rule(self, rule_id: str, updates: dict[str, Any]) -> bool:
        """Update a rate limit rule.

        Args:
            rule_id: Rule ID to update
            updates: Updates to apply

        Returns:
            True if updated
        """
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                logger.info(f"Updated rate limit rule: {rule_id}")
                return True

        return False

    async def get_metrics(self) -> RateLimitManager_get_metricsResult:
        """Get rate limiting metrics.

        Returns:
            Metrics dictionary
        """
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules if r.enabled])

        # Count by scope
        scope_counts: StringCountMap = defaultdict(int)
        type_counts: StringCountMap = defaultdict(int)

        for rule in self.rules:
            scope_counts[rule.scope.value] += 1
            type_counts[rule.type.value] += 1

        return RateLimitManager_get_metricsResult.model_validate({
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "rules_by_scope": dict(scope_counts),
            "rules_by_type": dict(type_counts),
            "metrics": dict(self.metrics),
            "store_connected": self.store.redis_client is not None,
        })


    async def cleanup(self):
        """Cleanup expired rate limit data."""
        await self.store.cleanup_expired_keys()
        logger.info("Rate limit cleanup completed")


# Global rate limit manager instance
_rate_limit_manager: RateLimitManager | None = None


def get_rate_limit_manager() -> RateLimitManager | None:
    """Get global rate limit manager instance.

    Returns:
        Rate limit manager instance
    """
    return _rate_limit_manager


async def initialize_rate_limiting(config: RateLimitConfig) -> RateLimitManager:
    """Initialize global rate limiting system.

    Args:
        config: Rate limiting configuration

    Returns:
        Rate limit manager instance
    """
    global _rate_limit_manager
    _rate_limit_manager = RateLimitManager(config)
    await _rate_limit_manager.start()
    logger.info("Rate limiting system initialized")
    return _rate_limit_manager
