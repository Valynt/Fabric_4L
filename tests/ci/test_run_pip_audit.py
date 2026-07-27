from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "run_pip_audit.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_pip_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _service(tmp_path: Path) -> Path:
    service = tmp_path / "services" / "example"
    service.mkdir(parents=True)
    (service / "pyproject.toml").write_text('[project]\nname = "example"\nversion = "1.0.0"\n')
    (service / "uv.lock").write_text('version = 1\n')
    return service


def _runner(report: object, scanner_status: int = 0) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if command[0] == "uv":
            Path(command[command.index("--output-file") + 1]).write_text("example==1.0.0\n")
            return subprocess.CompletedProcess(command, 0, "exported", "")
        report_path = Path(command[command.index("--output") + 1])
        report_path.write_text(json.dumps(report))
        return subprocess.CompletedProcess(command, scanner_status, "audited", "")

    return run


def _scan(module: ModuleType, tmp_path: Path, runner: Callable[..., subprocess.CompletedProcess[str]]):
    service = _service(tmp_path)
    return module.run_scan(
        service_name="example",
        service_dir=service,
        artifact_dir=tmp_path / "artifacts" / "example",
        command_runner=runner,
        executable_finder=lambda name: f"/usr/bin/{name}",
    )


def test_clean_report_writes_clean_diagnostic_and_sarif(tmp_path: Path) -> None:
    module = _load_module()

    status, diagnostic = _scan(module, tmp_path, _runner({"dependencies": []}, scanner_status=0))

    assert status == module.CLEAN_EXIT == 0
    assert diagnostic["outcome"] == "clean"
    assert diagnostic["exit_code"] == 0
    assert diagnostic["dependency_source"].endswith("services/example/uv.lock")
    assert diagnostic["vulnerabilities"] == []
    assert Path(diagnostic["requirements_file"]).read_text() == "example==1.0.0\n"
    sarif = json.loads(Path(diagnostic["sarif_file"]).read_text())
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"] == []


def test_vulnerability_report_fails_with_package_and_all_ids(tmp_path: Path) -> None:
    module = _load_module()
    report = {
        "dependencies": [
            {
                "name": "example",
                "version": "1.0.0",
                "vulns": [
                    {
                        "id": "PYSEC-2099-1",
                        "aliases": ["CVE-2099-0001", "GHSA-xxxx-yyyy-zzzz"],
                        "description": "example advisory",
                    }
                ],
            }
        ]
    }

    status, diagnostic = _scan(module, tmp_path, _runner(report, scanner_status=1))

    assert status == module.VULNERABLE_EXIT == 1
    assert diagnostic["outcome"] == "vulnerable"
    assert diagnostic["vulnerabilities"] == [
        {
            "package": "example",
            "ids": ["PYSEC-2099-1", "CVE-2099-0001", "GHSA-xxxx-yyyy-zzzz"],
        }
    ]
    sarif = json.loads(Path(diagnostic["sarif_file"]).read_text())
    assert sarif["runs"][0]["results"][0]["ruleId"] == "PYSEC-2099-1"


@pytest.mark.parametrize(
    ("report_writer", "scanner_status", "message"),
    [
        (lambda path: path.write_text("not-json"), 0, "malformed JSON"),
        (lambda path: None, 0, "did not produce a report"),
        (lambda path: path.write_text(json.dumps({"dependencies": [{"name": "", "vulns": []}]})), 0, "non-empty package name"),
        (lambda path: path.write_text(json.dumps({"dependencies": [{"name": "example", "vulns": [{"id": ""}]}]})), 1, "non-empty canonical id"),
    ],
)
def test_invalid_or_missing_reports_are_operational_errors(
    tmp_path: Path,
    report_writer: Callable[[Path], object],
    scanner_status: int,
    message: str,
) -> None:
    module = _load_module()

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if command[0] == "uv":
            Path(command[command.index("--output-file") + 1]).write_text("example==1.0.0\n")
            return subprocess.CompletedProcess(command, 0, "", "")
        report_writer(Path(command[command.index("--output") + 1]))
        return subprocess.CompletedProcess(command, scanner_status, "", "scanner stderr")

    status, diagnostic = _scan(module, tmp_path, runner)

    assert status == module.OPERATIONAL_ERROR_EXIT == 2
    assert diagnostic["outcome"] == "operational_error"
    assert message in diagnostic["error"]
    assert not Path(diagnostic["sarif_file"]).exists()


@pytest.mark.parametrize(
    ("scanner_status", "report", "message"),
    [
        (2, {"dependencies": []}, "unexpected exit code 2"),
        (0, {"dependencies": [{"name": "example", "vulns": [{"id": "CVE-1"}]}]}, "exit code 0"),
        (1, {"dependencies": []}, "exit code 1"),
    ],
)
def test_scanner_failure_and_exit_report_inconsistency_fail_closed(
    tmp_path: Path, scanner_status: int, report: object, message: str
) -> None:
    module = _load_module()

    status, diagnostic = _scan(module, tmp_path, _runner(report, scanner_status=scanner_status))

    assert status == module.OPERATIONAL_ERROR_EXIT
    assert diagnostic["outcome"] == "operational_error"
    assert message in diagnostic["error"]


def test_missing_lock_or_project_metadata_fails_without_running_commands(tmp_path: Path) -> None:
    module = _load_module()
    service = tmp_path / "services" / "example"
    service.mkdir(parents=True)

    status, diagnostic = module.run_scan(
        service_name="example",
        service_dir=service,
        artifact_dir=tmp_path / "artifacts",
        command_runner=lambda *_args, **_kwargs: pytest.fail("must not resolve unlocked metadata"),
        executable_finder=lambda name: f"/usr/bin/{name}",
    )

    assert status == module.OPERATIONAL_ERROR_EXIT
    assert diagnostic["outcome"] == "operational_error"
    assert "uv.lock and pyproject.toml" in diagnostic["error"]


def test_export_uses_locked_graph_and_export_failure_stops_before_scanner(tmp_path: Path) -> None:
    module = _load_module()
    commands: list[list[str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, "", "lockfile needs to be updated")

    status, diagnostic = _scan(module, tmp_path, runner)

    assert status == module.OPERATIONAL_ERROR_EXIT
    assert diagnostic["outcome"] == "operational_error"
    assert "frozen dependency export failed" in diagnostic["error"]
    assert len(commands) == 1
    assert commands[0][:2] == ["uv", "export"]
    assert "--locked" in commands[0]
    assert "--no-emit-project" in commands[0]


@pytest.mark.parametrize(("outcome", "saved_status", "expected"), [("clean", 0, 0), ("vulnerable", 1, 1), ("operational_error", 2, 2)])
def test_enforce_returns_saved_outcome_status(
    tmp_path: Path, outcome: str, saved_status: int, expected: int
) -> None:
    module = _load_module()
    diagnostic_path = tmp_path / "diagnostic.json"
    lock = tmp_path / "uv.lock"
    requirements = tmp_path / "requirements.txt"
    report = tmp_path / "report.json"
    sarif = tmp_path / "report.sarif"
    for path in (lock, requirements, sarif):
        path.write_text("evidence\n")
    dependencies = []
    if outcome == "vulnerable":
        dependencies = [{"name": "example", "vulns": [{"id": "CVE-2099-0001"}]}]
    report.write_text(json.dumps({"dependencies": dependencies}))
    diagnostic_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "service": "example",
                "outcome": outcome,
                "exit_code": saved_status,
                "dependency_source": str(lock),
                "requirements_file": str(requirements),
                "report_file": str(report),
                "sarif_file": str(sarif),
                "vulnerabilities": (
                    [{"package": "example", "ids": ["CVE-2099-0001"]}]
                    if outcome == "vulnerable"
                    else []
                ),
                "error": "scanner failed" if outcome == "operational_error" else None,
            }
        )
    )

    assert module.enforce(diagnostic_path, expected_status=saved_status) == expected


def test_enforce_fails_closed_for_missing_invalid_or_mismatched_diagnostic(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing.json"
    assert module.enforce(missing, expected_status=0) == module.OPERATIONAL_ERROR_EXIT

    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]")
    assert module.enforce(invalid, expected_status=0) == module.OPERATIONAL_ERROR_EXIT

    mismatch = tmp_path / "mismatch.json"
    mismatch.write_text(json.dumps({"schema_version": 1, "outcome": "clean", "exit_code": 0}))
    assert module.enforce(mismatch, expected_status=1) == module.OPERATIONAL_ERROR_EXIT


def test_enforce_rejects_clean_diagnostic_when_required_evidence_is_missing(tmp_path: Path) -> None:
    module = _load_module()
    diagnostic_path = tmp_path / "diagnostic.json"
    diagnostic_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "service": "example",
                "outcome": "clean",
                "exit_code": 0,
                "dependency_source": str(tmp_path / "uv.lock"),
                "requirements_file": str(tmp_path / "requirements.txt"),
                "report_file": str(tmp_path / "missing-report.json"),
                "sarif_file": str(tmp_path / "missing-report.sarif"),
                "vulnerabilities": [],
                "error": None,
            }
        )
    )

    assert module.enforce(diagnostic_path, expected_status=0) == module.OPERATIONAL_ERROR_EXIT
