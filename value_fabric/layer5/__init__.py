# mypy: ignore-missing-imports, disable-error-code="import-not-found"
# value_fabric.layer5 — Thin shim re-exporting canonical layer5_ground_truth.
# Canonical source lives in services/layer5-ground-truth/src/layer5_ground_truth/
# Do not add implementation here; modify the canonical source only.

from layer5_ground_truth.services.truth_service import TruthService
from layer5_ground_truth.services.truth_service import get_truth_service

__all__ = ["TruthService", "get_truth_service"]
