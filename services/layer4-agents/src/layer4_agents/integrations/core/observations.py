"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core.observations."""

from __future__ import annotations

from layer4_agents.integration.connectors.core.observations import (
    ErrorClass,
    ObservedStatus,
    SyncObservation,
    sync_failed,
    sync_interrupted,
    sync_partial,
    sync_started,
    sync_succeeded,
)

__all__ = [
    "ErrorClass",
    "ObservedStatus",
    "SyncObservation",
    "sync_failed",
    "sync_interrupted",
    "sync_partial",
    "sync_started",
    "sync_succeeded",
]