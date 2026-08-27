#!/usr/bin/env python3
"""
Fabric_4L Flakiness Tracker v1.2.0

A production-ready flakiness detection engine that runs the test suite
multiple times, aggregates pass/fail outcomes per test, and generates
detailed markdown + JSON reports for CI integration.

Usage:
    python flakiness_tracker.py --times 5 --output report.md --json report.json
    python flakiness_tracker.py --times 10 --backend-only --json backend.json
    python flakiness_tracker.py --times 5 --frontend-only --output frontend.md
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

__version__ = "1.2.0"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration constants
# ──────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]

# Ensure the repository root is importable for cross-script imports
# (scripts.ci.*) when invoked as `python scripts/ci/flakiness_tracker.py`.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_RUNS = 5
SEVERITY_GREEN = 100.0  # Perfect consistency
SEVERITY_YELLOW_MIN = 95.0  # Warning threshold
SEVERITY_RED = 95.0  # Failure threshold

# Pytest markers mapped to execution commands
BACKEND_TEST_CMD = [
    sys.executable, "-m", "pytest",
    "-q",
    "--tb=short",
    "-p", "no:cacheprovider",
    "--disable-warnings",
]

FRONTEND_TEST_CMD = [
    "npx", "vitest", "run",
    "--reporter=verbose",
]

# Markers that can be targeted individually for granular flakiness analysis
FLAKINESS_TARGET_MARKERS = [
    "unit",
    "integration",
    "contract_static",
    "tenant_boundary",
    "security",
]


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class TestIdentifier:
    """Canonical identifier for a test case."""
    nodeid: str
    suite: str  # 'backend' | 'frontend' | 'e2e'
    marker: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.nodeid, self.suite))


@dataclasses.dataclass
class TestResult:
    """Outcome of a single test attempt."""
    passed: bool
    duration_ms: float
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclasses.dataclass
class TestFlakinessRecord:
    """Aggregated flakiness data for a single test across multiple runs."""
    test_id: TestIdentifier
    attempts: int = 0
    passes: int = 0
    failures: int = 0
    skips: int = 0
    results: List[TestResult] = dataclasses.field(default_factory=list)
    durations_ms: List[float] = dataclasses.field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return (self.passes / self.attempts) * 100.0

    @property
    def consistency(self) -> float:
        """Consistency score: 100% if all same outcome, lower if mixed."""
        if self.attempts == 0:
            return 0.0
        max_outcome = max(self.passes, self.failures, self.skips)
        return (max_outcome / self.attempts) * 100.0

    @property
    def avg_duration_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        return sum(self.durations_ms) / len(self.durations_ms)

    @property
    def is_flaky(self) -> bool:
        """A test is flaky if it has mixed outcomes across runs."""
        return 0 < self.passes < self.attempts

    @property
    def severity(self) -> str:
        rate = self.pass_rate
        if rate == 100.0:
            return "stable"
        if rate >= SEVERITY_YELLOW_MIN:
            return "warning"
        return "critical"

    @property
    def severity_badge(self) -> str:
        return {
            "stable": "🟢",
            "warning": "🟡",
            "critical": "🔴",
        }[self.severity]


@dataclasses.dataclass
class FlakinessReport:
    """Complete flakiness analysis report."""
    generated_at: str
    version: str
    total_runs: int
    records: List[TestFlakinessRecord]
    metadata: Dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def total_tests(self) -> int:
        return len(self.records)

    @property
    def flaky_tests(self) -> List[TestFlakinessRecord]:
        return [r for r in self.records if r.is_flaky]

    @property
    def critical_tests(self) -> List[TestFlakinessRecord]:
        return [r for r in self.records if r.severity == "critical"]

    @property
    def warning_tests(self) -> List[TestFlakinessRecord]:
        return [r for r in self.records if r.severity == "warning"]

    @property
    def overall_pass_rate(self) -> float:
        total_attempts = sum(r.attempts for r in self.records)
        total_passes = sum(r.passes for r in self.records)
        if total_attempts == 0:
            return 0.0
        return (total_passes / total_attempts) * 100.0


# ──────────────────────────────────────────────────────────────────────────────
# Test execution
# ──────────────────────────────────────────────────────────────────────────────

def _run_subprocess(
    cmd: List[str],
    cwd: Path = REPO_ROOT,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Execute a subprocess with timeout and error handling."""
    merged_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-9,
            stdout=exc.stdout or "",
            stderr=f"TIMEOUT after {timeout}s",
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr=str(exc),
        )


def _parse_pytest_json_report(report_path: Path) -> List[TestResult]:
    """Parse pytest-json-report output into TestResult objects."""
    results: List[TestResult] = []
    if not report_path.exists():
        return results
    try:
        data = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return results

    for test in data.get("tests", []):
        outcome = test.get("outcome", "")
        results.append(TestResult(
            passed=(outcome == "passed"),
            duration_ms=test.get("call", {}).get("duration", 0) * 1000,
            error_message=test.get("call", {}).get("longrepr", ""),
        ))
    return results


def _parse_pytest_short_output(stdout: str) -> Dict[str, TestResult]:
    """Parse pytest short output to extract per-test outcomes."""
    results: Dict[str, TestResult] = {}
    for line in stdout.splitlines():
        # Match lines like: tests/test_foo.py::test_bar PASSED [0.42s]
        if "::" in line and ("PASSED" in line or "FAILED" in line or "ERROR" in line):
            parts = line.split()
            nodeid = parts[0] if "::" in parts[0] else None
            if nodeid is None:
                continue
            passed = "PASSED" in line and "FAILED" not in line
            duration = 0.0
            for part in parts:
                if part.startswith("[") and part.endswith("s]"):
                    try:
                        duration = float(part[1:-2]) * 1000
                    except ValueError:
                        pass
            results[nodeid] = TestResult(
                passed=passed,
                duration_ms=duration,
                error_message=stdout if not passed else None,
            )
    return results


def _parse_vitest_json_output(stdout: str) -> Dict[str, TestResult]:
    """Parse Vitest JSON output for per-test outcomes."""
    results: Dict[str, TestResult] = {}
    try:
        # Vitest outputs JSON lines; find the summary object
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and "testResults" in line:
                data = json.loads(line)
                for suite in data.get("testResults", []):
                    for test in suite.get("assertionResults", []):
                        title = test.get("title", "unknown")
                        status = test.get("status", "")
                        duration = test.get("duration", 0)
                        results[title] = TestResult(
                            passed=(status == "passed"),
                            duration_ms=duration,
                            error_message=test.get("failureMessages", [None])[0],
                        )
                break
    except (json.JSONDecodeError, KeyError):
        pass
    return results


def run_backend_tests(
    marker: Optional[str] = None,
    times: int = 1,
    verbose: bool = False,
) -> Dict[TestIdentifier, TestFlakinessRecord]:
    """Run backend pytest suite and collect per-test results."""
    records: Dict[TestIdentifier, TestFlakinessRecord] = {}

    for run_idx in range(times):
        if verbose:
            print(f"  [backend] Run {run_idx + 1}/{times}...", file=sys.stderr)

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, dir=REPO_ROOT
        ) as tmp:
            tmp_path = Path(tmp.name)

        cmd = BACKEND_TEST_CMD + [
            "--json-report",
            f"--json-report-file={tmp_path.name}",
        ]
        if marker:
            cmd.extend(["-m", marker])

        result = _run_subprocess(cmd)

        # Parse JSON report first; fall back to stdout parsing
        parsed = _parse_pytest_json_report(tmp_path)
        if not parsed:
            parsed = _parse_pytest_short_output(result.stdout)

        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

        # Merge into records
        for nodeid, test_result in parsed.items():
            test_id = TestIdentifier(
                nodeid=nodeid,
                suite="backend",
                marker=marker,
            )
            if test_id not in records:
                records[test_id] = TestFlakinessRecord(test_id=test_id)
            rec = records[test_id]
            rec.attempts += 1
            if test_result.passed:
                rec.passes += 1
            else:
                rec.failures += 1
            rec.results.append(test_result)
            rec.durations_ms.append(test_result.duration_ms)

    return records


def run_frontend_tests(
    times: int = 1,
    verbose: bool = False,
) -> Dict[TestIdentifier, TestFlakinessRecord]:
    """Run frontend Vitest suite and collect per-test results."""
    records: Dict[TestIdentifier, TestFlakinessRecord] = {}

    for run_idx in range(times):
        if verbose:
            print(f"  [frontend] Run {run_idx + 1}/{times}...", file=sys.stderr)

        result = _run_subprocess(FRONTEND_TEST_CMD, cwd=REPO_ROOT / "apps" / "web")
        parsed = _parse_vitest_json_output(result.stdout)

        if not parsed:
            # Fallback: parse Vitest verbose output lines
            for line in result.stdout.splitlines():
                if any(s in line for s in ("✓", "✗", "FAIL", "PASS")):
                    title = line.strip().split("  ")[0] if "  " in line else line.strip()
                    passed = "✓" in line or "PASS" in line
                    test_id = TestIdentifier(nodeid=title, suite="frontend")
                    if test_id not in records:
                        records[test_id] = TestFlakinessRecord(test_id=test_id)
                    rec = records[test_id]
                    rec.attempts += 1
                    if passed:
                        rec.passes += 1
                    else:
                        rec.failures += 1
                    rec.results.append(TestResult(passed=passed, duration_ms=0.0))
        else:
            for nodeid, test_result in parsed.items():
                test_id = TestIdentifier(nodeid=nodeid, suite="frontend")
                if test_id not in records:
                    records[test_id] = TestFlakinessRecord(test_id=test_id)
                rec = records[test_id]
                rec.attempts += 1
                if test_result.passed:
                    rec.passes += 1
                else:
                    rec.failures += 1
                rec.results.append(test_result)
                rec.durations_ms.append(test_result.duration_ms)

    return records


# ──────────────────────────────────────────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────────────────────────────────────────

def _generate_run_fingerprint() -> str:
    """Generate a unique fingerprint for this run."""
    ts = datetime.now(timezone.utc).isoformat()
    return hashlib.sha256(ts.encode()).hexdigest()[:12]


def generate_markdown_report(report: FlakinessReport) -> str:
    """Render the flakiness report as Markdown."""
    lines: List[str] = [
        "# Fabric_4L Flakiness Report",
        "",
        f"**Generated:** {report.generated_at}  ",
        f"**Version:** {report.version}  ",
        f"**Runs per test:** {report.total_runs}  ",
        f"**Overall pass rate:** {report.overall_pass_rate:.1f}%  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total unique tests | {report.total_tests} |",
        f"| Flaky tests (mixed outcomes) | {len(report.flaky_tests)} |",
        f"| Critical (< 95% pass rate) | {len(report.critical_tests)} |",
        f"| Warning (95-99% pass rate) | {len(report.warning_tests)} |",
        f"| Stable (100% pass rate) | {len(report.records) - len(report.flaky_tests)} |",
        f"| Overall pass rate | {report.overall_pass_rate:.1f}% |",
        "",
        "---",
        "",
    ]

    # Flaky tests detail
    if report.flaky_tests:
        lines.extend([
            "## ⚠️ Flaky Tests Detail",
            "",
            "| Test | Suite | Pass Rate | Consistency | Severity | Avg Duration |",
            "|------|-------|-----------|-------------|----------|-------------|",
        ])
        for rec in sorted(report.flaky_tests, key=lambda r: r.pass_rate):
            lines.append(
                f"| `{rec.test_id.nodeid}` | {rec.test_id.suite} | "
                f"{rec.pass_rate:.0f}% | {rec.consistency:.0f}% | "
                f"{rec.severity_badge} {rec.severity} | {rec.avg_duration_ms:.0f}ms |"
            )
        lines.extend(["", "---", ""])

    # All tests table (collapsible for large suites)
    lines.extend([
        "## Full Results",
        "",
        "<details>",
        "<summary>Click to expand all test results</summary>",
        "",
        "| Test | Suite | Pass Rate | Consistency | Severity | Avg Duration |",
        "|------|-------|-----------|-------------|----------|-------------|",
    ])
    for rec in sorted(report.records, key=lambda r: (not r.is_flaky, r.pass_rate)):
        lines.append(
            f"| `{rec.test_id.nodeid}` | {rec.test_id.suite} | "
            f"{rec.pass_rate:.0f}% | {rec.consistency:.0f}% | "
            f"{rec.severity_badge} {rec.severity} | {rec.avg_duration_ms:.0f}ms |"
        )
    lines.extend(["", "</details>", ""])

    # Historical tracking section
    lines.extend([
        "---",
        "",
        "## Historical Tracking",
        "",
        "| Run Date | Total Tests | Flaky Tests | Pass Rate | Commit |",
        "|----------|-------------|-------------|-----------|--------|",
        f"| {report.generated_at[:10]} | {report.total_tests} | {len(report.flaky_tests)} | {report.overall_pass_rate:.1f}% | {report.metadata.get('commit_sha', 'N/A')[:8]} |",
        "",
        "_To append historical data, CI should append rows to this table._",
        "",
    ])

    # Footer
    lines.extend([
        "---",
        "",
        f"*Report generated by Fabric_4L Flakiness Tracker v{report.version}*",
    ])

    return "\n".join(lines)


def generate_json_report(report: FlakinessReport) -> Dict:
    """Render the flakiness report as JSON-serializable dict."""
    return {
        "version": report.version,
        "generated_at": report.generated_at,
        "metadata": report.metadata,
        "summary": {
            "total_runs_per_test": report.total_runs,
            "total_unique_tests": report.total_tests,
            "flaky_tests_count": len(report.flaky_tests),
            "critical_tests_count": len(report.critical_tests),
            "warning_tests_count": len(report.warning_tests),
            "stable_tests_count": report.total_tests - len(report.flaky_tests),
            "overall_pass_rate_percent": round(report.overall_pass_rate, 2),
        },
        "flaky_tests": [
            {
                "nodeid": rec.test_id.nodeid,
                "suite": rec.test_id.suite,
                "marker": rec.test_id.marker,
                "attempts": rec.attempts,
                "passes": rec.passes,
                "failures": rec.failures,
                "pass_rate_percent": round(rec.pass_rate, 2),
                "consistency_percent": round(rec.consistency, 2),
                "severity": rec.severity,
                "avg_duration_ms": round(rec.avg_duration_ms, 2),
                "durations_ms": [round(d, 2) for d in rec.durations_ms],
            }
            for rec in sorted(report.flaky_tests, key=lambda r: r.pass_rate)
        ],
        "all_tests": [
            {
                "nodeid": rec.test_id.nodeid,
                "suite": rec.test_id.suite,
                "pass_rate_percent": round(rec.pass_rate, 2),
                "consistency_percent": round(rec.consistency, 2),
                "severity": rec.severity,
            }
            for rec in sorted(report.records, key=lambda r: r.test_id.nodeid)
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flakiness_tracker",
        description="Fabric_4L Flakiness Tracker — detect and report flaky tests",
    )
    parser.add_argument(
        "--times", type=int, default=DEFAULT_RUNS,
        help=f"Number of times to run each test (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="",
        help="Path to write Markdown report",
    )
    parser.add_argument(
        "--json", "-j", type=str, default="",
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--backend-only", action="store_true",
        help="Only run backend tests",
    )
    parser.add_argument(
        "--frontend-only", action="store_true",
        help="Only run frontend tests",
    )
    parser.add_argument(
        "--marker", type=str, default="",
        help="Run only tests with this pytest marker",
    )
    parser.add_argument(
        "--fail-on-flaky", action="store_true",
        help="Exit with non-zero code if any flaky tests detected",
    )
    parser.add_argument(
        "--candidate-evidence",
        default=None,
        help="Write proposed-registration candidate evidence JSON to this path",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress to stderr",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    if args.times < 2:
        print("error: --times must be at least 2 to detect flakiness", file=sys.stderr)
        return 2

    # Detect commit SHA if available
    commit_sha = ""
    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if args.verbose:
        print(
            f"Fabric_4L Flakiness Tracker v{__version__} — {args.times} runs per test",
            file=sys.stderr,
        )
        print(f"Repository: {REPO_ROOT}", file=sys.stderr)

    all_records: Dict[TestIdentifier, TestFlakinessRecord] = {}

    # Run backend tests
    if not args.frontend_only:
        if args.verbose:
            print("\n[Backend] Starting test runs...", file=sys.stderr)
        backend_records = run_backend_tests(
            marker=args.marker or None,
            times=args.times,
            verbose=args.verbose,
        )
        all_records.update(backend_records)
        if args.verbose:
            print(
                f"[Backend] Collected {len(backend_records)} unique tests",
                file=sys.stderr,
            )

    # Run frontend tests
    if not args.backend_only:
        if args.verbose:
            print("\n[Frontend] Starting test runs...", file=sys.stderr)
        frontend_records = run_frontend_tests(
            times=args.times,
            verbose=args.verbose,
        )
        all_records.update(frontend_records)
        if args.verbose:
            print(
                f"[Frontend] Collected {len(frontend_records)} unique tests",
                file=sys.stderr,
            )

    # Build report
    report = FlakinessReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version=__version__,
        total_runs=args.times,
        records=list(all_records.values()),
        metadata={
            "commit_sha": commit_sha,
            "run_fingerprint": _generate_run_fingerprint(),
            "cli_args": " ".join(sys.argv[1:]),
        },
    )

    # Markdown output
    if args.output:
        md_content = generate_markdown_report(report)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md_content)
        if args.verbose:
            print(f"\nMarkdown report written to: {output_path}", file=sys.stderr)

    # JSON output
    if args.json:
        json_content = generate_json_report(report)
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(json_content, indent=2))
        if args.verbose:
            print(f"JSON report written to: {json_path}", file=sys.stderr)
        if getattr(args, "candidate_evidence", None):
            from scripts.ci.emit_flaky_candidates import emit_candidates

            evidence_path = Path(args.candidate_evidence)
            emit_candidates(json_content, REPO_ROOT / "config/ci/test_skip_register.yaml", evidence_path)
            if args.verbose:
                print(f"Candidate evidence written to: {evidence_path}", file=sys.stderr)

    # Console summary
    print("\n" + "=" * 60)
    print("FLAKINESS TRACKER SUMMARY")
    print("=" * 60)
    print(f"Total unique tests : {report.total_tests}")
    print(f"Flaky tests        : {len(report.flaky_tests)}")
    print(f"Critical (< 95%)   : {len(report.critical_tests)}")
    print(f"Warning (95-99%)   : {len(report.warning_tests)}")
    print(f"Overall pass rate  : {report.overall_pass_rate:.1f}%")
    print("=" * 60)

    if report.flaky_tests:
        print("\nFlaky tests detected:")
        for rec in sorted(report.flaky_tests, key=lambda r: r.pass_rate):
            print(f"  {rec.severity_badge} {rec.test_id.nodeid} — {rec.pass_rate:.0f}% pass rate")

    # Exit code
    if args.fail_on_flaky and report.flaky_tests:
        print("\n❌ FAIL: Flaky tests detected (exit 1)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
