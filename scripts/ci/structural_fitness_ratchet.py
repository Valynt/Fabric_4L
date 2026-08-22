"""CI gate: enforce structural fitness ratchets (ARCH-HOTSPOT).

Gate for Initiative E (hotspot reduction) of the transformation plan:

* **Module size** — no production module may exceed the agreed significant-LOC
  threshold unless it is listed in the baseline as an approved exception.
  Existing oversized modules are grandfathered; new ones fail.
* **Function complexity** — no net-new high-complexity (cyclomatic) functions
  beyond the approved baseline set.
* **Dependency cycles** — the import cycle count may not increase. The baseline
  records the currently known cycles so the count can only go down.

The gate follows the ratchet convention established by
``scripts/ci/type_escape_ratchet.py``: a checked-in baseline, ``--update`` to
regenerate, and exit code 0 (clean) / 1 (violation).

Usage
-----
    # Check against the current working tree (CI mode, default):
    python scripts/ci/structural_fitness_ratchet.py

    # Regenerate the checked-in baseline after an approved change:
    python scripts/ci/structural_fitness_ratchet.py --update

Exit codes
----------
    0  No violations.
    1  A new hotspot (oversized module, high-complexity function, or import
       cycle) was detected that is not covered by the baseline.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_BASELINE = Path("config/ci/structural_fitness_baseline.json")

# Production code roots scanned for hotspots.
PRODUCTION_ROOTS = ("services/", "packages/")
# Files that are never scanned (mirror type_escape_ratchet exclusions, plus
# test/harness paths which are not production modules).
EXCLUDED_PATTERNS = (
    "**/__pycache__/**",
    "**/.mypy_cache/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/tests/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/harness/**",
)
# Structural hotspot thresholds that classify a module or function as hot.
DEFAULT_SIZE_THRESHOLD = 1000  # significant (non-blank, non-comment) lines
DEFAULT_COMPLEXITY_THRESHOLD = 25  # McCabe cyclomatic complexity

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
@dataclass(frozen=True, order=True)
class ModuleFinding:
    module: str
    size: int
    threshold: int
    detail: str = ""


@dataclass(frozen=True, order=True)
class FunctionFinding:
    module: str
    name: str
    complexity: int
    threshold: int


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------
def is_excluded(path: str) -> bool:
    posix = path.replace("\\", "/")
    return any(fnmatch.fnmatch(posix, p) for p in EXCLUDED_PATTERNS)


def tracked_python_files(root: Path) -> list[str]:
    """Return git-tracked python files under PRODUCTION_ROOTS (excluded filtered)."""
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    out: list[str] = []
    for line in proc.stdout.splitlines():
        posix = line.replace("\\", "/")
        if not posix.endswith(".py"):
            continue
        if not (
            posix.startswith(PRODUCTION_ROOTS[0])
            or posix.startswith(PRODUCTION_ROOTS[1])
        ):
            continue
        if is_excluded(line):
            continue
        out.append(line)
    return out


# ---------------------------------------------------------------------------
# Module size
# ---------------------------------------------------------------------------
def significant_line_count(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            text = path.read_text()
        except OSError:
            return 0
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


# ---------------------------------------------------------------------------
# Function complexity (McCabe)
# ---------------------------------------------------------------------------
class _FunctionComplexityVisitor(ast.NodeVisitor):
    """Count the cyclomatic complexity of a single function body.

    Branches owned by nested function/async-function definitions are excluded
    because they are measured separately as their own complexity entries.
    """

    def __init__(self) -> None:
        self.complexity = 1

    def _walk_children_skipping_nested_defs(self, node: ast.AST) -> None:
        """Visit a function's children but do not descend into nested defs."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue  # nested function: measured separately
            self.visit(child)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._walk_children_skipping_nested_defs(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._walk_children_skipping_nested_defs(node)

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)


def function_complexity(node: ast.AST) -> int:
    """Compute McCabe cyclomatic complexity for a function node.

    Nested function bodies are excluded because they are reported as separate
    complexity entries by :func:`collect_complexities`.
    """
    visitor = _FunctionComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


def _collect_scope_complexities(
    node: ast.AST, prefix: str, results: list[tuple[str, int]]
) -> None:
    """Emit (qualified_name, mccabe) for every function/method at any depth."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{prefix}.{child.name}" if prefix else child.name
            results.append((name, function_complexity(child)))
            _collect_scope_complexities(child, name, results)
        elif isinstance(child, ast.ClassDef):
            name = f"{prefix}.{child.name}" if prefix else child.name
            _collect_scope_complexities(child, name, results)
        else:
            _collect_scope_complexities(child, prefix, results)


def collect_complexities(source: str) -> list[tuple[str, int]]:
    """Return [(qualified_name, mccabe), ...] for functions/methods at any depth.

    Nested functions (e.g. handlers defined inside a router factory) are
    measured separately under a dotted qualified name so their complexity does
    not inflate the enclosing function and cannot escape the ratchet.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results: list[tuple[str, int]] = []
    _collect_scope_complexities(tree, "", results)
    return results


# ---------------------------------------------------------------------------
# Import graph & cycles
# ---------------------------------------------------------------------------
def module_key(path: str) -> str | None:
    posix = path.replace("\\", "/")
    if ("/src/" in posix) and (
        posix.startswith("services/") or posix.startswith("packages/")
    ):
        return posix.split("/src/", 1)[1][:-3].replace("/", ".")
    return None


def resolve_import(
    imported: str, importer: str, mod_to_path: dict[str, str]
) -> str | None:
    if imported in mod_to_path:
        return imported
    parts = importer.split(".")
    for i in range(len(parts), -1, -1):
        cand = ".".join(parts[:i] + imported.split(".")).lstrip(".")
        if cand in mod_to_path:
            return cand
    return None


def resolve_relative_import(
    level: int, module: str | None, imported_name: str | None, importer: str,
    mod_to_path: dict[str, str],
) -> str | None:
    """Resolve a relative import (``level`` dots) to a concrete module key.

    ``module`` is ``None`` for pure relative imports such as ``from .. import
    main``; the target module is then the ``imported_name`` bound inside the
    package at ``level`` levels up from the importer.
    """
    parts = importer.split(".")
    if level > len(parts):
        return None
    base = parts[: len(parts) - level]
    if not base:
        return None
    payload = module if module else imported_name
    if not payload:
        return None
    full = ".".join(base + [payload])
    resolved = resolve_import(full, importer, mod_to_path)
    if resolved:
        return resolved
    return full if full in mod_to_path else None


def build_import_graph(files: list[str]) -> dict[str, set[str]]:
    mod_to_path: dict[str, str] = {}
    for f in files:
        key = module_key(f)
        if key:
            mod_to_path[key] = f
    adj: dict[str, set[str]] = {k: set() for k in mod_to_path}
    for f in files:
        importer = module_key(f)
        if not importer:
            continue
        path = Path(f)
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            try:
                source = path.read_text()
            except OSError:
                continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    resolved = resolve_import(name, importer, mod_to_path)
                    if resolved and resolved != importer:
                        adj[importer].add(resolved)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level > 0:
                        # Relative from-import (``from .pkg import a, b``) may
                        # bind several submodules; record one edge per bound
                        # name so ``from .routes import benchmarks, system``
                        # closes real cycles through the submodules.
                        for alias in node.names:
                            submod = f"{node.module}.{alias.name}"
                            resolved = resolve_relative_import(
                                node.level, submod, None, importer, mod_to_path
                            )
                            if not resolved:
                                resolved = resolve_import(
                                    submod, importer, mod_to_path
                                )
                            if resolved and resolved != importer:
                                adj[importer].add(resolved)
                    else:
                        # Absolute ``from foo import ...``
                        resolved = resolve_import(node.module, importer, mod_to_path)
                        if resolved and resolved != importer:
                            adj[importer].add(resolved)
                else:
                    # Pure relative import (``from .. import x``): each bound
                    # name resolves inside the package ``node.level`` levels up.
                    for alias in node.names:
                        resolved = resolve_relative_import(
                            node.level, None, alias.name, importer, mod_to_path
                        )
                        if resolved and resolved != importer:
                            adj[importer].add(resolved)
    return adj


def find_cycles(adj: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Return SCCs with more than one module (import cycles), sorted."""
    index = 0
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def strong_connect(v: str) -> None:
        nonlocal index
        indices[v] = low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, ()):
            if w not in indices:
                strong_connect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                cycles.append(tuple(sorted(scc)))

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 200000))
    for v in adj:
        if v not in indices:
            strong_connect(v)
    return sorted(cycles)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
def scan(root: Path, size_threshold: int, complexity_threshold: int) -> tuple[
    list[ModuleFinding], list[FunctionFinding], list[tuple[str, ...]]
]:
    files = tracked_python_files(root)
    oversized: list[ModuleFinding] = []
    hot_functions: list[FunctionFinding] = []
    for f in files:
        path = root / f
        module = module_key(f)
        if not module:
            continue
        size = significant_line_count(path)
        if size > size_threshold:
            oversized.append(ModuleFinding(module, size, size_threshold))
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            source = path.read_text()
        for name, cx in collect_complexities(source):
            if cx > complexity_threshold:
                hot_functions.append(
                    FunctionFinding(module, name, cx, complexity_threshold)
                )
    oversized.sort(key=lambda m: (-m.size, m.module))
    hot_functions.sort(key=lambda fn: (-fn.complexity, fn.module, fn.name))

    adj = build_import_graph(files)
    cycles = find_cycles(adj)
    return oversized, hot_functions, cycles


# ---------------------------------------------------------------------------
# Baseline load/write/compare
# ---------------------------------------------------------------------------
def load_baseline(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(
    path: Path,
    oversized: list[ModuleFinding],
    functions: list[FunctionFinding],
    cycles: list[tuple[str, ...]],
    size_threshold: int,
    complexity_threshold: int,
) -> None:
    payload = {
        "description": "Baseline for Initiative E hotspot reduction. Regenerate only after approved refactors.",
        "size_threshold": size_threshold,
        "complexity_threshold": complexity_threshold,
        "oversized_modules": [
            {"module": m.module, "size": m.size} for m in oversized
        ],
        "high_complexity_functions": [
            {"module": fn.module, "function": fn.name, "complexity": fn.complexity}
            for fn in functions
        ],
        "dependency_cycles": [list(c) for c in cycles],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def compare(
    oversized: list[ModuleFinding],
    functions: list[FunctionFinding],
    cycles: list[tuple[str, ...]],
    baseline: dict,
) -> list[str]:
    violations: list[str] = []
    current_oversized = {m.module for m in oversized}
    baseline_oversized = {
        m["module"] for m in baseline.get("oversized_modules", [])
    }
    for m in oversized:
        if m.module not in baseline_oversized:
            violations.append(
                f"oversized module {m.module} ({m.size} lines > threshold {m.threshold}) "
                "not in baseline"
            )
    for stale in sorted(baseline_oversized - current_oversized):
        violations.append(
            f"baseline entry for oversized module {stale} is stale "
            "(no longer oversized in the current scan); regenerate the baseline"
        )

    baseline_functions = {
        (f["module"], f["function"])
        for f in baseline.get("high_complexity_functions", [])
    }
    current_functions = {(fn.module, fn.name) for fn in functions}
    for fn in functions:
        if (fn.module, fn.name) not in baseline_functions:
            violations.append(
                f"high-complexity function {fn.module}::{fn.name} "
                f"(McCabe {fn.complexity} > {fn.threshold}) not in baseline"
            )
    for stale in sorted(baseline_functions - current_functions):
        module, name = stale
        violations.append(
            f"baseline entry for high-complexity function {module}::{name} is stale "
            "(no longer hot in the current scan); regenerate the baseline"
        )

    baseline_cycle_set = {tuple(c) for c in baseline.get("dependency_cycles", [])}
    current_cycle_set = set(cycles)
    for cycle in cycles:
        if cycle not in baseline_cycle_set:
            violations.append(f"new import cycle: {' -> '.join(cycle)}")
    for stale in sorted(baseline_cycle_set - current_cycle_set):
        violations.append(
            f"baseline entry for import cycle {' -> '.join(stale)} is stale "
            "(no longer present in the current scan); regenerate the baseline"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Initiative E structural fitness ratchet."
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--size-threshold", type=int, default=DEFAULT_SIZE_THRESHOLD)
    parser.add_argument(
        "--complexity-threshold", type=int, default=DEFAULT_COMPLEXITY_THRESHOLD
    )
    parser.add_argument(
        "--update", action="store_true", help="Regenerate the checked-in baseline."
    )
    args = parser.parse_args(argv)

    root = REPO_ROOT
    baseline_path = (
        args.baseline if args.baseline.is_absolute() else root / args.baseline
    )
    oversized, functions, cycles = scan(
        root, args.size_threshold, args.complexity_threshold
    )

    if args.update:
        write_baseline(
            baseline_path,
            oversized,
            functions,
            cycles,
            args.size_threshold,
            args.complexity_threshold,
        )
        print(
            f"Updated {baseline_path.relative_to(root)}: "
            f"{len(oversized)} oversized modules, {len(functions)} hot functions, "
            f"{len(cycles)} cycles."
        )
        return 0

    baseline = load_baseline(baseline_path)
    if not baseline:
        print("No baseline found; run with --update to record the current state.")
        return 1

    violations = compare(oversized, functions, cycles, baseline)
    if violations:
        print("Structural fitness violations not covered by the baseline:")
        for v in violations[:50]:
            print(f"  - {v}")
        if len(violations) > 50:
            print(f"  ... and {len(violations) - 50} more")
        print(
            "Approve only after review: "
            "python scripts/ci/structural_fitness_ratchet.py --update"
        )
        return 1

    print(
        f"Structural fitness ratchet passed: {len(oversized)} oversized modules, "
        f"{len(functions)} hot functions, {len(cycles)} cycles — no net-new hotspots."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())