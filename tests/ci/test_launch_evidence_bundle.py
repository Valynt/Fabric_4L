from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "generate_launch_evidence_bundle.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_launch_evidence_bundle", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_non_staging_collection_does_not_require_staging_evidence(tmp_path: Path) -> None:
    module = _load_module()
    collector = module.LaunchEvidenceCollector(tmp_path, artifacts_only=True)

    results = collector.collect_all("evidence_archive")

    assert results
    assert all(result.item.stage != "staging" for result in results)
    assert {result.status for result in results} == {"missing"}


def test_generator_writes_dashboard_register_and_signoff_to_repo_root(tmp_path: Path) -> None:
    module = _load_module()
    results = module.LaunchEvidenceCollector(tmp_path, artifacts_only=True).collect_all("evidence_archive")

    summary = module.EvidenceDocs(tmp_path).write_all(results, dry_run=False, json_summary=Path(".tmp/summary.json"))

    assert (tmp_path / "docs" / "launch" / "readiness-dashboard.md").exists()
    assert (tmp_path / "docs" / "launch" / "launch-blocker-register.md").exists()
    assert (tmp_path / "docs" / "validation" / "launch_readiness_final_sign_off_evidence.md").exists()
    summary_file = tmp_path / ".tmp" / "summary.json"
    assert summary_file.exists()
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["summary"]["missing"] > 0
    assert summary["paths"]["dashboard"] == "docs/launch/readiness-dashboard.md"


def test_cli_dry_run_does_not_write_docs(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--up-to-stage",
            "evidence_archive",
            "--repo-root",
            str(tmp_path),
            "--json-summary",
            str(tmp_path / ".tmp" / "summary.json"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert not (tmp_path / "docs" / "launch" / "readiness-dashboard.md").exists()
    assert not (tmp_path / ".tmp" / "summary.json").exists()
    assert json.loads(result.stdout)["dry_run"] is True


def test_cli_artifacts_only_writes_json_summary(tmp_path: Path) -> None:
    summary_path = tmp_path / ".tmp" / "summary.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifacts-only",
            "--up-to-stage",
            "evidence_archive",
            "--repo-root",
            str(tmp_path),
            "--json-summary",
            str(summary_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["summary"]["missing"] > 0


def test_artifacts_only_summary_includes_launch_readiness_scores(tmp_path: Path) -> None:
    module = _load_module()
    summary_path = tmp_path / ".tmp" / "summary.json"
    evidence_root = tmp_path / "docs" / "launch" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "baseline-validators.json").write_text("{}", encoding="utf-8")

    results = module.LaunchEvidenceCollector(tmp_path, artifacts_only=True).collect_all("evidence_archive")
    module.EvidenceDocs(tmp_path).write_all(results, dry_run=False, json_summary=summary_path)

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    scores = payload["summary"]["scores"]

    assert scores["launch_readiness"] == 14.3
    assert scores["core_ga"] == 16.7
    assert scores["paid_ga"] == 16.7


def test_ci_backlog_json_adds_failure_health_without_running_history_collection(tmp_path: Path) -> None:
    module = _load_module()
    backlog_path = tmp_path / "docs" / "launch" / "evidence" / "ci-failure-backlog.json"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        json.dumps(
            {
                "summary": {"total_runs": 10, "failed_runs": 4},
                "failures": [
                    {
                        "workflow_name": "PR Checks",
                        "job_name": "contract-checks",
                        "failure_category": "contract drift",
                        "failure_signature": "openapi drift",
                        "count": 3,
                        "first_seen_date": "2026-05-27",
                        "owner": "Architecture",
                        "blocking_status": "merge-blocking",
                        "remediation_link": "https://example.test/issue/1",
                    },
                    {
                        "workflow_name": "PR Checks",
                        "job_name": "frontend-e2e",
                        "failure_category": "flaky test",
                        "failure_signature": "journey timeout",
                        "rerun_conclusion": "success",
                    },
                    {
                        "workflow_name": "PR Checks",
                        "job_name": "frontend-e2e",
                        "failure_category": "flaky test",
                        "failure_signature": "journey timeout",
                        "rerun_conclusion": "failure",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    results = module.LaunchEvidenceCollector(tmp_path, artifacts_only=True).collect_all("evidence_archive")
    health = module.CIFailureHealthCollector(tmp_path).collect(
        Path("docs/launch/evidence/ci-failure-backlog.json"),
        top_limit=2,
    )

    summary = module.EvidenceDocs(tmp_path).write_all(
        results,
        dry_run=False,
        json_summary=Path(".tmp/summary.json"),
        ci_failure_health=health,
    )

    dashboard = (tmp_path / "docs" / "launch" / "readiness-dashboard.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / ".tmp" / "summary.json").read_text(encoding="utf-8"))
    assert "## CI Failure Health" in dashboard
    assert "Failure rate: **40.0%**" in dashboard
    assert "Flaky rerun recovery: **1/2 (50.0%)**" in dashboard
    assert "PR Checks / contract-checks" in dashboard
    assert summary["summary"]["ci_failure_health"]["failed_runs"] == 4
    assert payload["summary"]["ci_failure_health"]["top_recurring_signatures"][0]["count"] == 3


def test_cli_does_not_include_ci_failure_health_unless_backlog_is_requested(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--artifacts-only",
            "--up-to-stage",
            "evidence_archive",
            "--repo-root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "ci_failure_health" not in payload["summary"]
