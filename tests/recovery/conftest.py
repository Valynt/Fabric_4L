from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def assert_contains_all(text: str, tokens: list[str], *, label: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, f"{label} missing expected token(s): {missing}"


@pytest.fixture(scope="session")
def restore_dry_run_evidence(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    output_dir = tmp_path_factory.mktemp("restore-dry-run")
    script = ROOT / "scripts" / "ops" / "restore_dry_run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output_dir)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence_path = output_dir / "restore-dry-run-evidence.json"
    assert evidence_path.exists(), "restore dry-run evidence was not written"
    return json.loads(evidence_path.read_text(encoding="utf-8"))
