"""
Eval tests for the evaluate_formula skill.

These tests validate fixture correctness and scenario ordering invariants
without requiring a real database or formula engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_traces() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "evaluate_formula_traces.json"
    with open(path) as f:
        data = json.load(f)
    return data["traces"]


@pytest.fixture(scope="module")
def traces() -> list[dict[str, Any]]:
    """Load fixture traces once per module for faster, deterministic checks."""
    return load_traces()


class TestEvaluateFormulaContract:
    """Validate evaluate_formula fixture structure and scenario semantics."""

    def test_fixture_has_required_fields(self, traces: list[dict[str, Any]]) -> None:
        assert traces, "Fixture must have at least one trace"
        for trace in traces:
            assert "id" in trace
            assert "input" in trace
            assert "formula_id" in trace["input"], (
                f"Trace {trace['id']} missing 'formula_id'"
            )
            assert "variables" in trace["input"], (
                f"Trace {trace['id']} missing 'variables'"
            )

    def test_scenario_values_are_valid(self, traces: list[dict[str, Any]]) -> None:
        """scenario must be BASE, BEST, or WORST."""
        valid = {"BASE", "BEST", "WORST"}
        for trace in traces:
            scenario = trace["input"].get("scenario", "BASE")
            assert scenario in valid, (
                f"Trace {trace['id']}: invalid scenario '{scenario}'"
            )

    def test_variables_are_numeric(self, traces: list[dict[str, Any]]) -> None:
        """All variable values must be numeric."""
        for trace in traces:
            for var_name, var_value in trace["input"]["variables"].items():
                assert isinstance(var_value, (int, float)), (
                    f"Trace {trace['id']}: variable '{var_name}' must be numeric, got {type(var_value)}"
                )

    def test_base_scenario_assertion_is_exact(self, traces: list[dict[str, Any]]) -> None:
        """BASE scenario fixtures with exact 'value' assertion must be consistent."""
        base_traces = [t for t in traces if t["input"].get("scenario", "BASE") == "BASE"]
        assert base_traces, "At least one BASE scenario trace is required"
        for trace in base_traces:
            if "value" in trace["assertions"]:
                assert isinstance(trace["assertions"]["value"], (int, float)), (
                    f"Trace {trace['id']}: assertion 'value' must be numeric"
                )

    def test_scenario_ordering_invariants(self, traces: list[dict[str, Any]]) -> None:
        """
        For the same formula and variables, BEST > BASE (value_gt) and WORST < BASE (value_lt).
        This validates the invariant in the fixture definitions.
        """
        # Find BASE trace for each formula_id
        base_by_formula: dict[str, dict[str, Any]] = {}
        for t in traces:
            if t["input"].get("scenario", "BASE") == "BASE" and "value" in t["assertions"]:
                base_by_formula[t["input"]["formula_id"]] = t

        for trace in traces:
            fid = trace["input"]["formula_id"]
            scenario = trace["input"].get("scenario", "BASE")
            if fid not in base_by_formula:
                continue
            base_value = base_by_formula[fid]["assertions"]["value"]

            if scenario == "BEST" and "value_gt" in trace["assertions"]:
                assert trace["assertions"]["value_gt"] >= base_value, (
                    f"Trace {trace['id']}: BEST value_gt {trace['assertions']['value_gt']} "
                    f"should be >= BASE {base_value}"
                )
            if scenario == "WORST" and "value_lt" in trace["assertions"]:
                assert trace["assertions"]["value_lt"] <= base_value, (
                    f"Trace {trace['id']}: WORST value_lt {trace['assertions']['value_lt']} "
                    f"should be <= BASE {base_value}"
                )
