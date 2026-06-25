#!/usr/bin/env python3
"""Fail on Layer 3/4 Cypher scope risks with explicit classification governance.

This gate classifies each discovered query as:
- Safe: approved scoped helper markers are present.
- Unsafe: known anti-patterns (inline f-strings, tenant interpolation, etc.).
- Unknown: Cypher appears present but could not be proven safe.

Unknown findings must be explicitly allowlisted to preserve drift visibility.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = (
    ROOT / "services" / "layer3-knowledge" / "src",
    ROOT / "services" / "layer4-agents" / "src",
)
SKIP_PARTS = {"migrations", "__pycache__"}
APPROVED_ROUTE_MARKERS = (
    "TenantScopedCypher",
    "custom_tenant_query",
    "match_node_query",
    "ScopedQuery",
    "strict-scoped-query-execution",
)

CLASS_SAFE = "Safe"
CLASS_UNSAFE = "Unsafe"
CLASS_UNKNOWN = "Unknown"


@dataclass(frozen=True)
class QueryFinding:
    path: Path
    line: int
    function: str
    classification: str
    message: str

    def key(self) -> str:
        return f"{self.path.relative_to(ROOT).as_posix()}::{self.function}::{self.line}"


class QueryClassifier(ast.NodeVisitor):
    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        self.source_lines = source.splitlines()
        self.findings: list[QueryFinding] = []
        self.function_stack: list[str] = []

    def _function_name(self) -> str:
        return self.function_stack[-1] if self.function_stack else "<module>"

    def _add(self, node: ast.AST, classification: str, message: str) -> None:
        self.findings.append(
            QueryFinding(
                path=self.path,
                line=getattr(node, "lineno", 1),
                function=self._function_name(),
                classification=classification,
                message=message,
            )
        )

    def _window_contains(self, line: int, markers: tuple[str, ...], radius: int = 12) -> bool:
        start = max(0, line - radius)
        end = min(len(self.source_lines), line + radius)
        window = "\n".join(self.source_lines[start:end])
        return any(marker in window for marker in markers)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "run" and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.JoinedStr):
                self._add(node, CLASS_UNSAFE, "session.run received inline f-string Cypher query")
            elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                q = first_arg.value
                if "MATCH (" in q:
                    if self._window_contains(node.lineno, APPROVED_ROUTE_MARKERS):
                        self._add(node, CLASS_SAFE, "session.run Cypher query guarded by approved tenant-scoped marker")
                    else:
                        self._add(node, CLASS_UNKNOWN, "session.run constant Cypher query requires explicit allowlist or scoped helper marker")
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        rendered = "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
        if "tenant_id:" in rendered:
            if any(isinstance(child, ast.Name) and child.id in {"tenant_id", "effective_tenant_id"} for child in ast.walk(node)):
                self._add(node, CLASS_UNSAFE, "tenant_id must be passed as Neo4j parameter, not interpolated")
        if "type(" in rendered:
            if any(isinstance(child, ast.Name) and child.id in {"relationship_types", "rel_types_str"} for child in ast.walk(node)):
                self._add(node, CLASS_UNSAFE, "relationship type filters must use validated parameter lists")
        self.generic_visit(node)


def iter_python_files(target: Path) -> list[Path]:
    return sorted(
        p for p in target.rglob("*.py") if not any(part in SKIP_PARTS for part in p.parts)
    )


def load_unknown_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("allowlist", [])
    return {str(item["finding_key"]) for item in entries if isinstance(item, dict) and "finding_key" in item}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", help="Optional explicit target directories")
    parser.add_argument("--report-json", default="docs/audit/l3-l4-cypher-scope-report.json")
    parser.add_argument("--unknown-allowlist", default="config/production-readiness/l3-l4-cypher-unknown-allowlist.json")
    args = parser.parse_args()

    targets = [Path(t).resolve() for t in args.targets] if args.targets else list(DEFAULT_TARGETS)

    findings: list[QueryFinding] = []
    files_scanned = 0
    for target in targets:
        for path in iter_python_files(target):
            files_scanned += 1
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            classifier = QueryClassifier(path=path, source=source)
            classifier.visit(tree)
            findings.extend(classifier.findings)

    allowlisted_unknowns = load_unknown_allowlist((ROOT / args.unknown_allowlist).resolve())

    unsafe = [f for f in findings if f.classification == CLASS_UNSAFE]
    unknown = [f for f in findings if f.classification == CLASS_UNKNOWN]
    unknown_missing_allowlist = [f for f in unknown if f.key() not in allowlisted_unknowns]

    report_payload = {
        "targets": [
            (t.relative_to(ROOT).as_posix() if t.is_relative_to(ROOT) else str(t))
            for t in targets
        ],
        "files_scanned": files_scanned,
        "summary": {
            CLASS_SAFE: sum(1 for f in findings if f.classification == CLASS_SAFE),
            CLASS_UNSAFE: len(unsafe),
            CLASS_UNKNOWN: len(unknown),
            "unknown_missing_allowlist": len(unknown_missing_allowlist),
        },
        "findings": [
            {
                "path": f.path.relative_to(ROOT).as_posix(),
                "line": f.line,
                "function": f.function,
                "classification": f.classification,
                "message": f.message,
                "finding_key": f.key(),
                "allowlisted": f.classification == CLASS_UNKNOWN and f.key() in allowlisted_unknowns,
            }
            for f in findings
        ],
    }

    report_path = (ROOT / args.report_json).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Layer 3/4 Cypher scope report written: {report_path.relative_to(ROOT)}")
    print(f"Files scanned: {files_scanned}")
    print(f"Unsafe: {len(unsafe)} | Unknown: {len(unknown)} | Unknown (missing allowlist): {len(unknown_missing_allowlist)}")

    if unsafe:
        print("FAIL: unsafe findings detected")
        for f in unsafe:
            print(f"  {f.key()} :: {f.message}")
        return 1

    if unknown_missing_allowlist:
        print("FAIL: unknown findings require explicit allowlist entry")
        for f in unknown_missing_allowlist:
            print(f"  {f.key()} :: {f.message}")
        return 1

    print("PASS: no unsafe findings and all unknown findings are explicitly allowlisted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
