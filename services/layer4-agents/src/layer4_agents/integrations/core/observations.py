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
def sync_started(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.SYNC_STARTED, ErrorClass.NONE, message)


def sync_succeeded(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.SUCCESS, ErrorClass.NONE, message)


def sync_partial(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.PARTIAL, ErrorClass.TRANSIENT, message)


def sync_failed(
    error_class: ErrorClass = ErrorClass.TRANSIENT, message: str | None = None
) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, error_class, message)


def sync_interrupted(message: str | None = None) -> SyncObservation:
    return SyncObservation(
        ObservedStatus.SYNC_INTERRUPTED, ErrorClass.INTERRUPTED, message
    )


def transient_failure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.TRANSIENT, message)


def auth_failure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.AUTH, message)


def permission_failure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.PERMISSION, message)


def mapping_failure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.MAPPING, message)


def permanent_failure(message: str | None = None) -> SyncObservation:
    return SyncObservation(ObservedStatus.FAILURE, ErrorClass.PERMANENT, message)

# Backward-compatible aliases for existing integrations and external consumers.
SyncStarted = sync_started
SyncSucceeded = sync_succeeded
SyncPartial = sync_partial
SyncFailed = sync_failed
SyncInterrupted = sync_interrupted
TransientFailure = transient_failure
AuthFailure = auth_failure
PermissionFailure = permission_failure
MappingFailure = mapping_failure
PermanentFailure = permanent_failure
