"""Redirect shim: value_fabric.layer1.* -> services/layer1-ingestion/src/layer1_ingestion/*.

Canonical Layer 1 code lives in ``services/layer1-ingestion/src/layer1_ingestion/``.
This shim appends the canonical package path to ``__path__`` so that
``import value_fabric.layer1.api.main`` resolves to the canonical tree.

**DEPRECATED:** Use canonical imports ``layer1_ingestion.*`` instead.
This facade will be removed in a future release.
"""

from __future__ import annotations

import warnings
from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_canonical_pkg: str = str(_repo_root / "services" / "layer1-ingestion" / "src" / "layer1_ingestion")

# Register the canonical package path for import resolution
if (_repo_root / "services" / "layer1-ingestion" / "src" / "layer1_ingestion").exists():
    if _canonical_pkg not in __path__:
        __path__.append(_canonical_pkg)
else:
    raise FileNotFoundError(
        f"Canonical Layer 1 package not found at {_canonical_pkg}. "
        "Expected services/layer1-ingestion/src/layer1_ingestion/ to exist."
    )

# Emit deprecation warning on import
warnings.warn(
    "value_fabric.layer1 is deprecated. Use canonical imports: layer1_ingestion.*",
    DeprecationWarning,
    stacklevel=2,
)
