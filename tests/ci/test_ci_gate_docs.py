from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".github" / "workflows" / "workflow-registry.json"
CI_GATES = ROOT / "docs" / "development" / "CI_GATES.md"


def test_ci_gate_inventory_has_one_row_per_registered_workflow() -> None:
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["workflows"]
    source = CI_GATES.read_text(encoding="utf-8")

    assert source.count("\n| `") == len(entries)
    for entry in entries:
        assert f"| `{Path(entry['path']).name}` |" in source


def test_ci_gate_inventory_documents_operational_triage_fields() -> None:
    source = CI_GATES.read_text(encoding="utf-8")

    for field in (
        "Classification",
        "Triggers",
        "Owner / triage",
        "Local command",
        "Dependencies",
        "Artifacts",
        "Runtime budget",
    ):
        assert field in source


def test_ci_gate_documentation_is_generated_without_drift() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/sync_ci_gate_docs.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
