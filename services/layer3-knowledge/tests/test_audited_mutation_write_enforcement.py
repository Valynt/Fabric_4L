from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_layer3_audited_relationship_writes.py"
TARGETS = [
    "services/layer3-knowledge/src/api/routes",
    "services/layer3-knowledge/src/services",
    "services/layer3-knowledge/src/agents",
]
AUDITED_HELPERS = {"write_relationship", "delete_relationship", "write_node", "delete_node"}


def test_audited_relationship_write_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *TARGETS, "--report-json", "artifacts/test-layer3-audited-writes.json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    report = json.loads((REPO_ROOT / "artifacts" / "test-layer3-audited-writes.json").read_text(encoding="utf-8"))
    assert report["summary"]["violations"] == 0


def test_write_endpoints_use_audited_mutation_helpers() -> None:
    routes_root = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes"
    mutating_functions: list[tuple[str, str]] = []

    for path in sorted(routes_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorator_text = " ".join(ast.unparse(d) for d in node.decorator_list)
                if any(method in decorator_text for method in [".post", ".put", ".patch", ".delete"]):
                    body_source = ast.unparse(node)
                    if "AuditedGraphMutation" in body_source and any(helper in body_source for helper in AUDITED_HELPERS):
                        continue
                    mutating_functions.append((str(path.relative_to(REPO_ROOT)), node.name))

    assert not mutating_functions, "Mutating route handlers must call AuditedGraphMutation helpers: " + str(mutating_functions)
