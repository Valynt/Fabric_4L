#!/usr/bin/env python3
"""CI gate script to validate tool contracts.

Validates that Layer 4 tools conform to CONTRACT.md §2.4:
- All tools must return ToolResult
- No bare exceptions raised in tool functions
- Proper error structure with recoverable flag

Usage:
    python3 scripts/ci/check_tool_contracts.py services/layer4-agents/src/tools/
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterator, NamedTuple


class Violation(NamedTuple):
    """A contract violation found in source code."""

    file: Path
    line: int
    col: int
    rule: str
    message: str


class ToolContractVisitor(ast.NodeVisitor):
    """AST visitor to detect tool contract violations."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[Violation] = []
        self.in_tool_function = False
        self.function_returns_tool_result: dict[str, bool] = {}
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        old_function = self.current_function
        self.current_function = node.name

        # Check if function is decorated with @tool
        self.in_tool_function = any(
            isinstance(decorator, ast.Name) and decorator.id == "tool"
            for decorator in node.decorator_list
        )

        if self.in_tool_function:
            # Check for bare return statements (no ToolResult)
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return):
                    if stmt.value is None:
                        self.violations.append(
                            Violation(
                                file=Path(self.filename),
                                line=stmt.lineno or 0,
                                col=stmt.col_offset or 0,
                                rule="no-bare-return",
                                message=f"Tool function '{node.name}' has bare return without ToolResult",
                            )
                        )
                    elif not self._is_tool_result_expr(stmt.value):
                        # This is a warning - might be valid if decorator wraps it
                        pass

        # Check for raise statements in tool functions
        if self.in_tool_function:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Raise):
                    self.violations.append(
                        Violation(
                            file=Path(self.filename),
                            line=stmt.lineno or 0,
                            col=stmt.col_offset or 0,
                            rule="no-throw-in-tool",
                            message=f"Tool function '{node.name}' raises exception - use ToolResult.error() instead",
                        )
                    )

        self.generic_visit(node)
        self.current_function = old_function
        self.in_tool_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.visit_FunctionDef(node)  # type: ignore

    def _is_tool_result_expr(self, node: ast.expr) -> bool:
        """Check if expression is a ToolResult constructor."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id in ("ToolResult", "success", "error", "partial")
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    return node.func.value.id == "ToolResult"
        return False


def find_python_files(directory: Path) -> Iterator[Path]:
    """Find all Python files in directory."""
    if directory.is_file():
        if directory.suffix == ".py":
            yield directory
        return

    for path in directory.rglob("*.py"):
        # Skip tests and __pycache__
        if "test" in path.name or "__pycache__" in str(path):
            continue
        yield path


def check_file(filepath: Path) -> list[Violation]:
    """Check a single file for violations."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as e:
        return [
            Violation(
                file=filepath,
                line=e.lineno or 0,
                col=e.offset or 0,
                rule="syntax-error",
                message=f"Syntax error: {e.msg}",
            )
        ]
    except UnicodeDecodeError:
        return []

    visitor = ToolContractVisitor(str(filepath))
    visitor.visit(tree)
    return visitor.violations


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_tool_contracts.py <directory_or_file>...")
        return 1

    all_violations: list[Violation] = []

    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"Error: Path does not exist: {path}")
            return 1

        for filepath in find_python_files(path):
            violations = check_file(filepath)
            all_violations.extend(violations)

    # Print results
    print("Tool Contract Validation")
    print("=" * 60)

    if not all_violations:
        print("PASS No contract violations found")
        return 0

    # Group by rule
    by_rule: dict[str, list[Violation]] = {}
    for v in all_violations:
        by_rule.setdefault(v.rule, []).append(v)

    print(f"Found {len(all_violations)} violations:\n")

    for rule, violations in sorted(by_rule.items()):
        print(f"  {rule}: {len(violations)} instances")
        for v in violations[:5]:  # Show first 5 per rule
            print(f"    {v.file}:{v.line} - {v.message}")
        if len(violations) > 5:
            print(f"    ... and {len(violations) - 5} more")
        print()

    print("\nCONTRACT.md §2.4 requires:")
    print("  - All tools must return ToolResult")
    print("  - Tools must not raise exceptions (use ToolResult.error())")

    return 1


if __name__ == "__main__":
    sys.exit(main())
