from __future__ import annotations

"""Tenant-level LLM budget guardrails with throttling and escalation signals."""


import asyncio
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from value_fabric.shared.identity.context import require_context
from value_fabric.shared.redis_ha import create_async_redis_client
from value_fabric.shared.security.neo4j import is_production_like_environment

from ..metrics import get_metrics

logger = logging.getLogger(__name__)


class LLMBudgetExceededError(RuntimeError):
    """Raised when a tenant exceeds a hard budget threshold."""


@dataclass(slots=True)
class LLMBudgetDecision:
    """Result of pre-flight budget validation for an LLM request."""

    model: str
    throttle_seconds: int
    escalation_required: bool


class LLMBudgetGuardrails:
    """Tenant budget guardrails with Redis-backed production accounting.

    Caps and thresholds are configured by environment variables:
    - ``LLM_BUDGET_HOURLY_CAP_USD`` (default: 100)
    - ``LLM_BUDGET_DAILY_CAP_USD`` (default: 1000)
    - ``LLM_BUDGET_SOFT_THRESHOLD_RATIO`` (default: 0.8)
    - ``LLM_BUDGET_THROTTLE_SECONDS`` (default: 15)
    - ``LLM_BUDGET_FALLBACK_MODEL`` (default: gpt-4o-mini)
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self.hourly_cap_usd = float(os.getenv("LLM_BUDGET_HOURLY_CAP_USD", "100"))
        self.daily_cap_usd = float(os.getenv("LLM_BUDGET_DAILY_CAP_USD", "1000"))
        self.soft_threshold_ratio = float(os.getenv("LLM_BUDGET_SOFT_THRESHOLD_RATIO", "0.8"))
        self.throttle_seconds = int(os.getenv("LLM_BUDGET_THROTTLE_SECONDS", "15"))
        self.fallback_model = os.getenv("LLM_BUDGET_FALLBACK_MODEL", "gpt-4o-mini")
        self.environment = os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development"

        self._usage_events: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._redis = redis_client if redis_client is not None else self._build_redis_client()
        if is_production_like_environment(self.environment) and self._redis is None:
            raise RuntimeError(
                "Redis-backed LLM budget guardrails are required in production/staging. "
                "Set LLM_BUDGET_REDIS_URL or REDIS_URL."
            )

    def _build_redis_client(self) -> Any | None:
        redis_url = os.getenv("LLM_BUDGET_REDIS_URL") or os.getenv("REDIS_URL")
        if not redis_url:
            return None
        try:
            return create_async_redis_client(redis_url, decode_responses=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if is_production_like_environment(self.environment):
                raise RuntimeError("Failed to initialize Redis LLM budget backend") from exc
            logger.warning("Using in-memory LLM budget fallback: %s", exc)
            return None

    async def precheck_or_raise(self, model: str) -> LLMBudgetDecision:
        """Check budget state and return throttling/escalation decision.

        Raises:
            LLMBudgetExceededError: if hard cap was exceeded and request must be blocked.
        """
        ctx = require_context()
        tenant_id = str(ctx.tenant_id) if ctx.tenant_id else "unknown"
        normalized_tenant = tenant_id.strip() or "unknown"

        now = datetime.now(timezone.utc)  # noqa: UP017 (Python 3.10 compatibility)
        if self._redis is not None:
            hourly_spend, daily_spend = await self._redis_window_spend(normalized_tenant, now)
        else:
            async with self._lock:
                hourly_spend, daily_spend = self._window_spend_locked(normalized_tenant, now)

        if hourly_spend >= self.hourly_cap_usd or daily_spend >= self.daily_cap_usd:
            self._record_event(normalized_tenant, "blocked", "hard_cap_exceeded")
            raise LLMBudgetExceededError(
                "LLM budget hard cap exceeded "
                f"(hourly=${hourly_spend:.2f}/${self.hourly_cap_usd:.2f}, "
                f"daily=${daily_spend:.2f}/${self.daily_cap_usd:.2f})"
            )

        hourly_ratio = hourly_spend / self.hourly_cap_usd if self.hourly_cap_usd > 0 else 0.0
        daily_ratio = daily_spend / self.daily_cap_usd if self.daily_cap_usd > 0 else 0.0
        ratio = max(hourly_ratio, daily_ratio)

        if ratio >= self.soft_threshold_ratio:
            self._record_event(normalized_tenant, "throttled", "soft_cap_threshold")
            return LLMBudgetDecision(
                model=self.fallback_model,
                throttle_seconds=self.throttle_seconds,
                escalation_required=True,
            )

        return LLMBudgetDecision(model=model, throttle_seconds=0, escalation_required=False)

    async def record_usage(self, cost_usd: float) -> None:
        """Record observed LLM usage for budget window accounting."""
        ctx = require_context()
        tenant_id = str(ctx.tenant_id) if ctx.tenant_id else "unknown"
        normalized_tenant = tenant_id.strip() or "unknown"
        if cost_usd <= 0:
            return

        now = datetime.now(timezone.utc)  # noqa: UP017 (Python 3.10 compatibility)
        if self._redis is not None:
            await self._redis_record_usage(normalized_tenant, now, cost_usd)
            return

        async with self._lock:
            self._usage_events[normalized_tenant].append((now, cost_usd))
            self._prune_locked(normalized_tenant, now)

    async def _redis_window_spend(self, tenant_id: str, now: datetime) -> tuple[float, float]:
        hourly_key, daily_key = self._redis_keys(tenant_id, now)
        try:
            hourly_raw, daily_raw = await self._redis.mget(hourly_key, daily_key)
            return float(hourly_raw or 0), float(daily_raw or 0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if is_production_like_environment(self.environment):
                self._record_event(tenant_id, "blocked", "redis_unavailable")
                raise LLMBudgetExceededError("LLM budget backend unavailable") from exc
            logger.warning("LLM budget Redis unavailable; using in-memory fallback: %s", exc)
            async with self._lock:
                return self._window_spend_locked(tenant_id, now)

    async def _redis_record_usage(self, tenant_id: str, now: datetime, cost_usd: float) -> None:
        hourly_key, daily_key = self._redis_keys(tenant_id, now)
        try:
            pipe = self._redis.pipeline()
            pipe.incrbyfloat(hourly_key, cost_usd)
            pipe.expire(hourly_key, 3700)
            pipe.incrbyfloat(daily_key, cost_usd)
            pipe.expire(daily_key, 90000)
            await pipe.execute()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if is_production_like_environment(self.environment):
                self._record_event(tenant_id, "blocked", "redis_unavailable")
                raise LLMBudgetExceededError("LLM budget backend unavailable") from exc
            logger.warning("LLM budget Redis record failed; using in-memory fallback: %s", exc)
            async with self._lock:
                self._usage_events[tenant_id].append((now, cost_usd))
                self._prune_locked(tenant_id, now)

    def _redis_keys(self, tenant_id: str, now: datetime) -> tuple[str, str]:
        hour_bucket = now.strftime("%Y%m%d%H")
        day_bucket = now.strftime("%Y%m%d")
        prefix = os.getenv("LLM_BUDGET_REDIS_PREFIX", "llm_budget")
        return (
            f"{prefix}:{tenant_id}:hour:{hour_bucket}",
            f"{prefix}:{tenant_id}:day:{day_bucket}",
        )

    def _window_spend_locked(self, tenant_id: str, now: datetime) -> tuple[float, float]:
        self._prune_locked(tenant_id, now)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        hourly_spend = 0.0
        daily_spend = 0.0
        for ts, cost in self._usage_events[tenant_id]:
            if ts >= one_day_ago:
                daily_spend += cost
            if ts >= one_hour_ago:
                hourly_spend += cost

        return hourly_spend, daily_spend

    def _prune_locked(self, tenant_id: str, now: datetime) -> None:
        one_day_ago = now - timedelta(days=1)
        self._usage_events[tenant_id] = [
            event for event in self._usage_events[tenant_id] if event[0] >= one_day_ago
        ]

    def _record_event(self, tenant_id: str, action: str, reason: str) -> None:
        logger.warning(
            "LLM budget guardrail triggered",
            extra={"tenant_id": tenant_id, "action": action, "reason": reason},
        )
        metrics = get_metrics()
        if metrics:
            metrics.increment_llm_budget_guardrail_event(
                tenant_id=tenant_id,
                action=action,
                reason=reason,
            )


_budget_guardrails: LLMBudgetGuardrails | None = None


def get_llm_budget_guardrails() -> LLMBudgetGuardrails:
    """Return process-wide budget guardrails singleton."""
    global _budget_guardrails
    if _budget_guardrails is None:
        _budget_guardrails = LLMBudgetGuardrails()
    return _budget_guardrails
