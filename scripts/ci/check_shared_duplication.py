"""CI gate: enforce DRY within ``packages/shared`` (ARCH-DUPLICATION).

Detects copy-pasted logic inside the canonical shared package
``packages/shared/src/value_fabric/shared/`` using deterministic, stdlib-only
AST fingerprinting. It never inspects code outside that scope and never
modifies source.

Two fingerprint tiers are produced for every function/method body that is large
enough to matter (class bodies are intentionally excluded — data declarations
such as enums, dataclasses, and TypedDicts are shapes, not logic):

* **exact** — identical AST (only the docstring is stripped), which catches
  verbatim copy-paste.
* **normalized** — identifiers, attribute names, and literal values are
  normalized to placeholders first, which catches "same logic, different names
  and constants". This tier is intentionally coarser and therefore requires a
  larger body before it is considered.

The gate follows the ratchet convention established by
``scripts/ci/structural_fitness_ratchet.py``: a checked-in baseline, ``--update``
to regenerate, and exit code 0 (clean) / 1 (violation). A duplication *cluster*
is keyed by the sorted set of member locations (``module::qualified_name``), so
the baseline stays stable across unrelated refactors and only changes when
duplication is added or removed.

Usage
-----
    # Check against the current working tree (CI mode, default):
    python scripts/ci/check_shared_duplication.py

    # Regenerate the checked-in baseline after an approved dedup/waiver:
    python scripts/ci/check_shared_duplication.py --update

    # Emit a machine-readable sub-check envelope (used by check_governance.py):
    python scripts/ci/check_shared_duplication.py --json artifacts/governance/check-shared-duplication.json

Exit codes
----------
    0  No net-new duplication.
    1  New duplication cluster, or a stale baseline entry.
"""

from __future__ import annotations

import argparse
import ast
import copy
import fnmatch
import json
import subprocess
from pathlib import Path

# Functions/methods are the only AST nodes fingerprinted (class bodies are
# declarations, not logic), so the collected nodes are always function defs.
_FuncDef = ast.FunctionDef | ast.AsyncFunctionDef

DEFAULT_BASELINE = Path("config/ci/shared_duplication_baseline.json")
SCOPE = "packages/shared/src/value_fabric/shared/"

# Files inside the scope that are never fingerprinted.
EXCLUDED_PATTERNS = (
    "**/__pycache__/**",
    "**/tests/**",
    "**/test_*.py",
    "**/*_test.py",
)

# Minimum number of body statements (after docstring stripping) required before
# a function/method body is considered significant enough to fingerprint.
MIN_STATEMENTS_EXACT = 4
MIN_STATEMENTS_NORMALIZED = 8

REPO_ROOT = Path(__file__).resolve().parents[2]

CHECK_ID = "check-shared-duplication"
CHECK_NAME = "Shared-package DRY (duplication) ratchet"


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------
def is_excluded(path: str) -> bool:
    posix = path.replace("\\", "/")
    return any(fnmatch.fnmatch(posix, p) for p in EXCLUDED_PATTERNS)


def tracked_files(root: Path) -> list[str]:
    """Return git-tracked python files under SCOPE, exclusions applied."""
    proc = subprocess.run(
        ["git", "ls-files", "--", SCOPE],
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
        if is_excluded(posix):
            continue
        out.append(line)
    return out


def module_key(path: str) -> str | None:
    posix = path.replace("\\", "/")
    if "/src/" in posix and posix.startswith("packages/"):
        return posix.split("/src/", 1)[1][:-3].replace("/", ".")
    return None


# ---------------------------------------------------------------------------
# AST collection
# ---------------------------------------------------------------------------
def _collect_defs(
    node: ast.AST, prefix: str, results: list[tuple[str, _FuncDef]]
) -> None:
    """Emit ``(qualified_name, node)`` for every function/method at any depth.

    Class bodies themselves are not emitted: they are declarations (enums,
    dataclasses, TypedDicts), and their methods are still collected with the
    class name as a qualifier so method-level logic duplication is caught.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{prefix}.{child.name}" if prefix else child.name
            results.append((name, child))
            _collect_defs(child, name, results)
        elif isinstance(child, ast.ClassDef):
            name = f"{prefix}.{child.name}" if prefix else child.name
            _collect_defs(child, name, results)
        else:
            _collect_defs(child, prefix, results)


def collect_defs(source: str, filename: str = "<unknown>") -> list[tuple[str, _FuncDef]]:
    tree = ast.parse(source, filename=filename)
    results: list[tuple[str, _FuncDef]] = []
    _collect_defs(tree, "", results)
    return results


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------
def _strip_docstring_and_decorators(node: _FuncDef) -> _FuncDef:
    """Return a deep copy of ``node`` with decorators and docstring removed."""
    prepared = copy.deepcopy(node)
    prepared.decorator_list = []
    body = prepared.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        prepared.body = body[1:]
    return prepared


class _Normalizer(ast.NodeTransformer):
    """Replace identifiers, attribute names, and literals with placeholders.

    Structure (statement nesting, control flow, call/assignment shape) is
    preserved; only the things that vary between two copies of the same logic
    are erased. This makes ``def f(a): return a + 1`` and ``def g(b): return b +
    1`` produce the same normalized fingerprint.
    """

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="n", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.copy_location(ast.arg(arg="a", annotation=None), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.copy_location(ast.Constant(value="c"), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        return ast.copy_location(
            ast.Attribute(value=self.visit(node.value), attr="a", ctx=node.ctx),
            node,
        )

    def visit_alias(self, node: ast.alias) -> ast.AST:
        return ast.copy_location(ast.alias(name="m", asname=None), node)

    def visit_keyword(self, node: ast.keyword) -> ast.AST:
        return ast.copy_location(ast.keyword(arg="k", value=self.visit(node.value)), node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "f"
        node.returns = None
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = "f"
        node.returns = None
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = "c"
        return self.generic_visit(node)

    def normalize_statement(self, stmt: ast.stmt) -> ast.stmt:
        result = self.visit(stmt)
        if not isinstance(result, ast.stmt):
            raise TypeError(
                f"_Normalizer produced {type(result).__name__}, expected ast.stmt"
            )
        return result


def _body(node: _FuncDef) -> list[ast.stmt]:
    prepared = _strip_docstring_and_decorators(node)
    return list(prepared.body)


def fingerprint(node: _FuncDef, normalize: bool) -> str:
    """Fingerprint the *body* only (names and signatures are ignored).

    Two functions with copy-pasted bodies are duplication regardless of what
    they are called or how they are declared, so the enclosing name/signature
    is deliberately excluded. The qualified name is preserved separately as the
    cluster member key.
    """
    body = _body(node)
    if normalize:
        normalizer = _Normalizer()
        body = [normalizer.normalize_statement(stmt) for stmt in body]
    return ast.dump(ast.Module(body=body, type_ignores=[]), annotate_fields=False)


def body_statement_count(node: _FuncDef) -> int:
    count = 0

    def visit(current: ast.AST) -> None:
        nonlocal count
        if current is not node and isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            return
        if isinstance(current, ast.stmt):
            count += 1
        for child in ast.iter_child_nodes(current):
            visit(child)

    for statement in _body(node):
        visit(statement)
    return count


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------
def _cluster(
    defs: list[tuple[str, _FuncDef]],
    *,
    normalize: bool,
    min_statements: int,
) -> list[tuple[str, list[str]]]:
    """Group significant defs by fingerprint; return clusters with >= 2 members.

    Each returned cluster is ``(fingerprint, [member, ...])`` where a member is
    ``"module::qualified_name"`` and the list is sorted for stability.
    """
    index: dict[str, list[str]] = {}
    for name, node in defs:
        if body_statement_count(node) < min_statements:
            continue
        index.setdefault(fingerprint(node, normalize), []).append(name)
    clusters: list[tuple[str, list[str]]] = []
    for fp, members in index.items():
        if len(set(members)) >= 2:
            clusters.append((fp, sorted(set(members))))
    clusters.sort(key=lambda item: item[1])
    return clusters


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
def scan(root: Path) -> tuple[list[tuple[str, list[str]]], list[tuple[str, list[str]]]]:
    files = tracked_files(root)
    all_defs: list[tuple[str, _FuncDef]] = []
    for f in files:
        module = module_key(f)
        if not module:
            continue
        path = root / f
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        all_defs.extend(
            (f"{module}::{name}", node) for name, node in collect_defs(source, filename=f)
        )
    exact = _cluster(all_defs, normalize=False, min_statements=MIN_STATEMENTS_EXACT)
    normalized = _cluster(all_defs, normalize=True, min_statements=MIN_STATEMENTS_NORMALIZED)
    return exact, normalized


# ---------------------------------------------------------------------------
# Baseline load/write/compare
# ---------------------------------------------------------------------------
def load_baseline(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(
    path: Path,
    exact: list[tuple[str, list[str]]],
    normalized: list[tuple[str, list[str]]],
) -> None:
    payload = {
        "description": (
            "Baseline of known duplication clusters in packages/shared. "
            "Regenerate only after an approved dedup or waiver decision."
        ),
        "scope": SCOPE,
        "exact_clusters": [{"members": members} for _, members in exact],
        "normalized_clusters": [{"members": members} for _, members in normalized],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _member_sets(items: list[dict]) -> set[frozenset[str]]:
    return {frozenset(item.get("members", [])) for item in items}


def compare(
    exact: list[tuple[str, list[str]]],
    normalized: list[tuple[str, list[str]]],
    baseline: dict,
) -> list[dict]:
    """Return violation envelopes for net-new and stale duplication clusters."""
    violations: list[dict] = []
    tiers = (
        ("exact_clusters", exact, "exact duplication"),
        ("normalized_clusters", normalized, "normalized (same-logic) duplication"),
    )
    for key, clusters, label in tiers:
        current = {frozenset(members) for _, members in clusters}
        baseline_sets = _member_sets(baseline.get(key, []))
        for members in sorted(current - baseline_sets, key=sorted):
            violations.append(
                {
                    "path": ", ".join(sorted(members)),
                    "message": f"new {label} cluster: {', '.join(sorted(members))}",
                    "recommendation": (
                        "Deduplicate the shared logic or, if the duplication is "
                        "intentional, regenerate the baseline with "
                        "`python scripts/ci/check_shared_duplication.py --update`."
                    ),
                }
            )
        for members in sorted(baseline_sets - current, key=sorted):
            violations.append(
                {
                    "path": ", ".join(sorted(members)),
                    "message": (
                        f"stale baseline entry for {label} cluster "
                        f"{', '.join(sorted(members))} is no longer present; "
                        "regenerate the baseline"
                    ),
                    "recommendation": (
                        "Regenerate the baseline with "
                        "`python scripts/ci/check_shared_duplication.py --update`."
                    ),
                }
            )
    return violations


# ---------------------------------------------------------------------------
# Envelope / main
# ---------------------------------------------------------------------------
def envelope(
    status: str,
    baseline_present: bool,
    violations: list[dict],
) -> dict:
    return {
        "check_id": CHECK_ID,
        "name": CHECK_NAME,
        "scope": SCOPE,
        "status": status,
        "baseline_present": baseline_present,
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Shared-package DRY (duplication) ratchet."
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--update", action="store_true", help="Regenerate the checked-in baseline."
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="Write a machine-readable envelope here."
    )
    args = parser.parse_args(argv)

    root = REPO_ROOT
    baseline_path = (
        args.baseline if args.baseline.is_absolute() else root / args.baseline
    )
    exact, normalized = scan(root)

    if args.update:
        write_baseline(baseline_path, exact, normalized)
        try:
            display = str(baseline_path.relative_to(root))
        except ValueError:
            display = str(baseline_path)
        print(
            f"Updated {display}: "
            f"{len(exact)} exact clusters, {len(normalized)} normalized clusters."
        )
        return 0

    baseline = load_baseline(baseline_path)
    if not baseline:
        print("No baseline found; run with --update to record the current state.")
        if args.json is not None:
            out_path = args.json if args.json.is_absolute() else root / args.json
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(envelope("fail", False, []), indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
        return 1

    violations = compare(exact, normalized, baseline)
    status = "fail" if violations else "pass"

    if args.json is not None:
        out_path = args.json if args.json.is_absolute() else root / args.json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(envelope(status, True, violations), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    if violations:
        print("Shared-package duplication not covered by the baseline:")
        for v in violations[:50]:
            print(f"  - {v['message']}")
        if len(violations) > 50:
            print(f"  ... and {len(violations) - 50} more")
        print(
            "Approve only after review: "
            "python scripts/ci/check_shared_duplication.py --update"
        )
        return 1

    print(
        f"Shared-package DRY ratchet passed: {len(exact)} exact clusters, "
        f"{len(normalized)} normalized clusters — no net-new duplication."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
