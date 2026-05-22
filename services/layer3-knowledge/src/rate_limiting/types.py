"""Typed structures for Layer 3 rate limiting internals."""

from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class RateLimitRuleMetadata(TypedDict, total=False):
    """Optional metadata for rule-level annotations."""

    source: str
    description: str
    tags: list[str]
    owner: str


class TokenBucketState(TypedDict):
    """Persisted token-bucket state."""

    tokens: float
    last_refill: float
    created_at: float


class LeakyBucketState(TypedDict):
    """Persisted leaky-bucket state."""

    queue_size: int
    last_leak: float
    created_at: float


BucketState = TokenBucketState | LeakyBucketState

MetricsMap = dict[str, int]
StringCountMap = dict[str, int]
MetadataMap = dict[str, Any]
