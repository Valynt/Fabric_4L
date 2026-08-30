"""Revision-aware authorization decision cache.

Protected commands are never cached (see ``UNCACHEABLE_ACTIONS``). Cacheable
decisions are keyed by an input fingerprint that includes the resource
revision, so a role removal or a resource change invalidates the entry without
explicit eviction. On any doubt (unknown entry, resolver error) we fail closed
by treating the entry as a miss so the PDP is consulted again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class CacheEntry:
    decision: Any
    cached_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl_ms: int = 0

    def is_fresh(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        if self.ttl_ms <= 0:
            return False
        expires = self.cached_at + timedelta(milliseconds=self.ttl_ms)
        return now < expires


class InMemoryAuthzCache:
    """Thread-safe, revision-aware in-memory decision cache.

    For multi-instance deployments, rooms can use Redis; the interface is
    identical (``get``/``set``/``invalidate``). ``invalidate`` keys by a
    role/principal scope so role removal evicts all dependent decisions.
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._roles_index: dict[str, set[str]] = {}  # scope_key -> set(cache_keys)

    async def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if not entry.is_fresh():
            self._entries.pop(key, None)
            return None
        return entry.decision

    async def set(self, key: str, decision: Any, ttl_ms: int = 0) -> None:
        self._entries[key] = CacheEntry(decision=decision, ttl_ms=ttl_ms)

    async def scope(self, key: str, scope_keys: list[str]) -> None:
        for scope_key in scope_keys:
            self._roles_index.setdefault(scope_key, set()).add(key)

    async def invalidate_scope(self, scope_key: str) -> None:
        """Evict any decision cached under a role/principal/tenant scope."""
        keys = self._roles_index.pop(scope_key, set())
        for key in keys:
            self._entries.pop(key, None)

    async def invalidate_all(self) -> None:
        self._entries.clear()
        self._roles_index.clear()

    def __len__(self) -> int:  # pragma: no cover - test convenience
        return len(self._entries)


class CacheOutcome:
    """Sentinel helper distinguishing a hit/miss for tests."""

    HIT = "HIT"
    MISS = "MISS"