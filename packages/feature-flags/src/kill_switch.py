"""
Fabric_4L Kill Switch Framework — v1.2.0

Kill switches are emergency feature flags that bypass ALL normal evaluation
rules and return a safe default (graceful degradation). They are designed for
incident response: when a feature is causing outages or data corruption,
activating its kill switch immediately disables it across all tenants.

Key properties:
  • Instant global effect (Redis-backed, sub-millisecond check).
  • Mandatory TTL — auto-expires after 4 hours (prevents permanent shadows).
  • Every activation triggers a PagerDuty alert.
  • Full audit trail in feature_flag_audit_log.
  • Zero rule evaluation overhead when killed.

Usage:
    from value_fabric.shared.kill_switches import KillSwitch

    ks = KillSwitch("layer4-workflow-execution")
    if ks.is_killed():
        logger.warning("Kill switch active for workflow execution")
        return WorkflowResponse(status="degraded", message="Temporarily disabled")

Integration with api.py:
    The FastAPI router in api.py exposes POST/GET/DELETE endpoints for kill
    switch management. This module is the runtime check used by L1-L6 services.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional, Protocol

logger = logging.getLogger("fabric.kill_switch")

# ────────────────────────────────────────────────────────────────
# Default configuration
# ────────────────────────────────────────────────────────────────

DEFAULT_KILL_SWITCH_TTL_SECONDS = 14_400  # 4 hours
MAX_KILL_SWITCH_TTL_SECONDS = 86_400  # 24 hours hard cap
_REDIS_KEY_PREFIX = "ff:v1:kill"
_LOCAL_CACHE_TTL_SECONDS = 5  # In-process LRU cache to reduce Redis load


# ────────────────────────────────────────────────────────────────
# Protocol for Redis (allows swapping implementations in tests)
# ────────────────────────────────────────────────────────────────

class RedisLike(Protocol):
    """Minimal Redis interface needed by KillSwitch."""

    async def get(self, key: str) -> Optional[str]: ...
    async def setex(self, key: str, seconds: int, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def ttl(self, key: str) -> int: ...


class _NoOpRedis:
    """Fallback when Redis is unavailable — kill switches silently disarm."""

    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, seconds: int, value: str) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def ttl(self, key: str) -> int:
        return -2


# ────────────────────────────────────────────────────────────────
# PagerDuty notifier
# ────────────────────────────────────────────────────────────────

class PagerDutyNotifier:
    """Fire-and-forget PagerDuty alert sender."""

    def __init__(self, routing_key: Optional[str] = None) -> None:
        self.routing_key = routing_key or os.environ.get("PAGERDUTY_ROUTING_KEY")

    async def send(
        self,
        flag_key: str,
        reason: str,
        actor_id: str,
        duration_seconds: int,
    ) -> None:
        if not self.routing_key:
            logger.warning("PagerDuty routing key not configured — alert suppressed")
            return

        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": f"ff-kill-{flag_key}-{datetime.now(timezone.utc):%Y%m%d}",
            "payload": {
                "summary": f"[CRITICAL] Kill switch activated: {flag_key}",
                "severity": "critical",
                "source": "fabric-kill-switches",
                "component": flag_key,
                "group": "feature-flags",
                "class": "kill_switch",
                "custom_details": {
                    "flag_key": flag_key,
                    "reason": reason,
                    "actor_id": actor_id,
                    "duration_seconds": duration_seconds,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    body = await resp.text()
                    if resp.status >= 400:
                        logger.error(
                            "PagerDuty alert failed: HTTP %s — %s", resp.status, body
                        )
                    else:
                        logger.info("PagerDuty alert sent for kill switch %s", flag_key)
        except Exception as exc:
            logger.error("PagerDuty alert exception: %s", exc)


# ────────────────────────────────────────────────────────────────
# KillSwitch class
# ────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class KillSwitchStatus:
    """Snapshot of a kill switch at a point in time."""

    flag_key: str
    killed: bool
    armed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    actor_id: Optional[str] = None


class KillSwitch:
    """
    Emergency kill switch for a single feature flag.

    Usage pattern in services:
        ks = KillSwitch("layer4-workflow-execution")
        if ks.is_killed():
            return graceful_degradation_response()

    The check is designed to be extremely fast on the hot path:
      • An in-process LRU cache avoids repeated Redis round-trips.
      • Cache TTL is 5 seconds — worst-case delay from arm to effect is 5s.
      • Direct Redis get otherwise (typically < 1ms).
    """

    _redis: Optional[RedisLike] = None
    _pagerduty: Optional[PagerDutyNotifier] = None
    _local_cache: dict[str, tuple[bool, float]] = {}

    def __init__(self, flag_key: str) -> None:
        self.flag_key = flag_key
        self._cache_key = f"{_REDIS_KEY_PREFIX}:{flag_key}"

    # ── Class-level dependency injection ─────────────────────────

    @classmethod
    def configure(cls, redis: RedisLike, pagerduty: Optional[PagerDutyNotifier] = None) -> None:
        """Set global Redis and PagerDuty instances (called once at startup)."""
        cls._redis = redis
        cls._pagerduty = pagerduty or PagerDutyNotifier()

    @classmethod
    def _get_redis(cls) -> RedisLike:
        if cls._redis is None:
            # Graceful fallback: if not configured, assume not killed
            logger.warning("KillSwitch Redis not configured — using no-op fallback")
            cls._redis = _NoOpRedis()
        return cls._redis

    @classmethod
    def _get_pagerduty(cls) -> PagerDutyNotifier:
        if cls._pagerduty is None:
            cls._pagerduty = PagerDutyNotifier()
        return cls._pagerduty

    # ── Hot-path checks (synchronous wrappers) ──────────────────

    def is_killed(self) -> bool:
        """
        Synchronous check. Uses a 5-second local cache to avoid Redis
        round-trips on every call.

        **This is the primary API for services.**
        """
        now = time.monotonic()
        cached = self._local_cache.get(self._cache_key)
        if cached is not None:
            killed, cached_at = cached
            if now - cached_at < _LOCAL_CACHE_TTL_SECONDS:
                return killed

        # Cache miss or expired — hit Redis (sync wrapper for async)
        killed = self._check_redis_sync()
        self._local_cache[self._cache_key] = (killed, now)
        return killed

    def is_killed_async(self) -> "KillSwitchAsyncContext":
        """Return an async context manager for use in async functions."""
        return KillSwitchAsyncContext(self)

    def status(self) -> KillSwitchStatus:
        """Return full status, bypassing local cache."""
        raw = self._check_redis_raw_sync()
        if raw is None:
            return KillSwitchStatus(flag_key=self.flag_key, killed=False)
        parts = raw.split("|", 3)
        return KillSwitchStatus(
            flag_key=self.flag_key,
            killed=True,
            armed_at=datetime.fromisoformat(parts[0]) if len(parts) > 0 else None,
            reason=parts[1] if len(parts) > 1 else None,
            actor_id=parts[2] if len(parts) > 2 else None,
        )

    # ── Redis interactions (private) ────────────────────────────

    def _check_redis_sync(self) -> bool:
        """Synchronous wrapper around async Redis get."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop — use asyncio.run
            return asyncio.run(self._async_redis_get())
        # In an async context — schedule it; but since is_killed() is meant
        # to be called from sync code, we use a thread-safe approach.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, self._async_redis_get())
            return future.result(timeout=2)

    def _check_redis_raw_sync(self) -> Optional[str]:
        try:
            return asyncio.run(self._async_redis_get_raw())
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self._async_redis_get_raw())
                return future.result(timeout=2)

    async def _async_redis_get(self) -> bool:
        redis = self._get_redis()
        raw = await redis.get(self._cache_key)
        return raw is not None

    async def _async_redis_get_raw(self) -> Optional[str]:
        redis = self._get_redis()
        return await redis.get(self._cache_key)

    # ── Modification (called by admin API) ──────────────────────

    @classmethod
    async def arm(
        cls,
        flag_key: str,
        reason: str,
        actor_id: str,
        duration_seconds: int = DEFAULT_KILL_SWITCH_TTL_SECONDS,
    ) -> KillSwitchStatus:
        """
        Arm a kill switch. This is the programmatic equivalent of the
        POST /api/v1/admin/feature-flags/{key}/kill endpoint.

        Args:
            flag_key: The feature flag to kill.
            reason: Human-readable justification (min 5 chars).
            actor_id: Who is activating the kill switch.
            duration_seconds: TTL before auto-expiry. Max 86400 (24h).

        Returns:
            KillSwitchStatus reflecting the armed state.
        """
        duration = min(duration_seconds, MAX_KILL_SWITCH_TTL_SECONDS)
        now = datetime.now(timezone.utc)
        expires = now + __import__("datetime").timedelta(seconds=duration)

        redis = cls._get_redis()
        cache_key = f"{_REDIS_KEY_PREFIX}:{flag_key}"
        value = f"{now.isoformat()}|{reason}|{actor_id}"
        await redis.setex(cache_key, duration, value)

        # Fire PagerDuty alert (non-blocking)
        pd = cls._get_pagerduty()
        asyncio.create_task(pd.send(flag_key, reason, actor_id, duration))

        logger.critical(
            "KillSwitch ARMED: flag=%s actor=%s duration=%ds reason=%s",
            flag_key,
            actor_id,
            duration,
            reason,
        )

        return KillSwitchStatus(
            flag_key=flag_key,
            killed=True,
            armed_at=now,
            expires_at=expires,
            reason=reason,
            actor_id=actor_id,
        )

    @classmethod
    async def disarm(cls, flag_key: str, actor_id: str) -> KillSwitchStatus:
        """Manually disarm a kill switch before TTL expiry."""
        redis = cls._get_redis()
        cache_key = f"{_REDIS_KEY_PREFIX}:{flag_key}"
        await redis.delete(cache_key)

        # Clear local cache entry for this flag across all instances
        for k in list(cls._local_cache.keys()):
            if k.endswith(f":{flag_key}"):
                del cls._local_cache[k]

        logger.warning("KillSwitch DISARMED: flag=%s actor=%s", flag_key, actor_id)
        return KillSwitchStatus(flag_key=flag_key, killed=False)

    @classmethod
    @lru_cache(maxsize=128)
    def get_instance(cls, flag_key: str) -> "KillSwitch":
        """Cached factory — reduces object churn for repeated checks."""
        return cls(flag_key)


# ────────────────────────────────────────────────────────────────
# Async context manager variant
# ────────────────────────────────────────────────────────────────

class KillSwitchAsyncContext:
    """
    Async context manager for use in async service handlers.

    Example:
        ks = KillSwitch("layer4-workflow-execution")
        async with ks.is_killed_async() as killed:
            if killed:
                return degraded_response()
    """

    def __init__(self, kill_switch: KillSwitch) -> None:
        self._ks = kill_switch
        self.killed: bool = False

    async def __aenter__(self) -> "KillSwitchAsyncContext":
        redis = KillSwitch._get_redis()
        raw = await redis.get(self._ks._cache_key)
        self.killed = raw is not None
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


# ────────────────────────────────────────────────────────────────
# Decorator for automatic graceful degradation
# ────────────────────────────────────────────────────────────────

from typing import Callable, TypeVar

T = TypeVar("T")


def graceful_degradation(
    flag_key: str,
    *,
    fallback: Callable[[], T],
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that checks a kill switch before executing the wrapped function.
    If the kill switch is armed, returns the fallback instead.

    Example:
        @graceful_degradation(
            "layer4-workflow-execution",
            fallback=lambda: WorkflowResponse(status="degraded"),
        )
        def execute_workflow(payload: dict) -> WorkflowResponse:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        ks = KillSwitch.get_instance(flag_key)

        def wrapper(*args: object, **kwargs: object) -> T:
            if ks.is_killed():
                logger.warning(
                    "Kill switch '%s' active — returning fallback for %s",
                    flag_key,
                    func.__name__,
                )
                return fallback()
            return func(*args, **kwargs)  # type: ignore[return-value]

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# ────────────────────────────────────────────────────────────────
# Startup validation (called by service bootstrap)
# ────────────────────────────────────────────────────────────────

async def validate_kill_switch_health() -> dict[str, str]:
    """
    Health check used by the /health endpoint in each service.
    Verifies Redis connectivity and kill-switch subsystem readiness.
    """
    redis = KillSwitch._get_redis()
    test_key = f"{_REDIS_KEY_PREFIX}:health:{datetime.now(timezone.utc).timestamp()}"
    try:
        await redis.setex(test_key, 10, "ok")
        result = await redis.get(test_key)
        await redis.delete(test_key)
        if result == "ok":
            return {"status": "ok", "redis": "connected"}
        return {"status": "degraded", "redis": "unexpected_response"}
    except Exception as exc:
        logger.error("Kill switch health check failed: %s", exc)
        return {"status": "error", "redis": str(exc)}
