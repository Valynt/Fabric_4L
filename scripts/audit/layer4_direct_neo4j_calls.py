#!/usr/bin/env python3
"""List every direct Neo4j session.run / execute_query call in Layer 4."""

import ast
from pathlib import Path

ROOT = Path("services/layer4-agents/src/layer4_agents")


def find_calls(path: Path):
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("run", "execute_query"):
                print(f"{path}:{node.lineno}  {func.attr}()")


for path in ROOT.rglob("*.py"):
    find_calls(path)
