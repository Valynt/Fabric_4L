"""Deprecated location; protocols moved to integrations.core.connector.

TODO(PR9): Delete this shim once all downstream imports migrate to
integrations.core.connector.
"""

from __future__ import annotations

from .core.connector import CRMConnector, CRMWriteConnector

__all__ = ["CRMConnector", "CRMWriteConnector"]
