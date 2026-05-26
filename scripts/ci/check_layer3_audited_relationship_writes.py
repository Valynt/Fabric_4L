#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [
    Path("services/layer3-knowledge/src/api/routes"),
    Path("services/layer3-knowledge/src/services"),
    Path("services/layer3-knowledge/src/agents"),
]
WRITE_PATTERNS = ("CREATE", "MERGE", "DELETE")
QUERY_CALL_NAMES = {
    "run",
    "run_validated_query",
    "execute_tenant_scoped",
    "execute_tenant_query",
    "execute_scoped_query",
    "execute_tenant_cypher",
    "_run_cypher",
}
AUDITED_HELPERS = {
    "write_relationship",
    "delete_relationship",
    "write_node",
    "delete_node",
    "write_relationships_bulk",
    "delete_relationships_bulk",
    "write_nodes_bulk",
    "delete_nodes_bulk",
}


@dataclass
class Violation:
    path: Path
    line: int
    function: str
    snippet: str


class ScanVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[Violation] = []
        self.function_stack: list[str] = []

    def _function_name(self) -> str:
        return self.function_stack[-1] if self.function_stack else "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Await(self, node: ast.Await) -> None:
        if isinstance(node.value, ast.Call) and self._is_audited_helper_call(node.value):
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_audited_helper_call(node):
            return

        if not self._is_query_execution_call(node):
            self.generic_visit(node)
            return

        query_text = self._extract_query_arg(node)
        if query_text and self._contains_direct_write(query_text):
            self.violations.append(
                Violation(
                    path=self.path,
                    line=getattr(node, "lineno", 1),
                    function=self._function_name(),
                    snippet=self._snippet(query_text),
                )
            )
        self.generic_visit(node)

    @staticmethod
    def _snippet(text: str) -> str:
        normalized = " ".join(text.split())
        return normalized[:180]

    @staticmethod
    def _contains_direct_write(text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text.upper())
        return any(re.search(rf"\\b{word}\\b", normalized) for word in WRITE_PATTERNS)

    @staticmethod
    def _is_audited_helper_call(node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in AUDITED_HELPERS
        if isinstance(node.func, ast.Name):
            return node.func.id in AUDITED_HELPERS
        return False

    @staticmethod
    def _is_query_execution_call(node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in QUERY_CALL_NAMES
        if isinstance(node.func, ast.Name):
            return node.func.id in QUERY_CALL_NAMES
        return False

    def _extract_query_arg(self, node: ast.Call) -> str | None:
        candidates: list[ast.AST] = []
        if node.args:
            candidates.append(node.args[0])
        for kw in node.keywords:
            if kw.arg and kw.arg.lower() in {"query", "cypher", "statement", "q"}:
                candidates.append(kw.value)
        for candidate in candidates:
            value = self._literal_string(candidate)
            if value:
                return value
        return None

    def _literal_string(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
            return "".join(parts) if parts else None
        return None


def _iter_files(target: Path) -> list[Path]:
    return sorted(p for p in target.rglob("*.py") if "__pycache__" not in p.parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*", help="Directories to scan")
    parser.add_argument("--report-json", default="artifacts/layer3-audited-mutation-violations.json")
    args = parser.parse_args()

    targets = [Path(t) for t in args.targets] if args.targets else DEFAULT_TARGETS
    resolved_targets = [(ROOT / t).resolve() if not t.is_absolute() else t.resolve() for t in targets]

    violations: list[Violation] = []
    parse_errors: list[dict[str, str | int]] = []

    for target in resolved_targets:
        for path in _iter_files(target):
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                parse_errors.append({"path": str(path.relative_to(ROOT)), "line": int(exc.lineno or 1), "error": str(exc.msg)})
                continue
            visitor = ScanVisitor(path)
            visitor.visit(tree)
            violations.extend(visitor.violations)

    report = {
        "targets": [str(t.relative_to(ROOT) if t.is_relative_to(ROOT) else t) for t in resolved_targets],
        "summary": {"violations": len(violations), "parse_errors": len(parse_errors)},
        "violations": [
            {
                "path": str(v.path.relative_to(ROOT)),
                "line": v.line,
                "function": v.function,
                "query_snippet": v.snippet,
            }
            for v in violations
        ],
        "parse_errors": parse_errors,
    }

    output = (ROOT / args.report_json).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Layer3 audited mutation write check report: {output.relative_to(ROOT)}")
    if violations:
        print("FAIL: direct Cypher relationship writes detected outside audited mutation helpers")
        for v in violations[:20]:
            print(f"- {v.path.relative_to(ROOT)}::{v.function} L{v.line} :: {v.snippet}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
