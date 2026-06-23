"""Canonical-event replay helpers for cross-store consistency checks.

The production invariant is that PostgreSQL is the canonical store for mutable
business metadata and outbox events. Neo4j, vector indexes, object stores, and
embedding stores are derived projections that must be rebuildable from those
canonical events. This module intentionally keeps the replay contract small so
service-specific adapters can bind real SQLAlchemy/Neo4j/vector/object-store
clients without coupling the shared consistency gate to one backend.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4


class ProjectionStatus(StrEnum):
    """Lifecycle for one target projection of one canonical event."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    """Durable event emitted from a canonical PostgreSQL write."""

    tenant_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: Mapping[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ProjectionAttempt:
    """Replay state for a single event/target pair."""

    event_id: UUID
    target: str
    status: ProjectionStatus = ProjectionStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class DerivedProjectionObservation:
    """Observed derived record used to detect projections without a source event."""

    target: str
    tenant_id: UUID
    aggregate_type: str
    aggregate_id: str

    @property
    def canonical_key(self) -> tuple[UUID, str, str]:
        return (self.tenant_id, self.aggregate_type, self.aggregate_id)


class ProjectionTarget(Protocol):
    """Service adapter that idempotently applies one derived projection."""

    name: str

    def project(self, event: CanonicalEvent) -> None:
        """Apply the projection for ``event``.

        Implementations must be idempotent: re-applying the same canonical event
        for the same tenant/aggregate must converge to the same derived state.
        """


class InMemoryProjectionOutbox:
    """Small event/outbox store used by integration gates and adapter tests.

    Real services should persist equivalent state in PostgreSQL beside the
    canonical write. The behavior here mirrors the production contract: events
    are appended once, target attempts are tracked independently, and dead-letter
    rows remain inspectable.
    """

    def __init__(self) -> None:
        self._events: dict[UUID, CanonicalEvent] = {}
        self._attempts: dict[tuple[UUID, str], ProjectionAttempt] = {}

    def append(self, event: CanonicalEvent, targets: Sequence[str]) -> None:
        """Record a canonical event and ensure target attempt rows exist.

        Re-appending an existing event is idempotent and will not reset applied
        or failed target state.
        """

        self._events.setdefault(event.event_id, event)
        for target in targets:
            self._attempts.setdefault(
                (event.event_id, target),
                ProjectionAttempt(event_id=event.event_id, target=target),
            )

    def get_event(self, event_id: UUID) -> CanonicalEvent | None:
        return self._events.get(event_id)

    def events(self) -> list[CanonicalEvent]:
        return list(self._events.values())

    def attempts(self) -> list[ProjectionAttempt]:
        return list(self._attempts.values())

    def attempt_for(self, event_id: UUID, target: str) -> ProjectionAttempt:
        return self._attempts[(event_id, target)]

    def pending_for(
        self, targets: Iterable[str]
    ) -> list[tuple[CanonicalEvent, ProjectionAttempt]]:
        target_names = set(targets)
        pending: list[tuple[CanonicalEvent, ProjectionAttempt]] = []
        for attempt in self._attempts.values():
            if attempt.target not in target_names:
                continue
            if attempt.status in {ProjectionStatus.PENDING, ProjectionStatus.FAILED}:
                event = self._events.get(attempt.event_id)
                if event is not None:
                    pending.append((event, attempt))
        return pending

    def mark_applied(self, attempt: ProjectionAttempt) -> None:
        attempt.status = ProjectionStatus.APPLIED
        attempt.last_error = None
        attempt.updated_at = datetime.now(UTC)

    def mark_failed(
        self, attempt: ProjectionAttempt, error: Exception, *, max_attempts: int
    ) -> None:
        attempt.attempts += 1
        attempt.last_error = f"{type(error).__name__}: projection_failed"
        attempt.status = (
            ProjectionStatus.DEAD_LETTER
            if attempt.attempts >= max_attempts
            else ProjectionStatus.FAILED
        )
        attempt.updated_at = datetime.now(UTC)

    def failed_or_dead_lettered(self) -> list[ProjectionAttempt]:
        return [
            attempt
            for attempt in self._attempts.values()
            if attempt.status in {ProjectionStatus.FAILED, ProjectionStatus.DEAD_LETTER}
        ]

    def canonical_keys(self) -> set[tuple[UUID, str, str]]:
        return {
            (event.tenant_id, event.aggregate_type, event.aggregate_id)
            for event in self._events.values()
        }


class CrossStoreProjectionRebuilder:
    """Replay canonical PostgreSQL events into derived stores."""

    def __init__(
        self,
        outbox: InMemoryProjectionOutbox,
        targets: Sequence[ProjectionTarget],
        *,
        max_attempts: int = 3,
    ) -> None:
        self.outbox = outbox
        self.targets = {target.name: target for target in targets}
        self.max_attempts = max_attempts

    def enqueue(self, event: CanonicalEvent) -> None:
        self.outbox.append(event, list(self.targets))

    def replay_pending(self) -> int:
        """Replay non-applied projections and return the number newly applied."""

        applied = 0
        for event, attempt in self.outbox.pending_for(self.targets):
            target = self.targets[attempt.target]
            try:
                target.project(event)
            # Adapter failures must be captured for operator inspection.
            except Exception as exc:  # noqa: BLE001
                self.outbox.mark_failed(attempt, exc, max_attempts=self.max_attempts)
                continue
            self.outbox.mark_applied(attempt)
            applied += 1
        return applied

    def rebuild_event(self, event_id: UUID) -> int:
        """Reset non-dead-letter attempts for one event and replay them."""

        event = self.outbox.get_event(event_id)
        if event is None:
            return 0
        for target_name in self.targets:
            attempt = self.outbox.attempt_for(event_id, target_name)
            if attempt.status != ProjectionStatus.DEAD_LETTER:
                attempt.status = ProjectionStatus.PENDING
        return self.replay_pending()

    def inspect_failed_projections(self) -> list[ProjectionAttempt]:
        return self.outbox.failed_or_dead_lettered()

    def find_orphaned_derived_projections(
        self,
        observations: Iterable[DerivedProjectionObservation],
    ) -> list[DerivedProjectionObservation]:
        """Return derived records that have no canonical PostgreSQL event key."""

        canonical_keys = self.outbox.canonical_keys()
        return [
            observation
            for observation in observations
            if observation.canonical_key not in canonical_keys
        ]
