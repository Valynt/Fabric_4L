from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from .observations import (
    ErrorClass,
    ObservedStatus,
    SyncObservation,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class OperationalStatus(StrEnum):
    """Operational state of an external connection."""

    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    RUNNING = "running"
    IDLE = "idle"




STATE_TRANSITIONS: dict[OperationalStatus, set[OperationalStatus]] = {
    OperationalStatus.IDLE: {
        OperationalStatus.IDLE,
        OperationalStatus.RUNNING,
        OperationalStatus.READY,
        OperationalStatus.BLOCKED,
    },
    OperationalStatus.RUNNING: {
        OperationalStatus.RUNNING,
        OperationalStatus.READY,
        OperationalStatus.DEGRADED,
        OperationalStatus.BLOCKED,
        OperationalStatus.IDLE,
    },
    OperationalStatus.READY: {
        OperationalStatus.READY,
        OperationalStatus.RUNNING,
        OperationalStatus.DEGRADED,
        OperationalStatus.BLOCKED,
    },
    OperationalStatus.DEGRADED: {
        OperationalStatus.DEGRADED,
        OperationalStatus.RUNNING,
        OperationalStatus.READY,
        OperationalStatus.BLOCKED,
    },
    OperationalStatus.BLOCKED: {
        OperationalStatus.BLOCKED,
        OperationalStatus.READY,
        OperationalStatus.DEGRADED,
    },
}


class ConnectionState:
    """Computed state output from the reducer."""

    def __init__(
        self,
        operational_status: OperationalStatus,
        observed_sync_status: str,
        error_class: ErrorClass,
        last_known_good_at: datetime | None,
        status: str,
    ) -> None:
        self.operational_status = operational_status
        self.observed_sync_status = observed_sync_status
        self.error_class = error_class
        self.last_known_good_at = last_known_good_at
        self.status = status

    def as_dict(self) -> dict[str, Any]:
        return {
            "operational_status": self.operational_status.value,
            "observed_sync_status": self.observed_sync_status,
            "error_class": self.error_class.value,
            "last_known_good_at": self.last_known_good_at,
            "status": self.status,
        }


def _resolve_observation(
    observation: SyncObservation | ObservedStatus,
    error_class: ErrorClass | None = None,
) -> tuple[ObservedStatus, ErrorClass]:
    """Support both new SyncObservation wrappers and legacy ObservedStatus enums."""
    if isinstance(observation, SyncObservation):
        return observation.observed_status, observation.error_class
    # Legacy path: callers passing the raw ObservedStatus enum.
    return observation, error_class or ErrorClass.NONE


def reduce(
    observed: SyncObservation | ObservedStatus,
    current: OperationalStatus | None,
    error_class: ErrorClass | None = None,
    last_known_good_at: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pure function: compute the next connection state from an observed event.

    Args:
        observed: A SyncObservation dataclass or, for legacy callers, an
            ObservedStatus enum.
        current: The current operational_status (None for a never-synced integration).
        error_class: Class of the most recent failure, used only with the legacy
            ObservedStatus path.
        last_known_good_at: Timestamp of the last fully successful sync.
        now: Clock override for deterministic tests.

    Returns:
        A mapping with reducer-derived fields and a legacy status shim.
    """
    now = now or datetime.now(UTC)
    current = current or OperationalStatus.IDLE

    observed, resolved_error_class = _resolve_observation(observed, error_class)

    if observed == ObservedStatus.SYNC_STARTED:
        # Starting a sync only updates the observed status; operational state
        # and LKG are intentionally untouched.
        next_state = current
    elif observed == ObservedStatus.RUNNING:
        next_state = OperationalStatus.RUNNING
    elif observed == ObservedStatus.SUCCESS:
        next_state = OperationalStatus.READY
        if resolved_error_class == ErrorClass.NONE:
            last_known_good_at = now
    elif observed == ObservedStatus.PARTIAL:
        next_state = OperationalStatus.DEGRADED
    elif observed == ObservedStatus.FAILURE:
        if resolved_error_class == ErrorClass.MAPPING:
            next_state = OperationalStatus.DEGRADED
        elif resolved_error_class in {
            ErrorClass.AUTH,
            ErrorClass.PERMISSION,
            ErrorClass.PERMANENT,
        }:
            # Escalate: degrade a healthy connection first; block only after a
            # prior degradation.
            next_state = (
                OperationalStatus.BLOCKED
                if current in {OperationalStatus.DEGRADED, OperationalStatus.BLOCKED}
                else OperationalStatus.DEGRADED
            )
        else:
            next_state = OperationalStatus.DEGRADED
    elif observed == ObservedStatus.SYNC_INTERRUPTED:
        # A worker/lease interruption is not evidence the provider is broken.
        # It is capped at DEGRADED and must never produce BLOCKED.
        next_state = OperationalStatus.DEGRADED
    elif observed == ObservedStatus.IDLE:
        next_state = current if current != OperationalStatus.RUNNING else OperationalStatus.IDLE
    else:
        next_state = current

    # Enforce allowed transitions; if disallowed, degrade rather than silently jumping.
    if next_state not in STATE_TRANSITIONS.get(current, set()):
        next_state = OperationalStatus.DEGRADED

    legacy_status_map = {
        # Map the new operational states to existing IntegrationStatus values.
        OperationalStatus.READY: "idle",
        OperationalStatus.RUNNING: "running",
        OperationalStatus.DEGRADED: "degraded",
        OperationalStatus.BLOCKED: "failed",
        OperationalStatus.IDLE: "idle",
    }

    return {
        "operational_status": next_state.value,
        "observed_sync_status": observed.value,
        "error_class": resolved_error_class.value,
        "last_known_good_at": last_known_good_at,
        "status": legacy_status_map[next_state],
    }


async def apply_observation(
    session: AsyncSession,
    integration: Any,
    observation: SyncObservation | ObservedStatus,
    *,
    error_class: ErrorClass | None = None,
    now: datetime | None = None,
) -> ConnectionState:
    """The single sanctioned write path for connection state on an Integration row.

    Applies the reducer to the current integration state, mutates the
    integration's reducer columns and legacy status shim in place, and flushes
    the session so the state write is persisted within the caller's transaction.

    Contract:
        This function owns the flush; the caller owns the commit. This guarantees
        the state write cannot be silently dropped by a caller that forgets to
        flush, while allowing callers to batch an observation with sync work in
        one transaction.

    Args:
        session: The SQLAlchemy AsyncSession for persistence.
        integration: An Integration model instance.
        observation: A SyncObservation or legacy ObservedStatus enum.
        error_class: Legacy error class used only with ObservedStatus enum.
        now: Clock override for deterministic tests.

    Returns:
        The computed ConnectionState.
    """
    current = (
        OperationalStatus(integration.operational_status)
        if integration.operational_status
        else None
    )
    reduced = reduce(
        observed=observation,
        current=current,
        error_class=error_class,
        last_known_good_at=integration.last_known_good_at,
        now=now,
    )
    state = ConnectionState(
        operational_status=OperationalStatus(reduced["operational_status"]),
        observed_sync_status=reduced["observed_sync_status"],
        error_class=ErrorClass(reduced["error_class"]),
        last_known_good_at=reduced["last_known_good_at"],
        status=reduced["status"],
    )
    integration.observed_sync_status = state.observed_sync_status
    integration.operational_status = state.operational_status.value
    integration.error_class = state.error_class.value
    integration.last_known_good_at = state.last_known_good_at
    integration.sync_status = state.status
    await session.flush()
    return state
