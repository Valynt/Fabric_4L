"""Tests for the ValueOS benchmark and VMRT readiness validator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/validate_valueos_benchmark_vmrt_readiness.py"
ARTIFACT = ROOT / "artifacts/readiness/valueos-benchmark-vmrt-readiness.json"


def test_valueos_benchmark_vmrt_readiness_validator_writes_passing_artifact() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["schema_index"]["passed"] is True
    assert checks["benchmark_pack"]["passed"] is True
    assert checks["schema_gold_payloads"]["passed"] is True
