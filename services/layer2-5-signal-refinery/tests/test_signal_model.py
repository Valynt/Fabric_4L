"""Unit tests for the ValueSignal Pydantic model and refinery logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from layer2_5_signal_refinery.services.signal_refinery import (
    classify_signal_type,
    compute_evidence_quality,
    compute_trust_score,
    refine_signal,
    refine_batch,
)


# ---------------------------------------------------------------------------
# compute_evidence_quality
# ---------------------------------------------------------------------------


def test_evidence_quality_empty():
    assert compute_evidence_quality([]) == 0.0


def test_evidence_quality_single_with_relevance():
    evidence = [{"confidence": 0.8, "relevance_score": 0.9}]
    score = compute_evidence_quality(evidence)
    assert abs(score - 0.72) < 0.001


def test_evidence_quality_no_relevance_falls_back_to_confidence():
    evidence = [{"confidence": 0.6}]
    score = compute_evidence_quality(evidence)
    assert abs(score - 0.6) < 0.001


def test_evidence_quality_multiple_items():
    evidence = [
        {"confidence": 1.0, "relevance_score": 1.0},
        {"confidence": 0.0, "relevance_score": 0.0},
    ]
    score = compute_evidence_quality(evidence)
    assert abs(score - 0.5) < 0.001


# ---------------------------------------------------------------------------
# compute_trust_score
# ---------------------------------------------------------------------------


def test_trust_score_human_validated():
    score = compute_trust_score(
        confidence=1.0,
        evidence=[{"confidence": 1.0, "relevance_score": 1.0}],
        provenance={"extractor": "human"},
        lifecycle_state="validated",
    )
    assert score == 1.0


def test_trust_score_ai_extracted():
    score = compute_trust_score(
        confidence=0.8,
        evidence=[{"confidence": 0.8, "relevance_score": 0.8}],
        provenance={"extractor": "ai"},
        lifecycle_state="extracted",
    )
    # 0.40*0.8 + 0.30*0.64 + 0.20*0.7 + 0.10*0.5 = 0.32 + 0.192 + 0.14 + 0.05 = 0.702
    assert 0.69 < score < 0.72


def test_trust_score_system_draft():
    score = compute_trust_score(
        confidence=0.5,
        evidence=[],
        provenance={"extractor": "system"},
        lifecycle_state="draft",
    )
    # 0.40*0.5 + 0.30*0.0 + 0.20*0.5 + 0.10*0.0 = 0.20 + 0 + 0.10 + 0 = 0.30
    assert abs(score - 0.30) < 0.01


def test_trust_score_clamped_to_one():
    score = compute_trust_score(
        confidence=1.0,
        evidence=[{"confidence": 1.0, "relevance_score": 1.0}],
        provenance={"extractor": "human"},
        lifecycle_state="validated",
    )
    assert score <= 1.0


def test_trust_score_clamped_to_zero():
    score = compute_trust_score(
        confidence=0.0,
        evidence=[],
        provenance={"extractor": "system"},
        lifecycle_state="rejected",
    )
    assert score >= 0.0


# ---------------------------------------------------------------------------
# classify_signal_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("pain_point", "pain"),
    ("pain", "pain"),
    ("opportunity", "opportunity"),
    ("risk", "risk"),
    ("churn_risk", "renewal"),
    ("renewal_risk", "renewal"),
    ("expansion", "expansion"),
    ("upsell", "expansion"),
    ("cost_reduction", "cost_saving"),
    ("revenue_uplift", "revenue_uplift"),
    ("efficiency", "efficiency"),
    ("compliance", "compliance"),
    ("strategic_priority", "strategic_priority"),
    ("unknown_type", "pain"),  # fallback
    ("PAIN", "pain"),          # case-insensitive
    ("Pain Point", "pain"),    # spaces normalized
])
def test_classify_signal_type(raw, expected):
    assert classify_signal_type(raw) == expected


# ---------------------------------------------------------------------------
# refine_signal
# ---------------------------------------------------------------------------


def test_refine_signal_sets_extracted_state():
    raw = {
        "account_id": str(uuid.uuid4()),
        "type": "pain_point",
        "content": "Customer is struggling with manual processes.",
        "confidence": 0.75,
        "provenance": {
            "extractor": "ai",
            "method": "llm_extraction",
            "extracted_at": "2026-05-14T10:00:00Z",
        },
        "evidence": [],
        "source_refs": [],
    }
    refined = refine_signal(raw)
    assert refined["lifecycle_state"] == "extracted"
    assert refined["type"] == "pain"
    assert refined["trust_score"] > 0.0
    assert refined["id"] is not None


def test_refine_signal_assigns_evidence_ids():
    raw = {
        "account_id": str(uuid.uuid4()),
        "type": "opportunity",
        "content": "Expansion opportunity in EMEA.",
        "confidence": 0.9,
        "provenance": {"extractor": "ai", "method": "llm_extraction", "extracted_at": "2026-05-14T10:00:00Z"},
        "evidence": [{"source_ref": "doc://test", "confidence": 0.9}],
        "source_refs": [],
    }
    refined = refine_signal(raw)
    for item in refined["evidence"]:
        assert item.get("id") is not None


def test_refine_signal_preserves_existing_id():
    existing_id = str(uuid.uuid4())
    raw = {
        "id": existing_id,
        "account_id": str(uuid.uuid4()),
        "type": "risk",
        "content": "Regulatory risk identified.",
        "confidence": 0.6,
        "provenance": {"extractor": "system", "method": "rule_based", "extracted_at": "2026-05-14T10:00:00Z"},
        "evidence": [],
        "source_refs": [],
    }
    refined = refine_signal(raw)
    assert refined["id"] == existing_id


def test_refine_batch_skips_bad_items():
    raws = [
        {
            "account_id": str(uuid.uuid4()),
            "type": "pain",
            "content": "Valid signal.",
            "confidence": 0.7,
            "provenance": {"extractor": "ai", "method": "llm_extraction", "extracted_at": "2026-05-14T10:00:00Z"},
            "evidence": [],
            "source_refs": [],
        },
        None,  # bad item — should be skipped
    ]
    # refine_batch should not raise; bad items are logged and skipped
    results = refine_batch([r for r in raws if r is not None])
    assert len(results) == 1
    assert results[0]["lifecycle_state"] == "extracted"
