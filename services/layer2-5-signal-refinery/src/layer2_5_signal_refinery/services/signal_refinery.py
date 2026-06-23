from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

"""Signal Refinery — core scoring, classification, and trust computation.

Responsibilities:
- Compute trust_score from evidence quality, provenance type, and confidence
- Classify raw L2 extraction output into ValueSignalType
- Advance lifecycle state from draft → extracted after refinement
- Emit refined signals to L3 graph (best-effort, non-blocking)

Trust score formula:
  trust_score = (
      0.40 * confidence
    + 0.30 * evidence_quality_score
    + 0.20 * provenance_weight
    + 0.10 * lifecycle_bonus
  )

Where:
  evidence_quality_score = mean(evidence[i].confidence * evidence[i].relevance_score)
  provenance_weight: human=1.0, ai=0.7, system=0.5
  lifecycle_bonus: validated=1.0, extracted=0.5, draft=0.0
"""

logger = logging.getLogger(__name__)

# Provenance extractor weights
_PROVENANCE_WEIGHTS: dict[str, float] = {
    "human": 1.0,
    "ai": 0.7,
    "system": 0.5,
}

# Lifecycle bonus
_LIFECYCLE_BONUS: dict[str, float] = {
    "validated": 1.0,
    "promoted": 1.0,
    "extracted": 0.5,
    "draft": 0.0,
    "rejected": 0.0,
    "expired": 0.0,
    "superseded": 0.0,
}

# L2 signal_type → ValueSignalType mapping
_L2_TYPE_MAP: dict[str, str] = {
    "pain_point": "pain",
    "pain": "pain",
    "opportunity": "opportunity",
    "risk": "risk",
    "churn_risk": "renewal",
    "renewal_risk": "renewal",
    "expansion": "expansion",
    "upsell": "expansion",
    "cost_reduction": "cost_saving",
    "cost_saving": "cost_saving",
    "revenue": "revenue_uplift",
    "revenue_uplift": "revenue_uplift",
    "efficiency": "efficiency",
    "compliance": "compliance",
    "strategic": "strategic_priority",
    "strategic_priority": "strategic_priority",
}


def compute_evidence_quality(evidence: list[dict[str, Any]]) -> float:
    """Mean of (confidence * relevance_score) across evidence items.

    Falls back to mean confidence when relevance_score is absent.
    Returns 0.0 for empty evidence.
    """
    if not evidence:
        return 0.0
    scores = []
    for item in evidence:
        conf = float(item.get("confidence", 0.0))
        rel = item.get("relevance_score")
        score = conf * float(rel) if rel is not None else conf
        scores.append(score)
    return sum(scores) / len(scores)


def compute_trust_score(
    confidence: float,
    evidence: list[dict[str, Any]],
    provenance: dict[str, Any],
    lifecycle_state: str,
) -> float:
    """Compute composite trust score (0–1)."""
    evidence_quality = compute_evidence_quality(evidence)
    provenance_weight = _PROVENANCE_WEIGHTS.get(
        provenance.get("extractor", "system"), 0.5
    )
    lifecycle_bonus = _LIFECYCLE_BONUS.get(lifecycle_state, 0.0)

    raw = (
        0.40 * confidence
        + 0.30 * evidence_quality
        + 0.20 * provenance_weight
        + 0.10 * lifecycle_bonus
    )
    return round(min(max(raw, 0.0), 1.0), 4)


def classify_signal_type(raw_type: str) -> str:
    """Map a raw L2 signal_type string to a canonical ValueSignalType value."""
    normalized = raw_type.lower().strip().replace(" ", "_").replace("-", "_")
    return _L2_TYPE_MAP.get(normalized, "pain")


def refine_signal(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply refinement to a raw signal dict.

    - Normalizes type via classify_signal_type
    - Computes trust_score
    - Advances lifecycle_state to 'extracted'
    - Ensures id, created_at, updated_at are set
    - Ensures evidence items have UUIDs
    """
    now = datetime.now(UTC).isoformat()

    # Normalize type
    raw_type = raw.get("type", "pain")
    refined_type = classify_signal_type(raw_type)

    # Ensure evidence items have IDs
    evidence = raw.get("evidence", [])
    for item in evidence:
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())

    # Compute trust score
    provenance = raw.get("provenance", {"extractor": "system", "method": "unknown", "extracted_at": now})
    confidence = float(raw.get("confidence", 0.0))
    lifecycle_state = "extracted"

    trust_score = compute_trust_score(confidence, evidence, provenance, lifecycle_state)

    return {
        **raw,
        "id": raw.get("id") or str(uuid.uuid4()),
        "type": refined_type,
        "confidence": confidence,
        "trust_score": trust_score,
        "lifecycle_state": lifecycle_state,
        "evidence": evidence,
        "provenance": provenance,
        "source_refs": raw.get("source_refs", []),
        "created_at": raw.get("created_at") or now,
        "updated_at": now,
    }


def refine_batch(raws: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Refine a batch of raw signal dicts."""
    refined = []
    for raw in raws:
        try:
            refined.append(refine_signal(raw))
        except Exception:
            logger.exception("Failed to refine signal: %s", raw.get("id", "<unknown>"))
    return refined
