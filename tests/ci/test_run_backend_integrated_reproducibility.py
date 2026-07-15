from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "ci" / "run_backend_integrated_reproducibility.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_backend_integrated_reproducibility", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_junit(path: Path, *, tests: int = 20, failures: int = 0, errors: int = 0, skipped: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}"></testsuite>',
        encoding="utf-8",
    )


def test_ci_or_staging_requires_explicit_sha(monkeypatch):
    runner = load_runner_module()
    for key in ("RELEASE_CANDIDATE_SHA", "GITHUB_SHA"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(runner.PhaseError, match="release-candidate SHA is required"):
        runner.resolve_release_candidate_sha(None, evidence_environment="ci")

    with pytest.raises(runner.PhaseError, match="release-candidate SHA is required"):
        runner.resolve_release_candidate_sha(None, evidence_environment="staging")


def test_local_fallback_sha_is_tooling_only(monkeypatch):
    runner = load_runner_module()
    for key in ("RELEASE_CANDIDATE_SHA", "GITHUB_SHA"):
        monkeypatch.delenv(key, raising=False)

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(["git"], 0, stdout="abc123\n", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    sha, source = runner.resolve_release_candidate_sha(None, evidence_environment="local")

    assert sha == "abc123"
    assert source == "local_git_rev_parse_tooling_only"


def test_ci_environment_requires_approved_metadata(monkeypatch):
    runner = load_runner_module()
    args = SimpleNamespace(evidence_run_id=None, evidence_url=None)

    with pytest.raises(runner.PhaseError, match="CI evidence requires CI metadata"):
        runner.validate_approved_environment(
            args=args,
            env={},
            evidence_environment="ci",
            release_sha_source="explicit_or_environment",
        )

    with pytest.raises(runner.PhaseError, match="CI evidence requires one run identifier"):
        runner.validate_approved_environment(
            args=args,
            env={"CI": "true"},
            evidence_environment="ci",
            release_sha_source="explicit_or_environment",
        )

    metadata = runner.validate_approved_environment(
        args=args,
        env={"CI": "true", "GITHUB_RUN_ID": "12345"},
        evidence_environment="ci",
        release_sha_source="explicit_or_environment",
    )

    assert metadata["approvedForGateClosure"] is True
    assert metadata["environment"] == "ci"
    assert metadata["runId"] == "12345"


def test_staging_environment_requires_approved_metadata():
    runner = load_runner_module()
    missing_args = SimpleNamespace(evidence_run_id=None, evidence_url=None)

    with pytest.raises(runner.PhaseError, match="staging evidence requires --evidence-run-id"):
        runner.validate_approved_environment(
            args=missing_args,
            env={},
            evidence_environment="staging",
            release_sha_source="explicit_or_environment",
        )

    with pytest.raises(runner.PhaseError, match="staging evidence requires --evidence-url"):
        runner.validate_approved_environment(
            args=SimpleNamespace(evidence_run_id="staging-run-1", evidence_url=None),
            env={},
            evidence_environment="staging",
            release_sha_source="explicit_or_environment",
        )

    metadata = runner.validate_approved_environment(
        args=SimpleNamespace(evidence_run_id="staging-run-1", evidence_url="https://staging.example.test/evidence/1"),
        env={},
        evidence_environment="staging",
        release_sha_source="explicit_or_environment",
    )

    assert metadata["approvedForGateClosure"] is True
    assert metadata["environment"] == "staging"
    assert metadata["evidenceRunId"] == "staging-run-1"


@pytest.mark.parametrize(
    ("counts", "message"),
    [
        ({"failures": 1}, "failures=0 and errors=0"),
        ({"errors": 1}, "failures=0 and errors=0"),
        ({"skipped": 1}, "skipped=0"),
    ],
)
def test_verify_junit_rejects_failures_errors_skips(tmp_path, counts, message):
    runner = load_runner_module()
    junit_path = tmp_path / "junit.xml"
    write_junit(junit_path, **counts)

    with pytest.raises(runner.PhaseError, match=message):
        runner.verify_junit(junit_path)


def test_pair_junit_requires_20_tests(tmp_path):
    runner = load_runner_module()
    junit_path = tmp_path / "junit.xml"
    write_junit(junit_path, tests=19)

    with pytest.raises(runner.PhaseError, match="tests=20"):
        runner.verify_junit(junit_path, expected_tests=20)


def test_retry_flaky_requires_classification():
    runner = load_runner_module()

    with pytest.raises(runner.PhaseError, match="no --retry-classification"):
        runner.evaluate_retry_status(
            playwright_outputs=[{"phase": "pair", "output": "1 flaky", "retryArtifacts": []}],
            retry_classification=None,
        )


def test_retry_flaky_with_classification_records_residual_risk():
    runner = load_runner_module()

    status = runner.evaluate_retry_status(
        playwright_outputs=[{"phase": "pair", "output": "", "retryArtifacts": ["retry1/trace.zip"]}],
        retry_classification="frontend route readiness retry observed and retained",
    )

    assert status["status"] == "classified"
    assert status["classification"] == "frontend route readiness retry observed and retained"
    assert status["detections"][0]["retryArtifacts"] == ["retry1/trace.zip"]


def test_main_records_validator_failure_in_summary(tmp_path, monkeypatch):
    runner = load_runner_module()
    artifact_dir = tmp_path / "artifacts"
    seed_path = artifact_dir / "seed-report.json"
    phases_seen: list[str] = []

    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backend_integrated_reproducibility.py",
            "--environment",
            "ci",
            "--release-candidate-sha",
            "abc123",
            "--artifact-dir",
            str(artifact_dir),
            "--skip-stack-start",
        ],
    )

    def fake_run_phase(*, name, command, cwd, env, phases):
        phases_seen.append(name)
        phases.append(
            {
                "name": name,
                "command": command,
                "cwd": str(cwd),
                "startedAt": "2026-01-01T00:00:00Z",
                "finishedAt": "2026-01-01T00:00:00Z",
                "returnCode": 1 if name == "validate core GA launch evidence" else 0,
                "retryOrFlakyOutputDetected": False,
            }
        )
        if name == "seed backend-integrated validation data":
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(
                json.dumps({"aggregateStatus": "present", "requiredRowsPresent": True}),
                encoding="utf-8",
            )
        if name.startswith("run J1-only"):
            write_junit(artifact_dir / "playwright" / "j1-junit.xml")
        if name.startswith("run J11-only"):
            write_junit(artifact_dir / "playwright" / "j11-junit.xml", tests=5)
        if name.startswith("run J1+J11"):
            write_junit(artifact_dir / "playwright" / "junit.xml", tests=20)
        if name == "validate core GA launch evidence":
            raise runner.PhaseError("validate core GA launch evidence failed with exit code 1")
        return ""

    monkeypatch.setattr(runner, "run_phase", fake_run_phase)

    assert runner.main() == 1

    summary = json.loads((artifact_dir / "backend-integrated-reproducibility-summary.json").read_text(encoding="utf-8"))
    assert "validate core GA launch evidence" in phases_seen
    assert summary["validatorStatus"] == {"status": "FAIL"}
    assert summary["approvedEnvironment"]["approvedForGateClosure"] is True


def test_main_summary_contains_environment_scope_sha_retry_and_validator_status(tmp_path, monkeypatch):
    runner = load_runner_module()
    artifact_dir = tmp_path / "artifacts"
    seed_path = artifact_dir / "seed-report.json"

    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backend_integrated_reproducibility.py",
            "--environment",
            "ci",
            "--release-candidate-sha",
            "abc123",
            "--artifact-dir",
            str(artifact_dir),
            "--skip-stack-start",
        ],
    )

    def fake_run_phase(*, name, command, cwd, env, phases):
        phases.append(
            {
                "name": name,
                "command": command,
                "cwd": str(cwd),
                "startedAt": "2026-01-01T00:00:00Z",
                "finishedAt": "2026-01-01T00:00:00Z",
                "returnCode": 0,
                "retryOrFlakyOutputDetected": False,
            }
        )
        if name == "seed backend-integrated validation data":
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(
                json.dumps({"aggregateStatus": "present", "requiredRowsPresent": True}),
                encoding="utf-8",
            )
        if name.startswith("run J1-only"):
            write_junit(artifact_dir / "playwright" / "j1-junit.xml")
        if name.startswith("run J11-only"):
            write_junit(artifact_dir / "playwright" / "j11-junit.xml", tests=5)
        if name.startswith("run J1+J11"):
            write_junit(artifact_dir / "playwright" / "junit.xml", tests=20)
        return ""

    monkeypatch.setattr(runner, "run_phase", fake_run_phase)

    assert runner.main() == 0

    summary = json.loads((artifact_dir / "backend-integrated-reproducibility-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["releaseCandidateSha"] == "abc123"
    assert summary["releaseCandidateShaSource"] == "explicit_or_environment"
    assert summary["evidenceEnvironment"] == "ci"
    assert summary["evidenceScope"] == "CI_STAGING_CANDIDATE"
    assert summary["approvedEnvironment"]["approvedForGateClosure"] is True
    assert summary["retryFlakeStatus"] == {"status": "none", "classification": None, "detections": []}
    assert summary["validatorStatus"] == {"status": "PASS"}
