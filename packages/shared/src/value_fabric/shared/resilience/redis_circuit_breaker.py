"""
Redis-backed circuit breaker state store for cross-process synchronization.

When running multiple Gunicorn/uvicorn workers, each process has its own
in-memory circuit breaker state. This Redis store ensures all workers share
the same breaker state, preventing thundering herd against struggling services.

Usage:
    from value_fabric.shared.resilience.redis_circuit_breaker import (
        RedisCircuitBreakerStore,
    )

    store = RedisCircuitBreakerStore(redis_client)
    state = await store.get_state("downstream-service")
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Optional


class RedisCircuitBreakerStore:
    """Redis-backed store for circuit breaker state sharing across processes."""

    KEY_PREFIX = "circuit_breaker"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self, redis_client, ttl: int = DEFAULT_TTL):
        self._redis = redis_client
        self._ttl = ttl

    def _key(self, service: str) -> str:
        return f"{self.KEY_PREFIX}:{service}"

    async def get_state(self, service: str) -> Optional[dict]:
        """Get breaker state from Redis."""
        raw = await self._redis.get(self._key(service))
        if raw:
            return json.loads(raw)
        return None

    async def set_state(self, service: str, state: dict) -> None:
        """Persist breaker state to Redis with TTL."""
        await self._redis.setex(
            self._key(service),
            self._ttl,
            json.dumps(state)
        )

    async def record_failure(self, service: str) -> int:
        """Increment failure count and return new value."""
        key = f"{self.KEY_PREFIX}:{service}:failures"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._ttl)
        return count

    async def reset_failures(self, service: str) -> None:
        """Reset failure count on successful call."""
        await self._redis.delete(f"{self.KEY_PREFIX}:{service}:failures")

    async def get_failure_count(self, service: str) -> int:
        """Get current failure count."""
        count = await self._redis.get(f"{self.KEY_PREFIX}:{service}:failures")
        return int(count) if count else 0

    async def set_open(self, service: str, recovery_timeout: float) -> None:
        """Mark breaker as OPEN with recovery timestamp."""
        import time
        state = {
            "state": "OPEN",
            "opened_at": time.time(),
            "recover_at": time.time() + recovery_timeout,
        }
        await self.set_state(service, state)

    async def set_half_open(self, service: str) -> None:
        """Mark breaker as HALF_OPEN."""
        state = {"state": "HALF_OPEN", "half_open_calls": 0}
        await self.set_state(service, state)

    async def set_closed(self, service: str) -> None:
        """Mark breaker as CLOSED and reset failures."""
        await self._redis.delete(self._key(service))
        await self.reset_failures(service)
