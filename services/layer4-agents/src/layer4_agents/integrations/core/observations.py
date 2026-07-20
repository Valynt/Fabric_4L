from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorClass(StrEnum):
    """Taxonomy class for the most recent failure."""

    NONE = "none"
    TRANSIENT = "transient"
    AUTH = "auth"
    PERMISSION = "permission"
    MAPPING = "mapping"
    PERMANENT = "permanent"
    INTERRUPTED = "interrupted"


class ObservedStatus(StrEnum):
    """Status observed from a single sync/connection event."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    RUNNING = "running"
    IDLE = "idle"
    SYNC_STARTED = "sync_started"
    SYNC_INTERRUPTED = "sync_interrupted"


@dataclass(frozen=True)
class SyncObservation:
    """A single observation used to drive the connection-state reducer.

    Producers (scheduler, job runner, sync service, webhooks, future SyncEngine)
    construct observations; the reducer consumes them. This dataclass keeps the
    observation surface small and explicit.
    """

    observed_status: ObservedStatus
    error_class: ErrorClass = ErrorClass.NONE
    message: str | None = None


# Convenience constructors so producers read like domain events rather than
# enum assemblies. They return plain SyncObservation instances.
def SyncStarted(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.SYNC_STARTED, ErrorClass.NONE, message)


def SyncSucceeded(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.SUCCESS, ErrorClass.NONE, message)


def SyncPartial(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.PARTIAL, ErrorClass.TRANSIENT, message)


def SyncFailed(
    error_class: ErrorClass = ErrorClass.TRANSIENT, message: str | None = None
) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, error_class, message)


def SyncInterrupted(message: str | None = None) -> SyncObservation:
    return SyncObservation(
        ObservedStatus.SYNC_INTERRUPTED, ErrorClass.INTERRUPTED, message
    )


def TransientFailure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.TRANSIENT, message)


def AuthFailure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.AUTH, message)


def PermissionFailure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.PERMISSION, message)


def MappingFailure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.MAPPING, message)


def PermanentFailure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.PERMANENT, message)
