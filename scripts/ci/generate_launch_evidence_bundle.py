#!/usr/bin/env python3
"""Generate launch-readiness evidence docs from local commands or CI artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from classify_failure import FailureClassifier
except ImportError:  # pragma: no cover - import path fallback for direct module loading
    FailureClassifier = None  # type: ignore[assignment]

Stage = Literal["baseline", "local_quality", "contract_security", "evidence_archive", "staging"]
Status = Literal["passed", "failed", "missing", "timeout", "environment_dependent"]

STAGE_ORDER: tuple[Stage, ...] = (
    "baseline",
    "local_quality",
    "contract_security",
    "evidence_archive",
    "staging",
)


@dataclass(frozen=True)
class EvidenceItem:
    name: str
    stage: Stage
    command: str
    artifact_path: str
    blocks_core_ga: bool
    blocks_paid_ga: bool
    environment_dependent: bool = False


@dataclass(frozen=True)
class EvidenceResult:
    item: EvidenceItem
    status: Status
    classification: str
    artifact_found: bool
    command: str
    artifact_path: str
    exit_code: int | None = None
    log_excerpt: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["item"] = asdict(self.item)
        return payload


REQUIRED_EVIDENCE: tuple[EvidenceItem, ...] = (
    EvidenceItem("baseline-validators", "baseline", "python scripts/ci/validate_final_testing_launch_gate.py && python scripts/ci/validate_core_ga_launch_evidence.py", "docs/launch/evidence/baseline-validators.json", True, True),
    EvidenceItem("frontend-test-report", "local_quality", "pnpm --dir apps/web run test", "apps/web/test-results/frontend-test-report.json", False, False),
    EvidenceItem("frontend-build", "local_quality", "pnpm --dir apps/web run build", "docs/launch/evidence/frontend-build.json", True, True),
    EvidenceItem("contract-tests", "contract_security", "python -m pytest tests/contract -n 0 --json-report --json-report-file=contract-report.json", "contract-report.json", True, True),
    EvidenceItem("security-suite-report", "contract_security", "python -m pytest tests/security -n 0 --json-report --json-report-file=security-report.json", "security-report.json", True, True),
    EvidenceItem("layer4-agent-tests", "contract_security", "python -m pytest services/layer4-agents/tests --json-report --json-report-file=layer4-report.json", "layer4-report.json", True, True),
    EvidenceItem("launch-evidence-bundle", "evidence_archive", "python scripts/ci/generate_launch_evidence_bundle.py --artifacts-only", "docs/launch/readiness-dashboard.md", True, True),
    EvidenceItem("journey-slo-report", "staging", "pnpm --dir apps/web run test:journey-slo-gate", "apps/web/tmp/journey-slo-report.json", True, True, True),
    EvidenceItem("live-llm-provider-evidence", "staging", "staging live LLM validation with mock fallback disabled", "docs/launch/evidence/live-llm-provider-evidence.json", True, True, True),
    EvidenceItem("sso-oidc-evidence", "staging", "staging OIDC login/logout/failure mapping", "docs/launch/evidence/sso-oidc-evidence.json", True, True, True),
    EvidenceItem("billing-evidence", "staging", "staging billing meter/idempotency/reconciliation", "docs/launch/evidence/billing-evidence.json", False, True, True),
    EvidenceItem("rollback-restore-evidence", "staging", "production-like rollback/restore drill", "docs/launch/evidence/rollback-restore-evidence.json", True, True, True),
    EvidenceItem("telemetry-alerting-evidence", "staging", "staging telemetry dashboard and alert receiver test", "docs/launch/evidence/telemetry-alerting-evidence.json", True, True, True),
    EvidenceItem("performance-smoke-artifact", "staging", "production-like performance smoke", "docs/launch/evidence/performance-smoke-artifact.json", True, True, True),
)


class LaunchEvidenceCollector:
    def __init__(self, repo_root: Path, artifacts_only: bool = False, dry_run: bool = False) -> None:
        self.repo_root = repo_root.resolve()
        self.artifacts_only = artifacts_only
        self.dry_run = dry_run

    def collect_all(self, up_to_stage: Stage) -> list[EvidenceResult]:
        max_index = STAGE_ORDER.index(up_to_stage)
        items = [item for item in REQUIRED_EVIDENCE if STAGE_ORDER.index(item.stage) <= max_index]
        return [self.collect_item(item, include_staging=up_to_stage == "staging") for item in items]

    def collect_item(self, item: EvidenceItem, *, include_staging: bool) -> EvidenceResult:
        artifact = self.repo_root / item.artifact_path
        if artifact.exists():
            return EvidenceResult(item, "passed", "artifact_present", True, item.command, item.artifact_path)
        if item.environment_dependent and not include_staging:
            return EvidenceResult(item, "environment_dependent", "environment_dependent", False, item.command, item.artifact_path)
        if self.artifacts_only:
            return EvidenceResult(item, "missing", "artifact_missing", False, item.command, item.artifact_path)
        if self.dry_run:
            return EvidenceResult(item, "missing", "dry_run_not_executed", False, item.command, item.artifact_path)

        try:
            proc = subprocess.run(item.command, cwd=self.repo_root, shell=True, text=True, capture_output=True, timeout=600)
        except subprocess.TimeoutExpired as exc:
            output = "\n".join(part for part in (exc.stdout or "", exc.stderr or "") if part)
            return EvidenceResult(item, "timeout", self._classify(output), False, item.command, item.artifact_path, None, output[-1000:])

        output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
        artifact_found = artifact.exists()
        status: Status = "passed" if proc.returncode == 0 else "failed"
        return EvidenceResult(item, status, "passed" if status == "passed" else self._classify(output), artifact_found, item.command, item.artifact_path, proc.returncode, output[-1000:])

    @staticmethod
    def _classify(output: str) -> str:
        if FailureClassifier is None:
            return "UNKNOWN"
        results = FailureClassifier().classify_suite(output)
        return results[0].category_key if results else "UNKNOWN"


class EvidenceDocs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def write_all(self, results: list[EvidenceResult], *, dry_run: bool, json_summary: Path | None = None) -> dict[str, object]:
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        git_sha = self._git_sha()
        summary = self._summary(results)
        paths = {
            "dashboard": "docs/launch/readiness-dashboard.md",
            "blocker_register": "docs/launch/launch-blocker-register.md",
            "sign_off": "docs/validation/launch_readiness_final_sign_off_evidence.md",
        }

        if not dry_run:
            self._write(paths["dashboard"], self.dashboard(results, timestamp, git_sha))
            self._write(paths["blocker_register"], self.blocker_register(results, timestamp, git_sha))
            self._write(paths["sign_off"], self.sign_off(results, timestamp, git_sha))
            if json_summary:
                json_summary = self._resolve_output_path(json_summary)
                json_summary.parent.mkdir(parents=True, exist_ok=True)
                json_summary.write_text(json.dumps({"timestamp": timestamp, "git_sha": git_sha, "summary": summary, "results": [r.to_dict() for r in results]}, indent=2, sort_keys=True), encoding="utf-8")

        return {"timestamp": timestamp, "git_sha": git_sha, "summary": summary, "paths": paths, "dry_run": dry_run}

    def dashboard(self, results: list[EvidenceResult], timestamp: str, git_sha: str) -> str:
        scores = self._score_summary(results)
        lines = [
            "<!-- AUTO-GENERATED by scripts/ci/generate_launch_evidence_bundle.py - DO NOT EDIT MANUALLY -->",
            "",
            "# Launch Readiness Dashboard",
            "",
            f"Generated: {timestamp} | Commit: `{git_sha}`",
            "",
            f"- Launch readiness score: **{scores['launch_readiness']}%**",
            f"- Core GA readiness score: **{scores['core_ga']}%**",
            f"- Paid GA readiness score: **{scores['paid_ga']}%**",
            "",
            "| Evidence Item | Status | Stage | Classification | Artifact | Blocks GA | Blocks Paid GA |",
            "|---|---|---|---|---|---:|---:|",
        ]
        for result in results:
            lines.append(self._result_row(result))
        lines.append("")
        return "\n".join(lines)

    def blocker_register(self, results: list[EvidenceResult], timestamp: str, git_sha: str) -> str:
        scores = self._score_summary(results)
        lines = [
            "# Launch Blocker Register",
            "",
            "<!-- AUTO-GENERATED by scripts/ci/generate_launch_evidence_bundle.py - DO NOT EDIT MANUALLY -->",
            "",
            f"Generated: {timestamp} | Commit: `{git_sha}`",
            "",
            f"- Launch readiness score: **{scores['launch_readiness']}%**",
            f"- Core GA readiness score: **{scores['core_ga']}%**",
            f"- Paid GA readiness score: **{scores['paid_ga']}%**",
            "",
            "| Item | Status | Classification | Blocks Core GA | Blocks Paid GA | Required Action |",
            "|---|---|---|---:|---:|---|",
        ]
        for result in results:
            action = "None" if result.status == "passed" else self._action(result)
            lines.append(f"| {result.item.name} | {result.status} | {result.classification} | {self._yes(result.item.blocks_core_ga)} | {self._yes(result.item.blocks_paid_ga)} | {action} |")
        lines.append("")
        lines.append("Paid GA remains blocked unless billing evidence passes or paid launch is removed from scope.")
        lines.append("")
        return "\n".join(lines)

    def sign_off(self, results: list[EvidenceResult], timestamp: str, git_sha: str) -> str:
        summary = self._summary(results)
        scores = summary["scores"]
        core_blocked = any(r.status != "passed" and r.item.blocks_core_ga for r in results)
        paid_blocked = any(r.status != "passed" and r.item.blocks_paid_ga for r in results)
        lines = [
            "# Launch Readiness Final Sign-Off Evidence",
            "",
            "<!-- AUTO-GENERATED by scripts/ci/generate_launch_evidence_bundle.py - DO NOT EDIT MANUALLY -->",
            "",
            f"Generated: {timestamp} | Commit: `{git_sha}`",
            "",
            f"- Launch readiness score: {scores['launch_readiness']}%",
            f"- Core GA readiness score: {scores['core_ga']}%",
            f"- Paid GA readiness score: {scores['paid_ga']}%",
            f"- Passed: {summary['passed']}",
            f"- Failed: {summary['failed']}",
            f"- Missing: {summary['missing']}",
            f"- Environment dependent: {summary['environment_dependent']}",
            f"- Core GA blocked: {'YES' if core_blocked else 'NO'}",
            f"- Paid GA blocked: {'YES' if paid_blocked else 'NO'}",
            "",
            "This document records repository-owned evidence only. Environment-dependent production readiness remains unproven until staging evidence artifacts are present.",
            "",
            "## Evidence Detail",
            "",
            "| Evidence Item | Status | Classification | Artifact |",
            "|---|---|---|---|",
        ]
        for result in results:
            artifact = result.item.artifact_path if result.artifact_found else "-"
            lines.append(f"| {result.item.name} | {result.status} | {result.classification} | {artifact} |")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _summary(results: list[EvidenceResult]) -> dict[str, Any]:
        return {
            "passed": sum(r.status == "passed" for r in results),
            "failed": sum(r.status == "failed" for r in results),
            "missing": sum(r.status == "missing" for r in results),
            "timeout": sum(r.status == "timeout" for r in results),
            "environment_dependent": sum(r.status == "environment_dependent" for r in results),
            "total": len(results),
            "scores": EvidenceDocs._score_summary(results),
        }

    @staticmethod
    def _score_summary(results: list[EvidenceResult]) -> dict[str, float]:
        return {
            "launch_readiness": EvidenceDocs._score(
                [result for result in results if result.status != "environment_dependent"]
            ),
            "core_ga": EvidenceDocs._score(
                [
                    result
                    for result in results
                    if result.item.blocks_core_ga and result.status != "environment_dependent"
                ]
            ),
            "paid_ga": EvidenceDocs._score(
                [
                    result
                    for result in results
                    if result.item.blocks_paid_ga and result.status != "environment_dependent"
                ]
            ),
        }

    @staticmethod
    def _score(results: list[EvidenceResult]) -> float:
        """Return a numeric readiness percentage for machine-readable summaries.

        Empty collections intentionally return 0.0 so downstream JSON/markdown
        consumers can treat "no eligible evidence" as an unproven/failing score,
        rather than a missing or nullable field.
        """
        if not results:
            return 0.0
        return round((sum(result.status == "passed" for result in results) / len(results)) * 100, 1)

    def _git_sha(self) -> str:
        try:
            proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.repo_root, text=True, capture_output=True, timeout=10)
        except Exception:
            return "unknown"
        return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "unknown"

    def _write(self, relative: str, content: str) -> None:
        path = self.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _resolve_output_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.repo_root / path

    @staticmethod
    def _yes(value: bool) -> str:
        return "YES" if value else "NO"

    @staticmethod
    def _action(result: EvidenceResult) -> str:
        if result.status == "environment_dependent":
            return "Collect staging evidence artifact"
        if result.status == "missing":
            return "Provide artifact or run evidence command"
        if result.status == "timeout":
            return "Bisect and profile timeout"
        return "Triage failure classification"

    def _result_row(self, result: EvidenceResult) -> str:
        artifact = result.item.artifact_path if result.artifact_found else "-"
        return f"| {result.item.name} | {result.status} | {result.item.stage} | {result.classification} | {artifact} | {self._yes(result.item.blocks_core_ga)} | {self._yes(result.item.blocks_paid_ga)} |"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--artifacts-only", action="store_true")
    parser.add_argument("--up-to-stage", choices=STAGE_ORDER, default="evidence_archive")
    parser.add_argument("--dashboard-only", action="store_true", help="Compatibility flag; dashboard is generated with the normal doc set.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--json-summary", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    collector = LaunchEvidenceCollector(repo_root, artifacts_only=args.artifacts_only, dry_run=args.dry_run)
    results = collector.collect_all(args.up_to_stage)
    summary = EvidenceDocs(repo_root).write_all(results, dry_run=args.dry_run, json_summary=args.json_summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.dry_run:
        return 0
    failed_or_missing = [r for r in results if r.status in {"failed", "missing", "timeout"} and (r.item.blocks_core_ga or r.item.blocks_paid_ga)]
    return 2 if failed_or_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
