"""CI guardrail for tenant isolation in Layer 6 benchmark dataset queries."""

import ast
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest
from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER6_REPOSITORY_PATHS = [
    REPO_ROOT / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks" / "repositories",
]
BENCHMARK_DATASET_CYPHER = re.compile(
    r"\b(?:MATCH|OPTIONAL\s+MATCH|MERGE|CREATE)\b[\s\S]*BenchmarkDataset",
    re.IGNORECASE,
)
BOUND_CYPHER_TENANT_PREDICATE = re.compile(
    r"(?:\b\w+\.)?tenant_id\s*(?:=|:)\s*\$tenant_id\b",
    re.IGNORECASE,
)
QUERY_SOURCE_MARKERS = (
    ".query(",
    "select(",
    ".join(",
    "joinedload(",
    "contains_eager(",
    "relationship(",
)


@dataclass(frozen=True)
class TenantPredicateViolation:
    path: Path
    line: int
    reason: str

    def format(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}:{self.line} {self.reason}"


def test_layer6_repository_paths_use_canonical_service_namespace() -> None:
    expected = (
        REPO_ROOT
        / "services"
        / "layer6-benchmarks"
        / "src"
        / "layer6_benchmarks"
        / "repositories"
    )
    assert [expected] == LAYER6_REPOSITORY_PATHS
    assert expected.is_dir()
    assert (expected / "benchmark_repository.py").is_file()


def _benchmark_dataset_aliases(tree: ast.AST) -> set[str]:
    aliases = {"BenchmarkDataset"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in aliases:
            aliases.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
    return aliases


def _first_benchmark_dataset_line(node: ast.AST, text: str) -> int:
    index = text.find("BenchmarkDataset")
    if index == -1:
        return getattr(node, "lineno", 1)
    return getattr(node, "lineno", 1) + text[:index].count("\n")


def _is_benchmark_dataset_cypher(text: str) -> bool:
    return "BenchmarkDataset" in text and bool(BENCHMARK_DATASET_CYPHER.search(text))


def _has_bound_cypher_tenant_predicate(text: str) -> bool:
    return bool(BOUND_CYPHER_TENANT_PREDICATE.search(text))


def _source_references_benchmark_dataset(source: str, aliases: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(alias)}\b", source) for alias in aliases)


def _is_benchmark_dataset_query_source(source: str, aliases: set[str]) -> bool:
    return _source_references_benchmark_dataset(source, aliases) and any(
        marker in source for marker in QUERY_SOURCE_MARKERS
    )


def _is_tenant_attr(node: ast.AST, aliases: set[str]) -> bool:
    if not isinstance(node, ast.Attribute) or node.attr != "tenant_id":
        return False
    return isinstance(node.value, ast.Name) and node.value.id in aliases


def _is_real_tenant_operand(node: ast.AST, aliases: set[str]) -> bool:
    if _is_tenant_attr(node, aliases):
        return False
    if isinstance(node, ast.Name):
        return node.id != "BenchmarkDataset"
    if isinstance(node, ast.Attribute):
        return not _is_tenant_attr(node, aliases)
    if isinstance(node, ast.Call):
        return False
    return False


def _has_ast_tenant_predicate(node: ast.AST, aliases: set[str]) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Compare) or not any(
            isinstance(op, ast.Eq) for op in child.ops
        ):
            continue
        operands = [child.left, *child.comparators]
        for left, right in zip(operands, operands[1:]):
            if _is_tenant_attr(left, aliases) and _is_real_tenant_operand(right, aliases):
                return True
            if _is_tenant_attr(right, aliases) and _is_real_tenant_operand(left, aliases):
                return True
    return False


def _has_local_tenant_constraint(node: ast.AST, source: str, aliases: set[str]) -> bool:
    return _has_ast_tenant_predicate(node, aliases) or bool(
        re.search(r"\.filter_by\s*\([^)]*\btenant_id\s*=(?!=)", source)
    )


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _has_benchmark_query_call_ancestor(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    source: str,
    aliases: set[str],
) -> bool:
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.Call):
            parent_source = ast.get_source_segment(source, parent)
            if parent_source and _is_benchmark_dataset_query_source(parent_source, aliases):
                return True
        parent = parents.get(parent)
    return False


def scan_benchmark_dataset_tenant_violations(path: Path) -> list[TenantPredicateViolation]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            TenantPredicateViolation(
                path=path,
                line=exc.lineno or 1,
                reason="Python AST parse failed; failing closed",
            )
        ]
    aliases = _benchmark_dataset_aliases(tree)
    parents = _parent_map(tree)
    violations: list[TenantPredicateViolation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _is_benchmark_dataset_cypher(node.value) and not _has_bound_cypher_tenant_predicate(node.value):
                violations.append(
                    TenantPredicateViolation(
                        path=path,
                        line=_first_benchmark_dataset_line(node, node.value),
                        reason="BenchmarkDataset Cypher query is not tenant-constrained with a bound tenant_id",
                    )
                )
            continue

        if not isinstance(node, ast.Call):
            continue

        if _has_benchmark_query_call_ancestor(node, parents, source, aliases):
            continue

        expression = ast.get_source_segment(source, node)
        if expression is None:
            if any(
                isinstance(child, ast.Name) and child.id in aliases
                for child in ast.walk(node)
            ):
                violations.append(
                    TenantPredicateViolation(
                        path=path,
                        line=getattr(node, "lineno", 1),
                        reason="BenchmarkDataset query could not be classified; failing closed",
                    )
                )
            continue

        if _is_benchmark_dataset_query_source(expression, aliases) and not _has_local_tenant_constraint(
            node, expression, aliases
        ):
            violations.append(
                TenantPredicateViolation(
                    path=path,
                    line=_first_benchmark_dataset_line(node, expression),
                    reason="BenchmarkDataset query expression is not tenant-constrained",
                )
            )

    return violations


def test_benchmarkdataset_match_always_scopes_tenant() -> None:
    violations: list[TenantPredicateViolation] = []
    for repo_path in LAYER6_REPOSITORY_PATHS:
        for py_file in repo_path.rglob("*.py"):
            violations.extend(scan_benchmark_dataset_tenant_violations(py_file))

    assert not violations, "Layer 6 tenant-isolation query violations:\n" + "\n".join(
        violation.format(REPO_ROOT) for violation in violations
    )


def test_guard_flags_unsafe_query_when_file_also_contains_safe_query(tmp_path: Path) -> None:
    source = textwrap.dedent(
        """
        def safe(tx):
            return tx.run(
                "MATCH (d:BenchmarkDataset) WHERE d.tenant_id = $tenant_id RETURN d",
                tenant_id=tenant_id,
            )

        def unsafe(tx):
            return tx.run("MATCH (d:BenchmarkDataset) RETURN d")
        """
    )
    test_file = tmp_path / "mixed_repository.py"
    test_file.write_text(source, encoding="utf-8")

    violations = scan_benchmark_dataset_tenant_violations(test_file)

    assert len(violations) == 1
    unsafe_line = source[: source.index("MATCH (d:BenchmarkDataset) RETURN d")].count("\n") + 1
    assert violations[0].path == test_file
    assert violations[0].line == unsafe_line
    assert f"mixed_repository.py:{unsafe_line}" in violations[0].format(tmp_path)


def test_guard_allows_multiple_tenant_scoped_queries_in_one_file(tmp_path: Path) -> None:
    test_file = tmp_path / "safe_repository.py"
    test_file.write_text(
        textwrap.dedent(
            """
            def first(tx):
                return tx.run(
                    "MATCH (d:BenchmarkDataset) WHERE d.tenant_id = $tenant_id RETURN d",
                    tenant_id=tenant_id,
                )

            def second(tx):
                return tx.run(
                    "MATCH (d:BenchmarkDataset {dataset_id: $dataset_id, tenant_id: $tenant_id}) RETURN d",
                    dataset_id=dataset_id,
                    tenant_id=tenant_id,
                )
            """
        ),
        encoding="utf-8",
    )

    assert scan_benchmark_dataset_tenant_violations(test_file) == []


def test_guard_fails_closed_when_python_file_cannot_be_parsed(tmp_path: Path) -> None:
    test_file = tmp_path / "broken_repository.py"
    test_file.write_text("def broken(:\n", encoding="utf-8")

    violations = scan_benchmark_dataset_tenant_violations(test_file)

    assert len(violations) == 1
    assert "broken_repository.py:1" in violations[0].format(tmp_path)
    assert violations[0].reason == "Python AST parse failed; failing closed"


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [
        ("def f(session):\n    return session.query(BenchmarkDataset).all()\n", 1),
        ("def f(session):\n    return select(BenchmarkDataset)\n", 1),
        ("BDS = BenchmarkDataset\ndef f(session):\n    return session.query(BDS).all()\n", 1),
        (
            "def f(session):\n"
            "    return session.query(Industry).join(BenchmarkDataset).all()\n",
            1,
        ),
        (
            "def base(session):\n"
            "    return session.query(BenchmarkDataset)\n"
            "def scoped(session, tenant_id):\n"
            "    return base(session).filter(BenchmarkDataset.tenant_id == tenant_id)\n",
            1,
        ),
        (
            "def f(session, tenant_id):\n"
            "    return session.query(BenchmarkDataset).filter(tenant_id == tenant_id).all()\n",
            1,
        ),
        (
            "def f(session, tenant_id):\n"
            "    return session.query(BenchmarkDataset).filter(BenchmarkDataset.tenant_id == tenant_id).all()\n",
            0,
        ),
    ],
)
def test_guard_classifies_orm_benchmarkdataset_queries(
    tmp_path: Path, source: str, expected_count: int
) -> None:
    test_file = tmp_path / "orm_repository.py"
    test_file.write_text(source, encoding="utf-8")

    assert len(scan_benchmark_dataset_tenant_violations(test_file)) == expected_count


class _DummyRunResult:
    async def single(self):
        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _CaptureTx:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **params):
        self.calls.append((query, params))
        return _DummyRunResult()


@pytest.mark.asyncio
async def test_list_datasets_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_list_datasets(tx, industry=None, segment=None, tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "d.tenant_id = $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant


@pytest.mark.asyncio
async def test_get_dataset_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_get_dataset(tx, dataset_id="manufacturing-efficiency-2024", tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "d.tenant_id = $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant


@pytest.mark.asyncio
async def test_delete_dataset_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_delete_dataset(tx, dataset_id="manufacturing-efficiency-2024", tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "tenant_id: $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant
