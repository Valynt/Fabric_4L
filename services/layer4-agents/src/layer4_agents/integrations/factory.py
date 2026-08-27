"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.factory."""

from __future__ import annotations

from layer4_agents.integration.connectors.factory import (
    get_connector,
    get_write_connector,
)

__all__ = ["get_connector", "get_write_connector"]