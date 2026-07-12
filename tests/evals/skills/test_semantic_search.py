"""
Eval tests for the semantic_search skill.

These tests validate that the skill contract is honoured.
In CI they run against mock implementations.
Mark with @pytest.mark.slow for tests that need a real knowledge graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_traces() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "semantic_search_traces.json"
    with open(path) as f:
        data = json.load(f)
    return data["traces"]


@pytest.fixture(scope="module")
def traces() -> list[dict[str, Any]]:
    """Load fixture traces once for all semantic-search contract checks."""
    return load_traces()


class TestSemanticSearchContract:
    """Validate that semantic_search output conforms to its tool manifest."""

    def test_fixture_has_required_fields(self, traces: list[dict[str, Any]]) -> None:
        """All fixture traces have required input fields."""
        assert traces, "Fixture must have at least one trace"
        for trace in traces:
            assert "id" in trace
            assert "input" in trace
            assert "query" in trace["input"], f"Trace {trace['id']} missing 'query' in input"

    def test_similarity_threshold_constraint(self, traces: list[dict[str, Any]]) -> None:
        """similarity_threshold must be between 0.0 and 1.0 in all fixtures."""
        for trace in traces:
            threshold = trace["input"].get("similarity_threshold")
            if threshold is not None:
                assert 0.0 <= threshold <= 1.0, (
                    f"Trace {trace['id']}: similarity_threshold {threshold} out of range"
                )

    def test_top_k_constraint(self, traces: list[dict[str, Any]]) -> None:
        """top_k must be between 1 and 50 in all fixtures."""
        for trace in traces:
            top_k = trace["input"].get("top_k")
            if top_k is not None:
                assert 1 <= top_k <= 50, (
                    f"Trace {trace['id']}: top_k {top_k} out of range"
                )

    def test_entity_types_are_valid(self, traces: list[dict[str, Any]]) -> None:
        """entity_types must only contain valid ontology types."""
        valid_types = {"Capability", "UseCase", "Persona", "ValueDriver"}
        for trace in traces:
            types = trace["input"].get("entity_types", [])
            invalid = set(types) - valid_types
            assert not invalid, (
                f"Trace {trace['id']}: invalid entity_types {invalid}"
            )
