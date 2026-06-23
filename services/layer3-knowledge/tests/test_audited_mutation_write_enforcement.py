from __future__ import annotations

import ast
import importlib.util
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

SPEC = importlib.util.spec_from_file_location("check_layer3_audited_relationship_writes", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audited_write_check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audited_write_check
SPEC.loader.exec_module(audited_write_check)


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
    violations: list[tuple[str, int, str, str]] = []

    for path in sorted(routes_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = audited_write_check.ScanVisitor(path)
        visitor.visit(tree)
        violations.extend(
            (str(item.path.relative_to(REPO_ROOT)), item.line, item.function, item.snippet)
            for item in visitor.violations
        )

    assert not violations, "Direct graph writes must route through AuditedGraphMutation helpers: " + str(violations)
