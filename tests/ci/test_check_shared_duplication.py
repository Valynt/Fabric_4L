from __future__ import annotations

import ast

from scripts.ci import check_shared_duplication as dup


def _defs(source: str) -> list[tuple[str, ast.AST]]:
    return dup.collect_defs(source)


def test_collect_defs_extracts_methods_but_not_class_bodies() -> None:
    source = "\n".join(
        [
            "def top():",
            "    return 1",
            "",
            "class Service:",
            "    def run(self):",
            "        return 2",
        ]
    )
    names = [name for name, _ in _defs(source)]
    assert names == ["top", "Service.run"]


def test_fingerprint_ignores_function_name_and_signature() -> None:
    # Same body, different name and different (unused) signature parameters.
    src_a = "\n".join(["def alpha():", "    return 42"])
    src_b = "\n".join(["def beta(unused, flag=True):", "    return 42"])
    node_a = _defs(src_a)[0][1]
    node_b = _defs(src_b)[0][1]
    assert dup.fingerprint(node_a, normalize=False) == dup.fingerprint(node_b, normalize=False)


def test_cluster_detects_planted_exact_duplicate() -> None:
    # The exact tier catches verbatim copy-paste (identical bodies, including
    # identifier names); only the enclosing function name differs.
    source = "\n".join(
        [
            "def alpha(x):",
            "    a = x * 2",
            "    b = a + 1",
            "    c = b - 3",
            "    return c",
            "",
            "def beta(x):",
            "    a = x * 2",
            "    b = a + 1",
            "    c = b - 3",
            "    return c",
        ]
    )
    clusters = dup._cluster(_defs(source), normalize=False, min_statements=4)
    assert len(clusters) == 1
    _, members = clusters[0]
    assert set(members) == {"alpha", "beta"}


def test_cluster_ignores_bodies_below_min_statement_threshold() -> None:
    source = "\n".join(
        [
            "def alpha(x):",
            "    return x",
            "",
            "def beta(y):",
            "    return y",
        ]
    )
    clusters = dup._cluster(_defs(source), normalize=False, min_statements=4)
    assert clusters == []


def test_normalized_tier_catches_renamed_logic() -> None:
    source = "\n".join(
        [
            "def compute_total(items):",
            "    total = 0",
            "    for item in items:",
            "        total = total + item",
            "    if total > 100:",
            "        total = 100",
            "    total = total * 1.1",
            "    total = round(total, 2)",
            "    result = str(total)",
            "    prefix = 'sum'",
            "    suffix = 'units'",
            "    return prefix + result + suffix",
            "",
            "def compute_sum(values):",
            "    acc = 0",
            "    for v in values:",
            "        acc = acc + v",
            "    if acc > 100:",
            "        acc = 100",
            "    acc = acc * 1.1",
            "    acc = round(acc, 2)",
            "    out = str(acc)",
            "    pre = 'sum'",
            "    post = 'units'",
            "    return pre + out + post",
        ]
    )
    clusters = dup._cluster(_defs(source), normalize=True, min_statements=8)
    assert len(clusters) == 1
    _, members = clusters[0]
    assert set(members) == {"compute_total", "compute_sum"}


def test_compare_reports_new_cluster_and_stale_baseline_entry() -> None:
    baseline = {
        "exact_clusters": [{"members": ["m.old_a", "m.old_b"]}],
        "normalized_clusters": [],
    }
    exact = [("fp", ["m.new_a", "m.new_b"])]
    violations = dup.compare(exact, [], baseline)
    messages = [v["message"] for v in violations]
    assert any("new exact duplication" in m for m in messages)
    assert any("stale baseline entry" in m and "old_a" in m for m in messages)


def test_compare_is_clean_when_current_matches_baseline() -> None:
    baseline = {
        "exact_clusters": [{"members": ["m.a", "m.b"]}],
        "normalized_clusters": [],
    }
    exact = [("fp", ["m.a", "m.b"])]
    assert dup.compare(exact, [], baseline) == []


def test_module_key_resolves_shared_python_module() -> None:
    assert (
        dup.module_key("packages/shared/src/value_fabric/shared/tasks.py")
        == "value_fabric.shared.tasks"
    )
    assert dup.module_key("services/layer1-ingestion/src/x/y.py") is None


def test_is_excluded_filters_test_and_cache_files() -> None:
    assert dup.is_excluded("packages/shared/src/value_fabric/shared/tests/test_x.py")
    assert dup.is_excluded("packages/shared/src/value_fabric/shared/test_x.py")
    assert dup.is_excluded("packages/shared/src/value_fabric/shared/__pycache__/x.py")
    assert not dup.is_excluded("packages/shared/src/value_fabric/shared/tasks.py")
