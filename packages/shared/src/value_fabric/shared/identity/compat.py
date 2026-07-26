"""Module namespace-shim and singleton guard.

This module owns process-wide tenant-identity state (rate-limit buckets,
middleware class attributes, etc.). The monorepo namespace shim can load it
under multiple import paths (e.g. ``value_fabric.shared.identity.middleware``
and ``packages.shared.src.value_fabric.shared.identity.middleware``), which
would create independent copies of that state and silently break tenant
isolation. Force every logical import path to resolve to the same module
object.
"""

from __future__ import annotations

import sys
import types

# Legacy compat: set up ``shared`` and ``shared.identity`` module aliases so
# older import paths continue to resolve.
_shared_compat_module = sys.modules.setdefault("shared", types.ModuleType("shared"))
_identity_compat_module = sys.modules.setdefault(
    "shared.identity", types.ModuleType("shared.identity")
)
setattr(_shared_compat_module, "identity", _identity_compat_module)


def register_middleware_module(module_name: str) -> None:
    """Register the middleware module under the canonical path and compat aliases."""
    current_module = sys.modules[module_name]
    setattr(_identity_compat_module, "middleware", current_module)
    sys.modules.setdefault("shared.identity.middleware", current_module)

    _CANONICAL_MIDDLEWARE_MODULE = (
        "packages.shared.src.value_fabric.shared.identity.middleware"
    )
    if module_name != _CANONICAL_MIDDLEWARE_MODULE:
        sys.modules.setdefault(_CANONICAL_MIDDLEWARE_MODULE, current_module)
        sys.modules[module_name] = sys.modules[_CANONICAL_MIDDLEWARE_MODULE]
