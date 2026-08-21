"""Behavior-first tests for HybridSearch._merge_results normalization and determinism.

Covers:
- Negative raw scores do not flip the sign of normalized/combined scores.
- Empty signal yields 0 contribution (no division-by-zero, no NaN).
- Tied combined scores resolve deterministically by entity_id (stable order).
- graph rows keyed by entity_id-only are merged (id/entity_id unification).
"""

from __future__ import annotations

import pytest

from src.retrieval.hybrid_search import HybridSearch


def _engine() -> HybridSearch:
    # Constructor only needs settings; _merge_results is pure over its args.
    from src.config import get_settings

    return HybridSearch(settings=get_settings())


def _weights() -> dict[str, float]:
    return {"bm25": 0.4, "vector": 0.3, "graph": 0.3}


def test_negative_raw_score_does_not_invert_combined():
    """A negative graph score must not drag the combined score below zero."""
    engine = _engine()
    bm25 = [{"id": "a", "score": 2.0, "entity_type": "Capability", "name": "A"}]
    vector = [{"id": "a", "score": 0.8, "entity_type": "Capability", "name": "A"}]
    graph = [{"id": "a", "score": -1.0, "entity_type": "Capability", "name": "A"}]

    results = engine._merge_results(bm25, vector, graph, _weights())
    assert len(results) == 1
    r = results[0]
    # Clamped to [0, 1]: negative raw graph score -> 0.0 normalized.
    assert r.graph_score == 0.0
    assert r.bm25_score == pytest.approx(1.0)
    assert r.vector_score == pytest.approx(1.0)
    assert r.combined_score >= 0.0


def test_empty_signal_does_not_divide_by_zero():
    """Empty graph results must not produce NaN/inf; contribution is 0."""
    engine = _engine()
    bm25 = [{"id": "a", "score": 1.0, "entity_type": "Capability", "name": "A"}]
    vector = [{"id": "a", "score": 1.0, "entity_type": "Capability", "name": "A"}]
    graph: list[dict] = []

    results = engine._merge_results(bm25, vector, graph, _weights())
    assert len(results) == 1
    r = results[0]
    assert r.graph_score == 0.0
    # No NaN/inf
    assert r.combined_score == r.combined_score  # NaN check
    assert abs(r.combined_score) != float("inf")


def test_ties_resolve_deterministically_by_entity_id():
    """Tied combined scores must order by entity_id ascending (stable)."""
    engine = _engine()
    # Two entities, identical scores -> identical combined score.
    bm25 = [
        {"id": "z-entity", "score": 1.0, "entity_type": "Capability", "name": "Z"},
        {"id": "a-entity", "score": 1.0, "entity_type": "Capability", "name": "A"},
    ]
    vector: list[dict] = []
    graph: list[dict] = []

    results = engine._merge_results(bm25, vector, graph, _weights())
    assert [r.entity_id for r in results] == ["a-entity", "z-entity"]

    # Re-running must produce the same order (deterministic).
    results2 = engine._merge_results(bm25, vector, graph, _weights())
    assert [r.entity_id for r in results2] == ["a-entity", "z-entity"]


def test_graph_row_keyed_by_entity_id_is_merged():
    """graph rows returning entity_id (not id) must still merge with bm25/vector."""
    engine = _engine()
    bm25 = [
        {"entity_id": "shared", "score": 1.0, "entity_type": "Capability", "name": "S"}
    ]
    vector: list[dict] = []
    graph = [
        {"entity_id": "shared", "score": 0.5, "entity_type": "Capability", "name": "S"}
    ]

    results = engine._merge_results(bm25, vector, graph, _weights())
    assert len(results) == 1
    assert results[0].entity_id == "shared"
    assert results[0].graph_score == pytest.approx(1.0)
