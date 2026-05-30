#!/usr/bin/env python3
"""Generate Layer 4 tool inventory report from canonical registry registration."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "services/layer4-agents/src/layer4_agents/tools"
TOOLS_INIT = TOOLS_DIR / "__init__.py"
OUTPUT = REPO_ROOT / "audit-output/layer4-tool-inventory.md"


class InitParser(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: dict[str, str] = {}
        self.registered_classes: list[str] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self.imports[local] = f"{module}.{alias.name}"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name != "create_default_registry":
            return
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr != "register" or not child.args:
                    continue
                callee = child.args[0]
                if isinstance(callee, ast.Call) and isinstance(callee.func, ast.Name):
                    self.registered_classes.append(callee.func.id)


def parse_top_level_symbols(py_file: Path) -> tuple[list[str], list[str], dict[str, str]]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    tool_names: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "name" and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                    tool_names[node.name] = item.value.value
    return classes, funcs, tool_names


def normalize_symbol(name: str) -> str:
    n = name.lower().replace("_", "")
    if n.endswith("tool"):
        n = n[: -len("tool")]
    return n


def build_report() -> str:
    init_tree = ast.parse(TOOLS_INIT.read_text(encoding="utf-8"))
    parser = InitParser()
    parser.visit(init_tree)

    registered_classes = parser.registered_classes

    class_occurrences: dict[str, list[str]] = defaultdict(list)
    internal_helpers: list[tuple[str, str]] = []
    module_symbols: dict[str, list[str]] = defaultdict(list)
    class_to_tool_name: dict[str, str] = {}

    for py_file in sorted(TOOLS_DIR.glob("*.py")):
        classes, funcs, tool_names = parse_top_level_symbols(py_file)
        rel = py_file.relative_to(REPO_ROOT).as_posix()

        for cls in classes:
            if cls in tool_names:
                class_to_tool_name[cls] = tool_names[cls]
            class_occurrences[cls].append(rel)
            if cls in {"BaseTool", "TenantAwareTool", "ToolRegistry", "ToolError", "ToolNotFoundError", "ToolValidationError", "PDFGenerator", "SafeExpressionEvaluator"}:
                internal_helpers.append((cls, rel))
            module_symbols[normalize_symbol(cls)].append(f"{cls} ({py_file.name})")

        for fn in funcs:
            if py_file.name in {"knowledge.py", "admin.py", "analytics.py", "files.py", "workflows.py", "registry.py"}:
                internal_helpers.append((fn, rel))
            module_symbols[normalize_symbol(fn)].append(f"{fn} ({py_file.name})")

    duplicate_classes = {k: v for k, v in class_occurrences.items() if len(v) > 1}

    alias_groups = {
        key: sorted(values)
        for key, values in module_symbols.items()
        if len(values) > 1
    }

    lines = [
        "# Layer 4 Tool Inventory Report",
        "",
        "Canonical source: `create_default_registry()` registration calls that populate `ToolRegistry`.",
        "",
        "## 1) Externally invocable tools",
        "",
        "These are the tools directly registered via `registry.register(...)` in `create_default_registry()`.",
        "",
        "| # | Registered class | Tool name (runtime) | Source |",
        "|---|------------------|---------------------|--------|",
    ]

    for idx, cls in enumerate(registered_classes, 1):
        source = parser.imports.get(cls, "(local)")
        runtime_name = class_to_tool_name.get(cls, normalize_symbol(cls))
        lines.append(f"| {idx} | `{cls}` | `{runtime_name}` | `{source}` |")

    lines += [
        "",
        "## 2) Internal/base helpers (not externally invocable registry entries)",
        "",
        "| Symbol | File |",
        "|--------|------|",
    ]

    for symbol, rel in sorted(set(internal_helpers)):
        lines.append(f"| `{symbol}` | `{rel}` |")

    lines += [
        "",
        "## 3) Aliases / duplicate names across files",
        "",
    ]

    if duplicate_classes:
        lines.append("### Duplicate class names (exact)")
        for name, files in sorted(duplicate_classes.items()):
            lines.append(f"- `{name}` in: {', '.join(f'`{f}`' for f in files)}")
    else:
        lines.append("### Duplicate class names (exact)")
        lines.append("- None detected.")

    lines += [
        "",
        "### Semantic aliases / naming overlap",
        "",
        "Overlaps are grouped by normalized name (case-folded, trailing `Tool` removed).",
        "",
    ]

    for key, values in sorted(alias_groups.items()):
        if key in {"toolerror", "toolnotfounderror", "toolvalidationerror"}:
            continue
        if len(values) < 2:
            continue
        lines.append(f"- `{key}`: " + ", ".join(f"`{v}`" for v in values))

    lines += [
        "",
        "Notable overlap requested for review:",
        "- `knowledge.py` function `get_entity` overlaps conceptually with `knowledge_tools.py` class `GetEntityTool`.",
    ]

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_report(), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
