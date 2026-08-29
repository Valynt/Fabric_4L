"""Legacy top-level re-export of the CRM connector protocols.

The canonical definitions live in ``connectors.core.connector``; this module
re-exports them for compatibility with code that imports from the top-level
``integration.connectors`` package. Use ``core.connector`` directly in new code.
"""

from __future__ import annotations

from .core.connector import CRMConnector, CRMWriteConnector

__all__ = ["CRMConnector", "CRMWriteConnector"]
