"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.connector."""

from __future__ import annotations

from layer4_agents.integration.connectors.connector import (
    CRMConnector,
    CRMWriteConnector,
)

__all__ = ["CRMConnector", "CRMWriteConnector"]