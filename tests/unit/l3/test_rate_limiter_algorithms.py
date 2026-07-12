"""Unit tests for Layer 3 rate-limiting algorithms (P0-004)."""

from __future__ import annotations

import time

import pytest
from rate_limiting.manager import (
    FixedWindow,
    LeakyBucket,
    SlidingWindow,
    TokenBucket,
)

pytestmark = [pytest.mark.unit]


class TestTokenBucket:
    """Token bucket algorithm tests."""

    def test_consume_within_capacity(self) -> None:
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.consume(1) is True
        assert bucket.consume(4) is True

    def test_consume_exceeds_capacity(self) -> None:
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.consume(6) is False

    def test_refill_over_time(self) -> None:
        bucket = TokenBucket(capacity=2, refill_rate=10.0)
        assert bucket.consume(2) is True
        assert bucket.consume(1) is False
        time.sleep(0.15)
        assert bucket.consume(1) is True

    def test_time_until_refill_zero_when_sufficient(self) -> None:
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.time_until_refill(1) == 0.0

    def test_time_until_refill_positive_when_empty(self) -> None:
        bucket = TokenBucket(capacity=1, refill_rate=10.0)
        bucket.consume(1)
        wait = bucket.time_until_refill(1)
        assert wait > 0.0

    def test_capacity_never_exceeds_max(self) -> None:
        bucket = TokenBucket(capacity=2, refill_rate=100.0)
        bucket.consume(2)
        time.sleep(0.1)
        bucket.consume(1)
        assert bucket.tokens <= 2


class TestSlidingWindow:
    """Sliding window algorithm tests."""

    def test_allows_requests_within_limit(self) -> None:
        window = SlidingWindow(limit=3, window_seconds=60)
        assert window.is_allowed() is True
        assert window.is_allowed() is True
        assert window.is_allowed() is True

    def test_rejects_when_limit_exceeded(self) -> None:
        window = SlidingWindow(limit=2, window_seconds=60)
        window.is_allowed()
        window.is_allowed()
        assert window.is_allowed() is False

    def test_window_slides_over_time(self) -> None:
        window = SlidingWindow(limit=1, window_seconds=0.1)
        assert window.is_allowed() is True
        assert window.is_allowed() is False
        time.sleep(0.15)
        assert window.is_allowed() is True

    def test_time_until_reset_zero_when_empty(self) -> None:
        window = SlidingWindow(limit=3, window_seconds=60)
        assert window.time_until_reset() == 0.0

    def test_time_until_reset_positive_when_requests_exist(self) -> None:
        window = SlidingWindow(limit=3, window_seconds=60)
        window.is_allowed()
        reset = window.time_until_reset()
        assert reset > 0.0
        assert reset <= 60.0

    def test_old_requests_purged(self) -> None:
        window = SlidingWindow(limit=2, window_seconds=0.1)
        window.is_allowed()
        time.sleep(0.15)
        window.is_allowed()
        assert window.is_allowed() is True  # first request expired


class TestFixedWindow:
    """Fixed window algorithm tests."""

    def test_allows_requests_within_limit(self) -> None:
        window = FixedWindow(limit=3, window_seconds=60)
        assert window.is_allowed() is True
        assert window.is_allowed() is True
        assert window.is_allowed() is True

    def test_rejects_when_limit_exceeded(self) -> None:
        window = FixedWindow(limit=2, window_seconds=60)
        window.is_allowed()
        window.is_allowed()
        assert window.is_allowed() is False

    def test_resets_after_window_expires(self) -> None:
        window = FixedWindow(limit=1, window_seconds=0.1)
        assert window.is_allowed() is True
        assert window.is_allowed() is False
        time.sleep(0.15)
        assert window.is_allowed() is True

    def test_time_until_reset_zero_at_start(self) -> None:
        window = FixedWindow(limit=3, window_seconds=60)
        reset = window.time_until_reset()
        assert reset > 0.0
        assert reset <= 60.0

    def test_count_increments_correctly(self) -> None:
        window = FixedWindow(limit=5, window_seconds=60)
        for _ in range(3):
            window.is_allowed()
        assert window.count == 3


class TestLeakyBucket:
    """Leaky bucket algorithm tests."""

    def test_allows_within_capacity(self) -> None:
        bucket = LeakyBucket(capacity=3, leak_rate=10.0)
        assert bucket.is_allowed() is True
        assert bucket.is_allowed() is True
        assert bucket.is_allowed() is True

    def test_rejects_when_full(self) -> None:
        bucket = LeakyBucket(capacity=2, leak_rate=10.0)
        bucket.is_allowed()
        bucket.is_allowed()
        assert bucket.is_allowed() is False

    def test_leaks_over_time(self) -> None:
        bucket = LeakyBucket(capacity=1, leak_rate=10.0)
        bucket.is_allowed()
        assert bucket.is_allowed() is False
        time.sleep(0.15)
        assert bucket.is_allowed() is True

    def test_queue_size_tracked(self) -> None:
        bucket = LeakyBucket(capacity=5, leak_rate=1.0)
        for _ in range(3):
            bucket.is_allowed()
        assert len(bucket.queue) == 3

    def test_last_leak_updated(self) -> None:
        bucket = LeakyBucket(capacity=5, leak_rate=1.0)
        before = bucket.last_leak
        time.sleep(0.01)
        bucket.is_allowed()
        assert bucket.last_leak > before
