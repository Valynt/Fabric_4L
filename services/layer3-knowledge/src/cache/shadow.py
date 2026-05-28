from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Shadow comparison utilities for CachePort parity pilots.

The comparator is deliberately passive from the application's perspective: the
primary provider result is always returned, while shadow mismatches are recorded
for tests or future staging telemetry.
"""


from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..cache.ports import CachePort


@dataclass(frozen=True)
class CacheParityMismatch:
    """A single observed primary-vs-shadow divergence."""

    operation: str
    key: str
    primary_result: Any
    shadow_result: Any


@dataclass
class ShadowCacheComparator:
    """Run paired CachePort operations and retain mismatch evidence."""

    primary: CachePort
    shadow: CachePort
    mismatches: list[CacheParityMismatch] = field(default_factory=list)

    async def _compare(
        self,
        operation: str,
        key: str,
        primary_call: Callable[[], Awaitable[Any]],
        shadow_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        primary_result = await primary_call()
        shadow_result = await shadow_call()
        if primary_result != shadow_result:
            self.mismatches.append(
                CacheParityMismatch(
                    operation=operation,
                    key=key,
                    primary_result=primary_result,
                    shadow_result=shadow_result,
                )
            )
        return primary_result

    async def get(self, key: str) -> Any | None:
        return await self._compare(
            "get",
            key,
            lambda: self.primary.get(key),
            lambda: self.shadow.get(key),
        )

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self._compare(
            "set",
            key,
            lambda: self.primary.set(key, value, ttl=ttl),
            lambda: self.shadow.set(key, value, ttl=ttl),
        )

    async def delete(self, key: str) -> bool:
        return await self._compare(
            "delete",
            key,
            lambda: self.primary.delete(key),
            lambda: self.shadow.delete(key),
        )

    async def clear_pattern(self, pattern: str) -> int:
        return await self._compare(
            "clear_pattern",
            pattern,
            lambda: self.primary.clear_pattern(pattern),
            lambda: self.shadow.clear_pattern(pattern),
        )

    async def exists(self, key: str) -> bool:
        return await self._compare(
            "exists",
            key,
            lambda: self.primary.exists(key),
            lambda: self.shadow.exists(key),
        )

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        return await self._compare(
            "increment",
            key,
            lambda: self.primary.increment(key, amount=amount, ttl=ttl),
            lambda: self.shadow.increment(key, amount=amount, ttl=ttl),
        )

    async def get_stats(self) -> dict[str, Any]:
        primary_result = await self.primary.get_stats()
        shadow_result = await self.shadow.get_stats()
        primary_hits = primary_result.get("keyspace_hits") if isinstance(primary_result, dict) else None
        shadow_hits = shadow_result.get("keyspace_hits") if isinstance(shadow_result, dict) else None
        primary_misses = primary_result.get("keyspace_misses") if isinstance(primary_result, dict) else None
        shadow_misses = shadow_result.get("keyspace_misses") if isinstance(shadow_result, dict) else None
        if (primary_hits, primary_misses) != (shadow_hits, shadow_misses):
            self.mismatches.append(
                CacheParityMismatch(
                    operation="get_stats",
                    key="*",
                    primary_result=primary_result,
                    shadow_result=shadow_result,
                )
            )
        return primary_result
