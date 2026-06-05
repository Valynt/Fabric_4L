"""Compatibility namespace for canonical Layer 5 modules.

Canonical source lives under
``services/layer5-ground-truth/src/layer5_ground_truth``. Keep this package as
a shim; do not add Layer 5 implementation here.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_PACKAGE = (
    _REPO_ROOT
    / "services"
    / "layer5-ground-truth"
    / "src"
    / "layer5_ground_truth"
)
__path__.append(str(_CANONICAL_PACKAGE))

from .services.truth_service import TruthService, get_truth_service

__all__ = ["TruthService", "get_truth_service"]
