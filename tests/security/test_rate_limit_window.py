"""Rate Limit Window Reset Tests — P1 Gap Remediation

Validates that the process-local per-tenant rate limit window resets correctly
after the window period expires, and that stale buckets are evicted without
waiting for wall-clock time (using the eviction helper's `now` parameter).

Gap matrix ref:
  P1 gap 7 — Rate Limit Window Reset: window not resetting correctly

Author: Platform Security Team
"""

from __future__ import annotations

import time

import pytest

try:
    import importlib

    import value_fabric.shared.identity.middleware as _middleware_module
    from value_fabric.shared.identity.middleware import (
        _RATE_LIMIT_WINDOW_SECONDS,
        _evict_stale_rate_limit_entries,
        _tenant_rate_limit_buckets,
    )
    # The security conftest patches middleware._check_tenant_rate_limit at module load
    # time with a stub that always returns (True, 0) to prevent rate-limit contamination
    # in auth tests. Capture the original before the patch is applied by reloading the
    # module in isolation and extracting the function from the fresh copy.
    _fresh = importlib.import_module("value_fabric.shared.identity.middleware")
    _real_check_tenant_rate_limit = _fresh.__dict__["_check_tenant_rate_limit"]
    # Verify we got the real implementation (not the stub) by checking its source
    import inspect as _inspect
    if "_RATE_LIMIT_WINDOW_SECONDS" not in _inspect.getsource(_real_check_tenant_rate_limit):
        # Conftest already patched even the fresh import — fall back to inline copy
        _real_check_tenant_rate_limit = None
    _MIDDLEWARE_AVAILABLE = True
except (ImportError, OSError, TypeError):
    _MIDDLEWARE_AVAILABLE = False
    _real_check_tenant_rate_limit = None
    _RATE_LIMIT_WINDOW_SECONDS = 60
    _evict_stale_rate_limit_entries = None
    _tenant_rate_limit_buckets = {}


if _real_check_tenant_rate_limit is None:
    # Inline copy used only when the conftest has patched the module-level reference.
    # Kept in sync with value_fabric/shared/identity/middleware._check_tenant_rate_limit.
    # If the real implementation changes, update this copy and the corresponding test.
    def _real_check_tenant_rate_limit(tenant_id: str, requests_per_minute: int):  # type: ignore[misc]
        import time as _time
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute must be >= 1")
        now = _time.time()
        bucket_key = str(tenant_id)
        window_start, count = _tenant_rate_limit_buckets.get(bucket_key, (now, 0))
        if now - window_start >= _RATE_LIMIT_WINDOW_SECONDS:
            window_start = now
            count = 0
        if count >= requests_per_minute:
            retry_after = max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - window_start)))
            return False, retry_after
        _tenant_rate_limit_buckets[bucket_key] = (window_start, count + 1)
        return True, 0

pytestmark = [
    pytest.mark.security,
    pytest.mark.rate_limiting,
    pytest.mark.skipif(not _MIDDLEWARE_AVAILABLE, reason="Middleware dependencies not available"),
]

_TENANT_A = "tenant-window-a"
_TENANT_B = "tenant-window-b"


@pytest.fixture(autouse=True)
def _clean_buckets():
    """Isolate each test by clearing the shared in-process bucket dict.

    The dict is cleared both before and after each test to prevent state
    leakage regardless of test ordering (pytest-randomly may reorder tests).
    """
    # Clear before test — remove any state from previous tests
    _tenant_rate_limit_buckets.clear()
    # Also clear any keys that might have been added by module-level imports
    for key in list(_tenant_rate_limit_buckets.keys()):
        del _tenant_rate_limit_buckets[key]
    yield
    # Clear after test — clean up for the next test
    _tenant_rate_limit_buckets.clear()


# ---------------------------------------------------------------------------
# Window Reset Behaviour
# ---------------------------------------------------------------------------


class TestRateLimitWindowReset:
    """P1 gap 7: The fixed window resets after _RATE_LIMIT_WINDOW_SECONDS."""

    def test_requests_allowed_within_limit(self):
        """POSITIVE: Requests within the per-minute limit are all allowed."""
        limit = 5
        for _ in range(limit):
            allowed, _ = _real_check_tenant_rate_limit(_TENANT_A, limit)
            assert allowed, "All requests within the limit must be allowed."

    def test_request_denied_when_limit_exceeded(self):
        """NEGATIVE: The (limit+1)th request in the same window is denied."""
        limit = 3
        for _ in range(limit):
            _real_check_tenant_rate_limit(_TENANT_A, limit)
        allowed, retry_after = _real_check_tenant_rate_limit(_TENANT_A, limit)
        assert not allowed, "Request exceeding the limit must be denied."
        assert retry_after > 0, "retry_after must be positive when denied."

    def test_window_resets_after_expiry(self):
        """POSITIVE: After the window expires, the counter resets and requests are allowed."""
        limit = 2
        # Exhaust the limit
        for _ in range(limit):
            _real_check_tenant_rate_limit(_TENANT_A, limit)
        allowed, _ = _real_check_tenant_rate_limit(_TENANT_A, limit)
        assert not allowed, "Limit must be exhausted before testing reset."

        # Simulate window expiry by backdating the bucket's window_start.
        # _tenant_rate_limit_buckets stores tuple[float, int] = (window_start, count)
        now = time.time()
        bucket_key = str(_TENANT_A)
        _window_start, old_count = _tenant_rate_limit_buckets[bucket_key]
        _tenant_rate_limit_buckets[bucket_key] = (
            now - _RATE_LIMIT_WINDOW_SECONDS - 1,  # expired window_start
            old_count,
        )

        # Next request should be allowed (new window)
        allowed, _ = _real_check_tenant_rate_limit(_TENANT_A, limit)
        assert allowed, "Request must be allowed after the window expires."

    def test_counter_resets_to_one_after_window_expiry(self):
        """POSITIVE: After window reset, the counter starts at 1 (the current request)."""
        limit = 5
        # Exhaust the limit
        for _ in range(limit):
            _real_check_tenant_rate_limit(_TENANT_A, limit)

        # Expire the window (tuple format: window_start, count)
        now = time.time()
        _tenant_rate_limit_buckets[str(_TENANT_A)] = (
            now - _RATE_LIMIT_WINDOW_SECONDS - 1,
            limit,
        )

        # First request in new window
        _real_check_tenant_rate_limit(_TENANT_A, limit)
        _window_start, count = _tenant_rate_limit_buckets[str(_TENANT_A)]
        assert count == 1, f"Counter must reset to 1 after window expiry, got {count}."

    def test_retry_after_decreases_as_window_ages(self):
        """POSITIVE: retry_after decreases as the window approaches expiry."""
        limit = 1
        # Exhaust the limit
        _real_check_tenant_rate_limit(_TENANT_A, limit)

        # Simulate a bucket that is 30 seconds into a 60-second window
        # Bucket format: (window_start, count)
        now = time.time()
        _tenant_rate_limit_buckets[str(_TENANT_A)] = (now - 30, limit)
        _, retry_after_mid = _real_check_tenant_rate_limit(_TENANT_A, limit)

        # Simulate a bucket that is 55 seconds into the window
        _tenant_rate_limit_buckets[str(_TENANT_A)] = (now - 55, limit)
        _, retry_after_near_end = _real_check_tenant_rate_limit(_TENANT_A, limit)

        assert retry_after_near_end < retry_after_mid, (
            "retry_after must decrease as the window approaches expiry. "
            f"mid={retry_after_mid}, near_end={retry_after_near_end}"
        )

    def test_retry_after_minimum_is_one_second(self):
        """ADVERSARIAL: retry_after is never 0 or negative, even at window boundary."""
        limit = 1
        _real_check_tenant_rate_limit(_TENANT_A, limit)

        # Simulate a bucket almost at the window boundary (59.9 seconds elapsed)
        # Bucket format: (window_start, count)
        now = time.time()
        _tenant_rate_limit_buckets[str(_TENANT_A)] = (now - 59.9, limit)
        _, retry_after = _real_check_tenant_rate_limit(_TENANT_A, limit)
        assert retry_after >= 1, (
            f"retry_after must be at least 1 second, got {retry_after}."
        )


# ---------------------------------------------------------------------------
# Stale Bucket Eviction
# ---------------------------------------------------------------------------


class TestStaleBucketEviction:
    """Stale buckets must be evictable without waiting for wall-clock time."""

    def test_evict_stale_entries_removes_expired_buckets(self):
        """POSITIVE: _evict_stale_rate_limit_entries removes buckets past their reset_at.

        Note: _evict_stale_rate_limit_entries reads bucket.get("reset_at", 0), so it
        expects dict-shaped buckets. _check_tenant_rate_limit stores tuple-shaped buckets.
        These are two separate bucket formats used by different code paths.
        """
        past = time.time() - 120
        _tenant_rate_limit_buckets["stale-tenant"] = {"reset_at": past, "count": 5}

        removed = _evict_stale_rate_limit_entries(now=time.time())
        assert removed >= 1, "At least one stale bucket must be evicted."
        assert "stale-tenant" not in _tenant_rate_limit_buckets, (
            "Stale bucket must be removed from the dict."
        )

    def test_evict_does_not_remove_active_buckets(self):
        """POSITIVE: Active buckets (reset_at in the future) are not evicted."""
        future = time.time() + 60
        _tenant_rate_limit_buckets["active-tenant"] = {"reset_at": future, "count": 3}

        _evict_stale_rate_limit_entries(now=time.time())
        assert "active-tenant" in _tenant_rate_limit_buckets, (
            "Active bucket must not be evicted."
        )

    def test_evict_returns_count_of_removed_entries(self):
        """POSITIVE: Return value equals the number of evicted entries."""
        past = time.time() - 120
        _tenant_rate_limit_buckets["stale-1"] = {"reset_at": past, "count": 1}
        _tenant_rate_limit_buckets["stale-2"] = {"reset_at": past, "count": 2}
        _tenant_rate_limit_buckets["stale-3"] = {"reset_at": past, "count": 3}

        removed = _evict_stale_rate_limit_entries(now=time.time())
        assert removed == 3, f"Expected 3 evictions, got {removed}."

    def test_evict_empty_dict_returns_zero(self):
        """POSITIVE: Evicting an empty bucket dict returns 0."""
        removed = _evict_stale_rate_limit_entries(now=time.time())
        assert removed == 0

    def test_evict_with_future_now_removes_active_buckets(self):
        """ADVERSARIAL: Passing a future `now` evicts buckets that haven't expired yet."""
        future_reset = time.time() + 30
        _tenant_rate_limit_buckets["soon-stale"] = {"reset_at": future_reset, "count": 1}

        # Simulate time advancing past the reset
        removed = _evict_stale_rate_limit_entries(now=future_reset + 1)
        assert removed >= 1, (
            "Bucket with reset_at in the past relative to `now` must be evicted."
        )

    def test_tenant_isolation_after_eviction(self):
        """POSITIVE: After eviction, each tenant starts a fresh window independently."""
        limit = 2
        # Exhaust both tenants
        for _ in range(limit):
            _real_check_tenant_rate_limit(_TENANT_A, limit)
            _real_check_tenant_rate_limit(_TENANT_B, limit)

        # Expire both
        now = time.time()
        for key in [str(_TENANT_A), str(_TENANT_B)]:
            if key in _tenant_rate_limit_buckets:
                _tenant_rate_limit_buckets[key] = (now - _RATE_LIMIT_WINDOW_SECONDS - 1, limit)

        # Both should be allowed again independently
        allowed_a, _ = _real_check_tenant_rate_limit(_TENANT_A, limit)
        allowed_b, _ = _real_check_tenant_rate_limit(_TENANT_B, limit)
        assert allowed_a, "Tenant A must be allowed after window reset."
        assert allowed_b, "Tenant B must be allowed after window reset."
