"""Compatibility shim for Layer 2 imports.

This package is a backward-compatibility facade per ADR-027.
The canonical implementation lives in ``services/layer2-extraction/src/``.

This shim appends the service source tree to ``__path__`` so legacy
``value_fabric.layer2.*`` imports continue to resolve during migration.

New code should import directly from ``services/layer2-extraction/src/`` or
use the service package names. Do not add new implementation logic here.
"""

from __future__ import annotations

from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_service_src: str = str(_repo_root / "services" / "layer2-extraction" / "src")

# Only register the service source path if it exists; fail fast otherwise.
if (_repo_root / "services" / "layer2-extraction" / "src").exists():
    if _service_src not in __path__:
        __path__.append(_service_src)
else:
    raise FileNotFoundError(
        f"Layer 2 service source tree not found at {_service_src}. "
        "Expected services/layer2-extraction/src/ to exist."
    )
