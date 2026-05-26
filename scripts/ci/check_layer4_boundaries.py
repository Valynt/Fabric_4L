#!/usr/bin/env python3
from __future__ import annotations
import ast
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [ROOT / "services/layer4-agents/src", ROOT / "value_fabric/layer4"]

CONTEXT_PREFIXES = {
    "orchestration": ["workflows", "agents", "engine"],
    "tools": ["tools", "skills"],
    "memory": ["messaging", "models/run_envelope", "engine/state_manager"],
    "providers": ["integration", "models/account", "models/integration", "models/crm_sync_job"],
    "evaluation": ["harness", "models/workflow_config", "models/tool_schemas"],
    "api_surface": ["api", "contracts"],
}

ALLOWED = {
    "orchestration": {"tools", "memory", "providers", "evaluation", "api_surface"},
    "tools": {"providers", "memory", "evaluation", "api_surface"},
    "memory": {"api_surface"},
    "providers": set(),
    "evaluation": {"orchestration", "tools", "memory", "providers", "api_surface"},
    "api_surface": {"orchestration", "tools", "memory", "providers", "evaluation"},
}

def module_from_path(p: Path, root: Path) -> str:
    return ".".join(p.relative_to(root).with_suffix("").parts)

def context_for_module(module: str) -> str | None:
    rel = module.replace(".", "/")
    for ctx, prefixes in CONTEXT_PREFIXES.items():
        if any(rel == pre or rel.startswith(pre + "/") for pre in prefixes):
            return ctx
    return None

def resolve_import(module: str, node: ast.ImportFrom) -> str | None:
    if node.module is None:
        return None
    if node.level == 0:
        return node.module
    parts = module.split(".")
    base = parts[:-node.level]
    return ".".join(base + node.module.split("."))

def scan():
    graph = defaultdict(set)
    violations = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if any(skip in py.parts for skip in ("tests", ".venv", "site-packages")):
                continue
            mod = module_from_path(py, root)
            src_ctx = context_for_module(mod)
            if not src_ctx:
                continue
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                target = None
                if isinstance(node, ast.ImportFrom):
                    target = resolve_import(mod, node)
                elif isinstance(node, ast.Import) and node.names:
                    target = node.names[0].name
                if not target:
                    continue
                target_ctx = context_for_module(target)
                if not target_ctx or target_ctx == src_ctx:
                    continue
                graph[mod].add(target)
                if target_ctx not in ALLOWED.get(src_ctx, set()):
                    violations.append((py.relative_to(ROOT), node.lineno, src_ctx, target_ctx, target))
    return graph, violations

def transitive_hotspots(graph):
    memo = {}
    def dfs(n, seen):
        if n in memo:
            return memo[n]
        out = set()
        for m in graph.get(n, set()):
            if m in seen:
                continue
            out.add(m)
            out |= dfs(m, seen | {m})
        memo[n] = out
        return out
    rows = []
    for n in graph:
        rows.append((n, len(dfs(n, {n}))))
    return sorted(rows, key=lambda x: x[1], reverse=True)[:10]

def main() -> int:
    graph, violations = scan()
    print("Layer4 boundary report")
    if violations:
        print("\nViolations:")
        for path, line, s, t, imp in violations:
            print(f"- {path}:{line} [{s} -> {t}] import {imp}")
    else:
        print("\nNo context dependency violations found.")
    print("\nTop transitive hotspots:")
    for mod, count in transitive_hotspots(graph):
        print(f"- {mod}: {count}")
    return 1 if violations else 0

if __name__ == "__main__":
    raise SystemExit(main())
