"""Priority queue implementation for crawl job scheduling.

Manages URL queue with priority-based ordering and rate limiting.
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.testability import Clock, SystemClock

from ..shared.config import settings


class PriorityScheduler_get_queue_statsResult(TypedDictModel):
    domains_pending: Any
    in_progress: dict[str, Any]
    top_domains: dict[str, Any]
    total_pending: Any

logger = structlog.get_logger()


@dataclass(order=True)
class QueueItem:
    """Priority queue item for URL scheduling."""

    priority: int  # Lower is higher priority
    timestamp: datetime = field(compare=True)
    url: str = field(compare=False)
    domain: str = field(compare=False)
    job_id: str = field(compare=False)
    depth: int = field(compare=False)
    retry_count: int = field(compare=False, default=0)

    def __post_init__(self):
        # Ensure timestamp is set
        if not self.timestamp:
            self.timestamp = datetime.now(UTC)


class PriorityScheduler:
    """Priority-based crawl scheduler with rate limiting."""

    def __init__(
        self,
        per_domain_delay: float | None = None,
        jitter_percent: float | None = None,
        clock: Clock | None = None,
    ):
        self.per_domain_delay = per_domain_delay or settings.per_domain_delay_seconds
        self.jitter_percent = jitter_percent or settings.jitter_percent
        self._clock: Clock = clock or SystemClock()

        # Domain rate limiting
        self._last_request_time: dict[str, float] = defaultdict(float)

        # Priority queue (implemented as sorted list for simplicity)
        # In production, use a proper priority queue (Redis sorted set, heapq)
        self._queue: list[QueueItem] = []

        # Track domains being processed
        self._in_progress: dict[str, int] = defaultdict(int)

    def add_url(
        self,
        job_id: str,
        url: str,
        domain: str,
        depth: int = 0,
        priority: int = 5,
        base_priority: int = 0,
    ) -> QueueItem:
        """Add a URL to the queue.

        Priority is calculated as base_priority + depth + custom priority.
        Lower values = higher priority.

        Args:
            job_id: Parent crawl job ID
            url: URL to crawl
            domain: Domain name
            depth: Crawl depth from start URL
            priority: Custom priority (1=high, 10=low)
            base_priority: Base priority for this job

        Returns:
            Created QueueItem
        """
        # Calculate effective priority (lower = sooner)
        effective_priority = base_priority + depth + priority

        item = QueueItem(
            priority=effective_priority,
            timestamp=self._clock.now(),
            url=url,
            domain=domain,
            depth=depth,
            job_id=job_id,
        )

        self._queue.append(item)
        self._queue.sort()  # Keep sorted by priority

        logger.debug(
            "URL added to queue",
            url=url,
            domain=domain,
            priority=effective_priority,
            queue_size=len(self._queue),
        )

        return item

    def get_next_url(self, respect_rate_limits: bool = True) -> QueueItem | None:
        """Get the next URL to crawl, respecting rate limits.

        Args:
            respect_rate_limits: Whether to enforce per-domain delays

        Returns:
            QueueItem if available and rate limit allows, None otherwise
        """
        if not self._queue:
            return None

        current_time = self._clock.monotonic()

        # Find the highest priority item that respects rate limits
        for i, item in enumerate(self._queue):
            domain = item.domain

            if respect_rate_limits:
                last_request = self._last_request_time[domain]
                elapsed = current_time - last_request

                # Calculate required delay with jitter
                delay = self.per_domain_delay
                if self.jitter_percent > 0:
                    jitter = delay * (self.jitter_percent / 100) * (2 * random.random() - 1)
                    delay += jitter

                if elapsed < delay:
                    # Rate limit in effect, skip this domain
                    continue

            # This item is ready to process
            self._queue.pop(i)
            self._last_request_time[domain] = current_time
            self._in_progress[domain] += 1

            logger.debug(
                "URL dequeued for crawling",
                url=item.url,
                domain=item.domain,
                priority=item.priority,
            )

            return item

        # No items ready (all rate limited)
        return None

    def mark_complete(self, item: QueueItem):
        """Mark a URL as completed."""
        self._in_progress[item.domain] -= 1
        if self._in_progress[item.domain] <= 0:
            del self._in_progress[item.domain]

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        domain_counts = defaultdict(int)
        for item in self._queue:
            domain_counts[item.domain] += 1

        return PriorityScheduler_get_queue_statsResult.model_validate({
            "total_pending": len(self._queue),
            "domains_pending": len(domain_counts),
            "in_progress": dict(self._in_progress),
            "top_domains": dict(
                sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }).model_dump()


    def get_estimated_wait_time(self, domain: str) -> float:
        """Estimate wait time before a domain can be crawled again."""
        last_request = self._last_request_time.get(domain, 0)
        elapsed = self._clock.monotonic() - last_request
        delay = self.per_domain_delay

        if elapsed >= delay:
            return 0.0

        return delay - elapsed

    def clear(self):
        """Clear the queue."""
        self._queue.clear()
        self._last_request_time.clear()
        self._in_progress.clear()


class RoundRobinScheduler(PriorityScheduler):
    """Round-robin scheduler that cycles through domains fairly.

    Ensures no single domain dominates the crawl queue.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._domain_order: list[str] = []
        self._current_domain_index = 0

    def get_next_url(self, respect_rate_limits: bool = True) -> QueueItem | None:
        """Get next URL using round-robin domain selection."""
        if not self._queue:
            return None

        # Group by domain
        domain_groups: dict[str, list[QueueItem]] = defaultdict(list)
        for item in self._queue:
            domain_groups[item.domain].append(item)

        # Update domain order if changed
        if set(domain_groups.keys()) != set(self._domain_order):
            self._domain_order = list(domain_groups.keys())

        if not self._domain_order:
            return None

        current_time = self._clock.monotonic()
        checked_domains = 0

        while checked_domains < len(self._domain_order):
            domain = self._domain_order[self._current_domain_index]
            self._current_domain_index = (self._current_domain_index + 1) % len(self._domain_order)
            checked_domains += 1

            if not domain_groups[domain]:
                continue

            # Check rate limit
            if respect_rate_limits:
                last_request = self._last_request_time.get(domain, 0)
                elapsed = current_time - last_request
                delay = self.per_domain_delay

                if elapsed < delay:
                    continue  # Skip this domain for now

            # Get highest priority item for this domain
            items = domain_groups[domain]
            items.sort()  # Sort by priority
            item = items[0]

            # Remove from main queue
            self._queue.remove(item)
            self._last_request_time[domain] = current_time
            self._in_progress[domain] += 1

            return item

        return None  # All domains rate limited
