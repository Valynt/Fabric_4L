"""Deprecated compatibility shim for legacy ``layer4_agents`` imports.

Canonical Layer 4 runtime modules live under ``value_fabric.layer4`` and are
served from ``services/layer4-agents/src`` via the canonical package shim.

Deprecation timeline:
- Deprecated: 2026-05-12
- Planned removal review: 2026-09-30

Use ``value_fabric.layer4`` for all new imports.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'layer4_agents' is deprecated. Use 'value_fabric.layer4' instead.",
    DeprecationWarning,
    stacklevel=2,
)
