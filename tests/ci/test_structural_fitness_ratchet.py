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


def test_function_complexity_excludes_nested_function_branches() -> None:
    # The outer function's complexity must not count branches owned by a
    # nested function; the nested function is measured separately.
    source = "\n".join(
        [
            "def outer(value):",
            "    if value < 0:",
            "        return -1",
            "    def inner(flag):",
            "        if flag:",
            "            return 1",
            "        return 0",
            "    return inner(value)",
        ]
    )
    tree = ast.parse(source)
    fn = tree.body[0]
    assert ratchet.function_complexity(fn) == 2  # outer if only


def test_collect_complexities_reports_nested_function_separately() -> None:
    # Nested handlers inside a router factory are emitted under a dotted
    # qualified name so they cannot escape the ratchet inside the outer count.
    source = "\n".join(
        [
            "def build_router():",
            "    async def get_item(item_id: int):",
            "        if item_id > 0:",
            "            return item_id",
            "        return None",
            "    return get_item",
        ]
    )
    result = dict(ratchet.collect_complexities(source))
    assert "build_router" in result
    assert result["build_router"] == 1  # nested if not counted on the outer
    assert "build_router.get_item" in result
    assert result["build_router.get_item"] == 2


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


def test_compare_reports_stale_baseline_entries() -> None:
    # A baseline is an allowlist; once a grandfathered hotspot is cleaned up
    # the entry must not silently linger, otherwise a later PR could re-introduce
    # the same hotspot while the stale baseline still covers it.
    baseline = {
        "oversized_modules": [{"module": "layer1_ingestion.old_big", "size": 1100}],
        "high_complexity_functions": [
            {"module": "layer4.service", "function": "legacy_hot", "complexity": 30}
        ],
        "dependency_cycles": [["a.b", "a.c"]],
    }
    violations = ratchet.compare([], [], [], baseline)
    assert any("oversized module" in v and "stale" in v for v in violations)
    assert any(
        "high-complexity function" in v and "stale" in v for v in violations
    )
    assert any("import cycle" in v and "stale" in v for v in violations)


def test_build_import_graph_resolves_pure_relative_import(
    tmp_path: Path, monkeypatch
) -> None:
    # `from .. import main as handlers` (node.module is None) must create the
    # layer6_benchmarks.api.routes.system -> layer6_benchmarks.api.main edge,
    # which closes the real layer6 cycle.
    src = tmp_path / "services/layer6-benchmarks/src/layer6_benchmarks/api"
    (src / "routes").mkdir(parents=True)
    (src / "main.py").write_text(
        "from .routes import benchmarks, system\n", encoding="utf-8"
    )
    (src / "routes/__init__.py").write_text("", encoding="utf-8")
    (src / "routes/system.py").write_text(
        "from .. import main as handlers\nfrom .. import main\n", encoding="utf-8"
    )
    (src / "routes/benchmarks.py").write_text("", encoding="utf-8")
    files = [
        "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
        "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/__init__.py",
        "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/system.py",
        "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/benchmarks.py",
    ]
    monkeypatch.chdir(tmp_path)
    adj = ratchet.build_import_graph(files)
    assert (
        "layer6_benchmarks.api.main"
        in adj["layer6_benchmarks.api.routes.system"]
    )
    assert (
        "layer6_benchmarks.api.routes.system"
        in adj["layer6_benchmarks.api.main"]
    )


def test_structural_fitness_ratchet_has_public_local_entrypoints() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))

    assert "check-structural-fitness-ratchet:" in makefile
    assert (
        package_json["scripts"]["check:structural-fitness"]
        == "make check-structural-fitness-ratchet"
    )


def test_structural_preflight_runs_structural_fitness_via_health_aggregate() -> None:
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    )

    commands = [
        step.get("run", "") for step in workflow["jobs"]["structural-preflight"]["steps"]
    ]
    assert "make check-health-ratchets" in commands
    assert "make check-structural-fitness-ratchet" not in commands
