"""Deprecated compatibility entrypoint for Layer 4 startup tests.

Canonical app import path: ``value_fabric.layer4.api.main:app``.
This shim remains only for legacy callers during the deprecation window.
"""

from __future__ import annotations

import warnings

from value_fabric.shared.security.config import validate_all_controls

validate_all_controls()

warnings.warn(
    "'layer4_agents.main' is deprecated; import 'value_fabric.layer4.api.main' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from value_fabric.layer4.api.main import app

__all__ = ["app"]
