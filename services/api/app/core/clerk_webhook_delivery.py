"""Webhook delivery semantics: idempotency, replay, and pending-event lifecycle.

This module owns the *delivery* state of Clerk webhook events, deliberately
separate from transport security (``app.core.clerk_webhook_signing``, Step 3).
It enforces the delivery rules from Step 4 of plans/clerk-implementation/plan.md:
a correctly signed duplicate never creates duplicate Fabric users or tenants
(idempotency by webhook event id / ``svix-id``), and events whose dependencies
are not yet available are retained in a recoverable pending state and retried
rather than dropped.

Delivered-event lifecycle (AC#4):
- ``processed``  — event fully applied; the canonical ``svix-id`` is recorded so
  any duplicate or replayed delivery is a no-op.
- ``pending``    — an event (usually a membership) referenced a user or
  organization that hasn't arrived yet. It is recorded with a first-seen time
  and an attempt count, and the handler returns a non-2xx so the sender retries.
- ``dead``       — terminal state after ``MAX_PENDING_ATTEMPTS`` attempts or
  ``MAX_PENDING_AGE_SECONDS`` of age. The event is dead-lettered (DLQ) once for
  operator recovery and observability, but is *not* hard-blocked: a later
  delivery (sender retry or operator replay via ``scripts/replay_clerk_webhooks.py``,
  which preserves the original event id per AC#3) can still recover by applying.

Retry trigger: the sender retries any non-2xx response with exponential backoff
(Svix/Clerk webhook semantics). A redelivery of the same ``svix-id`` re-enters
apply; if the missing dependency has meanwhile arrived the event is applied and
moved from pending to processed.
"""

from __future__ import annotations

import dataclasses
import threading
import time

# A pending event is given this many attempts before it is declared terminal.
MAX_PENDING_ATTEMPTS = 20
# A pending event older than this (seconds) is declared terminal regardless of
# how few attempts it has accrued.
MAX_PENDING_AGE_SECONDS = 86_400  # 24h
# DLQ reason recorded when a pending event reaches its terminal state.
DLQ_REASON_PENDING_EXHAUSTED = "pending_exhausted"


@dataclasses.dataclass(frozen=True)
class PendingEvent:
    """A delivery that referenced an as-yet-unavailable dependency."""

    event_id: str
    event_type: str
    first_seen: float
    attempts: int


@dataclasses.dataclass(frozen=True)
class PendingOutcome:
    """Result of recording a pending delivery."""

    #: True when the event is still retryable; False when it reached terminal.
    retryable: bool
    #: True only on the *transition* to the terminal (dead) state.
    transitioned_to_dead: bool


class WebhookDeliveryTracker:
    """Thread-safe, process-local owner of webhook delivery state.

    Consistent with the process-local dev adapter model (``AuthDirectory``,
    ``WebhookDLQ``); production deployments should back this with a durable,
    at-least-once store indexed by ``svix-id``.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processed: set[str] = set()
        self._pending: dict[str, PendingEvent] = {}
        self._dead_dlq_enqueued: set[str] = set()

    # ------------------------------------------------------------------
    # Processed / idempotency
    # ------------------------------------------------------------------
    def is_processed(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._processed

    def mark_processed(self, event_id: str, event_type: str | None = None) -> None:
        """Record that ``event_id`` was fully applied (dedup key)."""
        with self._lock:
            self._processed.add(event_id)
            self._pending.pop(event_id, None)
            self._dead_dlq_enqueued.discard(event_id)

    # ------------------------------------------------------------------
    # Pending / ordering lifecycle
    # ------------------------------------------------------------------
    def register_pending(self, event_id: str, event_type: str, *, now: float | None = None) -> PendingOutcome:
        """Record a delivery whose dependency is unavailable.

        Returns an outcome describing whether the event is still retryable and
        whether this call is the first transition to the terminal (dead) state.
        """
        now = time.time() if now is None else now
        with self._lock:
            existing = self._pending.get(event_id)
            if existing is None:
                self._pending[event_id] = PendingEvent(
                    event_id=event_id,
                    event_type=event_type,
                    first_seen=now,
                    attempts=1,
                )
                return PendingOutcome(retryable=True, transitioned_to_dead=False)

            attempts = existing.attempts + 1
            age = now - existing.first_seen
            updated = PendingEvent(
                event_id=existing.event_id,
                event_type=event_type,
                first_seen=existing.first_seen,
                attempts=attempts,
            )
            self._pending[event_id] = updated
            exhausted = attempts > MAX_PENDING_ATTEMPTS or age > MAX_PENDING_AGE_SECONDS
            if not exhausted:
                return PendingOutcome(retryable=True, transitioned_to_dead=False)
            if event_id in self._dead_dlq_enqueued:
                # Already terminal and dead-lettered; don't re-transition.
                return PendingOutcome(retryable=False, transitioned_to_dead=False)
            self._dead_dlq_enqueued.add(event_id)
            return PendingOutcome(retryable=False, transitioned_to_dead=True)

    def is_pending(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._pending

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, int]:
        """Return delivery-state counts for operators and health endpoints."""
        with self._lock:
            return {
                "processed": len(self._processed),
                "pending": len(self._pending),
                "dead_pending": len(self._dead_dlq_enqueued),
            }

    def pending_events(self) -> list[PendingEvent]:
        with self._lock:
            return list(self._pending.values())


# Process-level singleton (consistent with the other process-local stores).
_tracker: WebhookDeliveryTracker | None = None
_tracker_lock = threading.Lock()


def get_webhook_delivery_tracker() -> WebhookDeliveryTracker:
    """Return the shared ``WebhookDeliveryTracker`` singleton."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = WebhookDeliveryTracker()
    return _tracker


def reset_webhook_delivery_tracker() -> None:
    """Reset the shared tracker; intended for tests."""
    global _tracker
    with _tracker_lock:
        _tracker = None
