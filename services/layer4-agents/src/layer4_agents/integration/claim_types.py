"""Canonical claim-type taxonomy for the L4 -> L5 Ground Truth boundary.

Layer 5 (Ground Truth) owns the claim taxonomy. This module is Layer 4's
single source for that taxonomy and for mapping Layer 4's internal claim
vocabulary onto it. It must stay in lockstep with:

- ``services/layer5-ground-truth/src/layer5_ground_truth/models/truth_object.py``
  (``ClaimType`` enum — the runtime authority), and
- ``contracts/jsonschema/claim-types.v1.json`` (the published contract).

Guard: ``tests/contract/test_claim_type_taxonomy.py`` fails when either side
drifts.
"""

from __future__ import annotations

from typing import Any

# Canonical Layer 5 claim taxonomy (v1). Mirrors layer5_ground_truth ClaimType.
CANONICAL_CLAIM_TYPES: frozenset[str] = frozenset(
    {
        "cost_savings_baseline",
        "revenue_impact",
        "efficiency_gain",
        "risk_reduction",
        "compliance_requirement",
        "customer_outcome",
        "technical_capability",
        "market_benchmark",
        "persona_pain_point",
        "value_driver_metric",
        "other",
    }
)

# Layer 4 internal vocabulary -> canonical Layer 5 taxonomy.
LAYER4_TO_LAYER5_CLAIM_TYPE: dict[str, str] = {
    "metric": "value_driver_metric",
    "roi_assumption": "cost_savings_baseline",
    "outcome": "customer_outcome",
    "benchmark": "market_benchmark",
    "risk": "risk_reduction",
}


def to_layer5_claim_type(claim_type: Any) -> str:
    """Map a Layer 4 claim type onto the canonical Layer 5 taxonomy."""
    if not claim_type:
        raise ValueError(
            "claim_type is required; falsy values are not silently defaulted"
        )
    normalized = str(claim_type).strip().lower()
    try:
        return LAYER4_TO_LAYER5_CLAIM_TYPE[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unmapped Layer 4 claim_type for Layer 5 promotion: {claim_type!r}"
        ) from exc


def require_canonical_claim_type(claim_type: str) -> str:
    """Fail fast when a value is not in the canonical Layer 5 taxonomy.

    Called at the L4 -> L5 client boundary so taxonomy drift surfaces as a
    local error instead of a remote 422 with lost lineage. Accepts both
    canonical Layer 5 types and Layer 4 internal vocabulary (mapped via
    ``to_layer5_claim_type``).
    """
    normalized = str(claim_type or "").strip().lower()
    if normalized in CANONICAL_CLAIM_TYPES:
        return normalized
    try:
        return to_layer5_claim_type(normalized)
    except ValueError:
        raise ValueError(
            f"claim_type {claim_type!r} is not in the canonical Layer 5 "
            f"taxonomy (contracts/jsonschema/claim-types.v1.json)"
        )
