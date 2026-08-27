"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core.connector."""

from __future__ import annotations

from layer4_agents.integration.connectors.core.connector import (
    CRMConnector,
    CRMWriteConnector,
)

__all__ = ["CRMConnector", "CRMWriteConnector"]