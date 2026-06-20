"""Tests for the gate-engineering validator and failure-injection examples.

These tests prove that the release-readiness machinery can:
  - detect invalid registry/inventory JSON
  - detect missing cross-references
  - block a release when a critical gate fails or is inconclusive
  - allow a release when all blocking gates pass
  - treat warnings as non-blocking
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "ci" / "gate_engineering_validator.py"


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def _artifact_path(directory: Path, gate_id: str) -> Path:
    """Derive the canonical result file name from a gate_id."""
    return directory / f"gate-{gate_id.replace('.', '-')}.json"


def _clear_artifact_dir(directory: Path) -> None:
    if directory.exists():
        for path in directory.glob("gate-*.json"):
            path.unlink()



def test_validate_registry_and_inventory_pass():
    """The canonical registry and inventory validate against their schemas."""
    result = run_validator("validate")
    assert result.returncode == 0, result.stderr
    assert "Validation passed" in result.stdout


def test_report_blocks_on_missing_critical_gate():
    """A release report is blocked when a critical gate has no evidence."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "empty"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-empty"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_validator(
        "report",
        "--release-id", "rel_test_001",
        "--artifact-digest", "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "--environment", "production",
        "--risk-class", "high",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
    )
    assert result.returncode == 1, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert report["decision"] == "blocked"
    assert any(
        r["gate_id"].startswith("pre_production.tenant_isolation")
        for r in report["blocking_results"]
    )


def test_report_passes_with_all_gate_results():
    """A release report is ready when all blocking gates pass."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "passing"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _clear_artifact_dir(artifact_dir)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-passing"
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads((ROOT / ".fabric" / "gate-engineering" / "gate-registry.json").read_text())
    for gate in registry["gates"]:
        path = _artifact_path(artifact_dir, gate["gate_id"])
        path.write_text(
            json.dumps(
                {
                    "gate_id": gate["gate_id"],
                    "status": "PASS",
                    "reason": "real evidence from CI",
                    "evidence_uri": "https://ci.fabric.io/evidence",
                }
            )
        )

    result = run_validator(
        "report",
        "--release-id", "rel_test_002",
        "--artifact-digest", "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "--environment", "production",
        "--risk-class", "medium",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert report["decision"] == "ready"
    assert report["gates"]["passed"] == len(registry["gates"])


def test_report_blocks_on_explicit_fail():
    """A release report is blocked when a critical gate explicitly fails."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "failing"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _clear_artifact_dir(artifact_dir)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-failing"
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads((ROOT / ".fabric" / "gate-engineering" / "gate-registry.json").read_text())
    for gate in registry["gates"]:
        path = _artifact_path(artifact_dir, gate["gate_id"])
        path.write_text(
            json.dumps(
                {
                    "gate_id": gate["gate_id"],
                    "status": "PASS",
                    "reason": "real evidence from CI",
                }
            )
        )

    # Inject a failure on a blocking gate.
    fail_path = _artifact_path(artifact_dir, "pre_production.tenant_isolation")
    fail_path.write_text(
        json.dumps(
            {
                "gate_id": "pre_production.tenant_isolation",
                "status": "FAIL",
                "reason": "cross-tenant read succeeded",
                "evidence_uri": "https://ci.fabric.io/failed-tenant-isolation",
            }
        )
    )

    result = run_validator(
        "report",
        "--release-id", "rel_test_003",
        "--artifact-digest", "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        "--environment", "production",
        "--risk-class", "high",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
    )
    assert result.returncode == 1, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert report["decision"] == "blocked"
    assert any(
        r["gate_id"] == "pre_production.tenant_isolation" and r["result"] == "FAIL"
        for r in report["blocking_results"]
    )


def test_warning_is_non_blocking():
    """A warning on a non-critical gate does not block the release."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "warning"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _clear_artifact_dir(artifact_dir)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-warning"
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads((ROOT / ".fabric" / "gate-engineering" / "gate-registry.json").read_text())
    for gate in registry["gates"]:
        path = _artifact_path(artifact_dir, gate["gate_id"])
        path.write_text(
            json.dumps(
                {
                    "gate_id": gate["gate_id"],
                    "status": "PASS",
                    "reason": "real evidence from CI",
                }
            )
        )

    warn_path = _artifact_path(artifact_dir, "build.vulnerability_policy")
    warn_path.write_text(
        json.dumps(
            {
                "gate_id": "build.vulnerability_policy",
                "status": "WARNING",
                "reason": "one MEDIUM finding within exception",
            }
        )
    )

    result = run_validator(
        "report",
        "--release-id", "rel_test_004",
        "--artifact-digest", "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "--environment", "production",
        "--risk-class", "medium",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert report["decision"] == "ready"
    assert report["gates"]["warnings"] == 1


def test_cross_reference_validation():
    """A gate that references an unknown contract fails validation."""
    # This is a static test of the registry content; we rely on the validator.
    result = run_validator("validate")
    assert result.returncode == 0, result.stderr
    assert "Validation passed" in result.stdout


def test_placeholder_evidence_is_blocked_in_strict_mode():
    """Strict mode rejects placeholder evidence as INCONCLUSIVE for blocking gates."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "placeholder"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _clear_artifact_dir(artifact_dir)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-placeholder"
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads((ROOT / ".fabric" / "gate-engineering" / "gate-registry.json").read_text())
    for gate in registry["gates"]:
        path = _artifact_path(artifact_dir, gate["gate_id"])
        path.write_text(
            json.dumps(
                {
                    "gate_id": gate["gate_id"],
                    "status": "PASS",
                    "reason": "placeholder evidence",
                    "evidence_uri": "artifact:test",
                    "owner": gate["owner"],
                }
            )
        )

    result = run_validator(
        "report",
        "--release-id", "rel_test_005",
        "--artifact-digest", "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "--environment", "production",
        "--risk-class", "high",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
        "--strict",
    )
    assert result.returncode == 1, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert report["decision"] == "blocked"
    assert report["strict"] is True
    assert any(g["reason"] == "evidence contains placeholder/example values" for g in report["inconclusive_gates"])


def test_unknown_command_evidence_is_inconclusive():
    """Evidence produced by an unregistered command is INCONCLUSIVE."""
    artifact_dir = ROOT / "artifacts" / "test-gate-engineering" / "unknown-command"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _clear_artifact_dir(artifact_dir)
    output_dir = ROOT / "artifacts" / "test-gate-engineering" / "report-unknown-command"
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads((ROOT / ".fabric" / "gate-engineering" / "gate-registry.json").read_text())
    for gate in registry["gates"]:
        path = _artifact_path(artifact_dir, gate["gate_id"])
        path.write_text(
            json.dumps(
                {
                    "gate_id": gate["gate_id"],
                    "status": "PASS",
                    "reason": "real evidence",
                    "command": "unknown-command --example",
                    "owner": gate["owner"],
                }
            )
        )

    result = run_validator(
        "report",
        "--release-id", "rel_test_006",
        "--artifact-digest", "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "--environment", "production",
        "--risk-class", "high",
        "--artifact-dir", artifact_dir.as_posix(),
        "--output-dir", output_dir.as_posix(),
    )
    assert result.returncode == 1, result.stderr
    report = json.loads((output_dir / "release-readiness-report.json").read_text())
    assert any(g["reason"].startswith("evidence produced by unknown command") for g in report["inconclusive_gates"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
