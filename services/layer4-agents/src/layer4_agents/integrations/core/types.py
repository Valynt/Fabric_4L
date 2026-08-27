"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core.types."""

from __future__ import annotations

from layer4_agents.integration.connectors.core.types import (
    CRMModel,
    CRMOperationResult,
    CanonicalRecord,
    SyncCursor,
)

__all__ = ["CRMModel", "CanonicalRecord", "SyncCursor", "CRMOperationResult"]