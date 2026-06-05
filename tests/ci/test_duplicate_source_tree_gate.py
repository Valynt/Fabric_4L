from __future__ import annotations

from scripts.ci.check_duplicate_source_trees import find_violations, main


def test_layer4_duplicate_source_tree_gate_is_clean() -> None:
    assert find_violations({"layer4"}) == []


def test_duplicate_source_tree_gate_accepts_documented_strict_flag() -> None:
    assert main(["--strict", "--json", "--layers", "layer4"]) == 0
