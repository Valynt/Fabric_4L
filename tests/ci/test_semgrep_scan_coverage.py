from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/security-gates.yml"
UTIL_PATH = ROOT / "scripts/security/collect_scan_coverage.py"


def _load_util() -> Any:
    """Load the reporting utility without requiring it to be on sys.path."""
    spec = importlib.util.spec_from_file_location("collect_scan_coverage", UTIL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["collect_scan_coverage"] = module
    spec.loader.exec_module(module)
    return module


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _make_git_repo(
    tmp_path: Path, files: dict[str, str | bytes], gitignore: list[str] | None = None
) -> Path:
    """Create a minimal git repo with the given files and return its path."""
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    if gitignore:
        (tmp_path / ".gitignore").write_text(
            "\n".join(gitignore) + "\n", encoding="utf-8"
        )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    if files or gitignore:
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    return tmp_path


def _namespace(**kwargs: Any) -> Namespace:
    defaults: dict[str, Any] = {
        "json_path": None,
        "sarif_path": None,
        "output_dir": None,
        "scan_root": ".",
        "exclude": [],
        "max_target_bytes": 1_000_000,
        "workflow": "Security Gates",
        "job": "Semgrep CE Full Scan (SAST)",
        "commit_sha": None,
        "ref": None,
        "event": None,
        "scan_mode": "full",
        "scanner_version": "1.136.0",
        "setup_type": "python-package",
        "configuration": ["config/semgrep/registry/", ".semgrep/"],
        "status": None,
        "exit_code": 0,
        "started_at": None,
        "duration_seconds": None,
        "sarif_category": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestCollectScanCoverage:
    """Unit tests for scripts/security/collect_scan_coverage.py."""

    def test_no_findings_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "version": "2.1.0",
                    "results": [],
                    "errors": [],
                    "paths": {"scanned": ["src/app.py"]},
                    "time": {"profiling_times": {"total_time": 1.5}},
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["status"] == "success"
            assert evidence["coverage"]["scanned_files"] == 1
            assert evidence["coverage"]["candidate_files"] == 1
            assert evidence["findings"]["total"] == 0

    def test_findings_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "eval('1')\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "version": "2.1.0",
                    "results": [
                        {
                            "check_id": "reviewed.python-dangerous-eval",
                            "path": "src/app.py",
                            "start": {"line": 1, "col": 1},
                            "extra": {"severity": "ERROR"},
                        }
                    ],
                    "errors": [],
                    "paths": {"scanned": ["src/app.py"]},
                    "time": {},
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["status"] == "findings"
            assert evidence["findings"]["error"] == 1
            assert evidence["findings"]["total"] == 1

    def test_scanner_execution_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            util.collect_coverage(
                _namespace(
                    json_path=Path(td) / "missing.json",
                    output_dir=out,
                    scan_root=str(repo),
                    exit_code=2,
                )
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["status"] == "error"
            assert evidence["exit_code"] == 2
            assert (
                "Semgrep JSON output was not available"
                in evidence["reporting_limitations"][0]
            )

    def test_empty_repository(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "version": "2.1.0",
                    "results": [],
                    "errors": [],
                    "paths": {"scanned": []},
                    "time": {},
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["coverage"]["candidate_files"] == 0
            assert evidence["coverage"]["scanned_files"] == 0

    def test_skipped_files_with_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(
                Path(td),
                {
                    "src/app.py": "print(1)\n",
                    "src/big.bin": b"0" * 1_000_001,
                },
            )
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "version": "2.1.0",
                    "results": [],
                    "errors": [],
                    "paths": {
                        "scanned": ["src/app.py"],
                        "skipped": [
                            {"path": "src/big.bin", "reason": "exceeded_size_limit"}
                        ],
                    },
                    "time": {},
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["coverage"]["scanned_files"] == 1
            assert evidence["coverage"]["skipped_files"] == 1
            skipped = json.loads((out / "skipped-files.json").read_text())
            assert skipped[0]["reason"] == "exceeded_size_limit"

    def test_missing_optional_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            # Minimal JSON with only the scanned list.
            _write_json(json_path, {"paths": {"scanned": ["src/app.py"]}})
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["coverage"]["scanned_files"] == 1
            assert evidence["findings"]["total"] == 0

    def test_unsupported_semgrep_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            # 'paths' is a string instead of a dict, which the parser must survive.
            _write_json(json_path, {"paths": "unexpected", "results": []})
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["coverage"]["scanned_files"] is None
            assert any("JSON" in lim for lim in evidence["reporting_limitations"])

    def test_path_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "paths": {"scanned": [str((repo / "src" / "app.py").resolve())]},
                    "results": [],
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            scanned = (out / "scanned-files.txt").read_text().splitlines()
            assert scanned == ["src/app.py"]

    def test_rejects_outside_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "paths": {"scanned": ["/etc/passwd", "src/app.py"]},
                    "results": [],
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            scanned = (out / "scanned-files.txt").read_text().splitlines()
            assert "/etc/passwd" not in scanned
            assert "src/app.py" in scanned

    def test_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "paths": {"scanned": ["src/app.py"]},
                    "results": [],
                    "version": "2.1.0",
                },
            )
            # Inject a secret-looking token into the configuration list so it
            # would appear in the summary if redaction is missing.
            util.collect_coverage(
                _namespace(
                    json_path=json_path,
                    output_dir=out,
                    scan_root=str(repo),
                    configuration=["ghp_123456789012345678901234567890123456"],
                )
            )
            summary = (out / "job-summary.md").read_text()
            assert "ghp_" not in summary
            assert "REDACTED" in summary

    def test_deterministic_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(
                Path(td),
                {
                    "src/b.py": "print(2)\n",
                    "src/a.py": "print(1)\n",
                    "src/c.py": "print(3)\n",
                },
            )
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {
                    "paths": {"scanned": ["src/c.py", "src/a.py", "src/b.py"]},
                    "results": [],
                },
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            scanned = (out / "scanned-files.txt").read_text().splitlines()
            assert scanned == ["src/a.py", "src/b.py", "src/c.py"]

    def test_preserves_original_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {"paths": {"scanned": ["src/app.py"]}, "results": []},
            )
            util.collect_coverage(
                _namespace(
                    json_path=json_path,
                    output_dir=out,
                    scan_root=str(repo),
                    exit_code=7,
                )
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["exit_code"] == 7
            assert evidence["status"] == "error"

    def test_summary_generated_after_scanner_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            # No JSON output means Semgrep failed; coverage should still produce a
            # step summary that records the error state without masking it.
            util.collect_coverage(
                _namespace(
                    json_path=Path(td) / "missing.json",
                    output_dir=out,
                    scan_root=str(repo),
                    exit_code=2,
                )
            )
            summary = (out / "job-summary.md").read_text()
            assert "Result" in summary
            assert "Error" in summary
            assert "2" in summary

    def test_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_git_repo(Path(td), {"src/app.py": "print(1)\n"})
            out = Path(td) / "out"
            util = _load_util()
            json_path = Path(td) / "semgrep.json"
            _write_json(
                json_path,
                {"paths": {"scanned": ["src/app.py"]}, "results": []},
            )
            util.collect_coverage(
                _namespace(json_path=json_path, output_dir=out, scan_root=str(repo))
            )
            evidence = json.loads((out / "scan-coverage.json").read_text())
            assert evidence["schema_version"] == "1.0"
            assert set(evidence.keys()) >= {
                "schema_version",
                "scanner",
                "scanner_version",
                "setup_type",
                "workflow",
                "job",
                "scan_mode",
                "scan_root",
                "configuration",
                "status",
                "exit_code",
                "coverage",
                "findings",
                "artifacts",
                "reporting_limitations",
            }


class TestSecurityGatesWorkflow:
    """Contract tests for .github/workflows/security-gates.yml."""

    def test_semgrep_job_has_evidence_step(self) -> None:
        workflow = _workflow()
        steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
        step_names = [step.get("name") for step in steps]
        assert "Generate Semgrep scan coverage evidence" in step_names
        assert "Publish Semgrep scan coverage summary" in step_names

    def test_semgrep_job_produces_json_and_sarif(self) -> None:
        workflow = _workflow()
        steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
        run = next(
            step
            for step in steps
            if step.get("name") == "Run Semgrep CE (curated rules + local rules)"
        )["run"]
        assert "--json-output semgrep-full.json" in run
        assert "--sarif-output semgrep-full.sarif" in run
        assert "semgrep.exitcode" in run

    def test_fail_step_uses_json_severity(self) -> None:
        workflow = _workflow()
        steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
        fail = next(
            step
            for step in steps
            if step.get("name") == "Fail on ERROR-severity Semgrep findings"
        )["run"]
        assert "semgrep-full.json" in fail
        assert "severity" in fail
        assert "ERROR" in fail

    def test_evidence_steps_run_always(self) -> None:
        workflow = _workflow()
        steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
        evidence = next(
            step
            for step in steps
            if step.get("name") == "Generate Semgrep scan coverage evidence"
        )
        summary = next(
            step
            for step in steps
            if step.get("name") == "Publish Semgrep scan coverage summary"
        )
        assert evidence.get("if") == "always()"
        assert summary.get("if") == "always()"

    def test_evidence_artifact_upload_exists(self) -> None:
        workflow = _workflow()
        steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
        upload = next(
            step
            for step in steps
            if step.get("name") == "Upload Semgrep scan coverage evidence"
        )
        assert upload["if"] == "always()"
        assert upload["with"]["path"] == "artifacts/security/semgrep/"

    def test_no_continue_on_error_in_semgrep_job(self) -> None:
        workflow = _workflow()
        assert "continue-on-error" not in workflow["jobs"]["semgrep-full-scan"]
        for step in workflow["jobs"]["semgrep-full-scan"]["steps"]:
            assert step.get("continue-on-error") is None

    def test_no_duplicate_semgrep_sarif_categories(self) -> None:
        workflow = _workflow()
        categories = [
            step["with"]["category"]
            for step in workflow["jobs"]["semgrep-full-scan"]["steps"]
            if step.get("uses", "").startswith("github/codeql-action/upload-sarif")
        ]
        assert len(categories) == len(
            set(categories)
        ), f"duplicate categories: {categories}"
        assert "semgrep-full-scan" in categories
