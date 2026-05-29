"""Redirect shim: value_fabric.layer4.* -> services/layer4-agents/src/layer4_agents/*.

Canonical Layer 4 code lives in ``services/layer4-agents/src/layer4_agents/``.
This shim appends the canonical package path to ``__path__`` so that
``import value_fabric.layer4.engine`` resolves to the canonical tree.

**DEPRECATED:** Use canonical imports ``layer4_agents.*`` instead.
This facade will be removed in a future release.
"""

from __future__ import annotations

import warnings
from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_canonical_pkg: str = str(_repo_root / "services" / "layer4-agents" / "src" / "layer4_agents")

# Register the canonical package path for import resolution
if (_repo_root / "services" / "layer4-agents" / "src" / "layer4_agents").exists():
    if _canonical_pkg not in __path__:
        __path__.append(_canonical_pkg)
else:
    raise FileNotFoundError(
        f"Canonical Layer 4 package not found at {_canonical_pkg}. "
        "Expected services/layer4-agents/src/layer4_agents/ to exist."
    )

# Emit deprecation warning on import
warnings.warn(
    "value_fabric.layer4 is deprecated. Use canonical imports: layer4_agents.*",
    DeprecationWarning,
    stacklevel=2,
)
