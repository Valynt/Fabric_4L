"""`value_fabric` namespace package bootstrap (PEP 420 implicit namespace).

This package now uses PEP 420 implicit namespace packaging.
Namespace packages are discovered automatically from the filesystem without
explicit __path__ manipulation. All canonical `value_fabric.*` modules live under
package-local `src/` directories and are resolved via the configured pythonpath.

Deprecated: The value_fabric.layer* shims are deprecated and will be removed before 2026-09-30.
"""

from __future__ import annotations

import pkgutil
from pathlib import Path

__path__ = pkgutil.extend_path(__path__, __name__)

# Only register the shared package path; layer shims are deprecated
_REPO_ROOT = Path(__file__).resolve().parent.parent
_shared_path = _REPO_ROOT / "packages" / "shared" / "src" / "value_fabric"
if _shared_path.exists() and str(_shared_path) not in __path__:
    __path__.append(str(_shared_path))
