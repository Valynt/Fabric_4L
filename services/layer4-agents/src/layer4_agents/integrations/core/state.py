"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core.state."""

from __future__ import annotations

from layer4_agents.integration.connectors.core.state import (
    ConnectionState,
    OperationalStatus,
    STATE_TRANSITIONS,
    apply_observation,
    reduce,
)

__all__ = [
    "OperationalStatus",
    "STATE_TRANSITIONS",
    "ConnectionState",
    "reduce",
    "apply_observation",
]