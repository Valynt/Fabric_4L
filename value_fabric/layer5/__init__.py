"""Compatibility shim for Layer 5 imports.

This package is a backward-compatibility facade per ADR-027.
The canonical implementation lives in ``services/layer5-ground-truth/src/layer5_ground_truth/``.

This shim appends the service source tree to ``__path__`` so legacy
``value_fabric.layer5.*`` imports continue to resolve during migration.

New code should import directly from ``services/layer5-ground-truth/src/`` or
use the service package names. Do not add new implementation logic here.

**DEPRECATED:** Use canonical imports ``layer5_ground_truth.*`` instead.
This facade will be removed after 2026-09-30 per ADR-027.
"""

from __future__ import annotations

import warnings
from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_service_src: str = str(_repo_root / "services" / "layer5-ground-truth" / "src" / "layer5_ground_truth")

# Only register the service source path if it exists; fail fast otherwise.
if (_repo_root / "services" / "layer5-ground-truth" / "src" / "layer5_ground_truth").exists():
    if _service_src not in __path__:
        __path__.append(_service_src)
else:
    raise FileNotFoundError(
        f"Layer 5 service source tree not found at {_service_src}. "
        "Expected services/layer5-ground-truth/src/layer5_ground_truth/ to exist."
    )

# Emit deprecation warning on import
warnings.warn(
    "value_fabric.layer5 is deprecated. Use canonical imports: layer5_ground_truth.*. "
    "This facade will be removed after 2026-09-30 per ADR-027",
    DeprecationWarning,
    stacklevel=2,
)
