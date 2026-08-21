from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

from scripts.ci import structural_fitness_ratchet as ratchet

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_function_complexity_counts_branches() -> None:
    source = "\n".join(
        [
            "def hot(value):",
            "    if value > 0:",
            "        return 1",
            "    if value < 0:",
            "        return -1",
            "    return 0",
        ]
    )
    tree = ast.parse(source)
    fn = tree.body[0]
    assert ratchet.function_complexity(fn) == 3


def test_collect_complexities_includes_methods() -> None:
    source = "\n".join(
        [
            "class Service:",
            "    def run(self, flag):",
            "        if flag:",
            "            return True",
            "        return False",
        ]
    )
    result = dict(ratchet.collect_complexities(source))
    assert "Service.run" in result
    assert result["Service.run"] == 2


def test_collect_complexities_ignores_toplevel_executable_lines() -> None:
    # Top-level statements (calls, assignments) must not be treated as functions.
    source = "\n".join(
        [
            "s = setup()",
            "start(s)",
        ]
    )
    assert ratchet.collect_complexities(source) == []


def test_significant_line_count_ignores_blank_and_comment_lines(tmp_path: Path) -> None:
    f = tmp_path / "sample.py"
    f.write_text("# comment\n\ncode = 1\n# another\ncode2 = 2\n", encoding="utf-8")
    assert ratchet.significant_line_count(f) == 2


def test_excluded_patterns_filter_test_and_generated_files() -> None:
    assert ratchet.is_excluded("services/layer1/src/tests/test_x.py")
    assert ratchet.is_excluded("services/layer1/src/thing/test_thing.py")
    assert ratchet.is_excluded("services/layer4/harness/tests/test_harness.py")
    assert not ratchet.is_excluded("services/layer1/src/layer1/shared/tasks.py")


def test_module_key_resolves_src_python_module() -> None:
    assert (
        ratchet.module_key("services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py")
        == "layer1_ingestion.shared.tasks"
    )
    assert ratchet.module_key("scripts/ci/structure.py") is None


def test_compare_reports_new_oversized_module_and_hot_function() -> None:
    baseline = {
        "oversized_modules": [],
        "high_complexity_functions": [],
        "dependency_cycles": [],
    }
    oversized = [ratchet.ModuleFinding("layer1_ingestion.shared.tasks", 1200, 1000)]
    functions = [ratchet.FunctionFinding("layer4.service", "run", 30, 25)]

    violations = ratchet.compare(oversized, functions, [], baseline)
    assert len(violations) == 2
    assert any("oversized module" in v for v in violations)
    assert any("high-complexity function" in v for v in violations)


def test_structural_fitness_ratchet_has_public_local_entrypoints() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert "check-structural-fitness-ratchet:" in makefile
    assert (
        package_json["scripts"]["check:structural-fitness"]
        == "make check-structural-fitness-ratchet"
    )


def test_structural_preflight_runs_structural_fitness_ratchet() -> None:
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    )

    commands = [
        step.get("run", "") for step in workflow["jobs"]["structural-preflight"]["steps"]
    ]
    assert "make check-structural-fitness-ratchet" in commands