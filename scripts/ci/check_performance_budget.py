#!/usr/bin/env python3
"""
Fabric_4L Performance Budget Enforcer v1.2.0

Audits a web build against the performance budget defined in
apps/web/performance-budget.json using Lighthouse CI or a local
Lighthouse installation.

Fails CI if any budget threshold is exceeded.

Usage:
    # Via Lighthouse CI (recommended for CI)
    python check_performance_budget.py --budget apps/web/performance-budget.json

    # With a pre-generated Lighthouse report
    python check_performance_budget.py --lighthouse-report report.json --budget apps/web/performance-budget.json

    # Generate report and check
    python check_performance_budget.py --url http://localhost:3000 --budget apps/web/performance-budget.json

    # Output markdown report
    python check_performance_budget.py --url http://localhost:3000 --output report.md --json report.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

__version__ = "1.2.0"

# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class ResourceBudget:
    resource_type: str
    budget: float
    unit: str = "kilobyte"
    description: str = ""


@dataclasses.dataclass
class TimingBudget:
    metric: str
    budget: float
    unit: str = "millisecond"
    description: str = ""


@dataclasses.dataclass
class BudgetConfig:
    version: str
    budgets: List[ResourceBudget]
    timings: List[TimingBudget]
    thresholds: Dict[str, Any]


@dataclasses.dataclass
class BudgetResult:
    name: str
    budget: float
    actual: float
    unit: str
    status: str  # "pass" | "warning" | "fail"
    detail: str = ""

    @property
    def diff_percent(self) -> float:
        if self.budget == 0:
            return 0.0
        return ((self.actual - self.budget) / self.budget) * 100.0

    @property
    def status_icon(self) -> str:
        return {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(self.status, "❓")


@dataclasses.dataclass
class PerformanceReport:
    generated_at: str
    version: str
    url: str
    results: List[BudgetResult]
    metadata: Dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == "warning")

    @property
    def failures(self) -> int:
        return sum(1 for r in self.results if r.status == "fail")

    @property
    def overall_status(self) -> str:
        if self.failures > 0:
            return "fail"
        if self.warnings > 0:
            return "warning"
        return "pass"


# ──────────────────────────────────────────────────────────────────────────────
# Lighthouse result parsing
# ──────────────────────────────────────────────────────────────────────────────

# Map Lighthouse audit IDs to our budget metric names
LIGHTHOUSE_METRIC_MAP = {
    "first-contentful-paint": "first-contentful-paint",
    "largest-contentful-paint": "largest-contentful-paint",
    "interactive": "time-to-interactive",
    "total-blocking-time": "total-blocking-time",
    "cumulative-layout-shift": "cumulative-layout-shift",
    "speed-index": "speed-index",
    "first-meaningful-paint": "first-meaningful-paint",
}


def parse_lighthouse_report(report_path: Path) -> Dict[str, float]:
    """Extract performance metrics from a Lighthouse JSON report."""
    data = json.loads(report_path.read_text())
    metrics: Dict[str, float] = {}

    audits = data.get("audits", {})
    for audit_id, budget_key in LIGHTHOUSE_METRIC_MAP.items():
        audit = audits.get(audit_id)
        if audit and "numericValue" in audit:
            # Lighthouse reports timing in ms; CLS is unitless
            metrics[budget_key] = float(audit["numericValue"])

    # Resource summary from "network-requests" or "resource-summary" audit
    resource_summary = audits.get("resource-summary", {})
    details = resource_summary.get("details", {})
    if details:
        items = details.get("items", [])
        for item in items:
            rt = item.get("resourceType", "").lower()
            transfer_size = item.get("transferSize", 0) / 1024.0  # bytes -> KB
            metrics[f"resource:{rt}"] = transfer_size

    # Also try to get from network-requests audit
    network_audits = audits.get("network-requests", {})
    network_details = network_audits.get("details", {})
    if network_details and not metrics:
        # Aggregate by resource type manually
        items = network_details.get("items", [])
        type_totals: Dict[str, float] = {}
        for item in items:
            rt = item.get("resourceType", "Other")
            size = item.get("transferSize", 0) / 1024.0
            type_totals[rt] = type_totals.get(rt, 0) + size
        for rt, size in type_totals.items():
            metrics[f"resource:{rt.lower()}"] = size

    # Calculate total page weight
    if any(k.startswith("resource:") for k in metrics):
        total = sum(v for k, v in metrics.items() if k.startswith("resource:"))
        metrics["resource:total"] = total

    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Budget loading
# ──────────────────────────────────────────────────────────────────────────────


def load_budget_config(path: Path) -> BudgetConfig:
    """Load and validate the performance budget configuration."""
    data = json.loads(path.read_text())

    budgets = [
        ResourceBudget(
            resource_type=b["resourceType"],
            budget=float(b["budget"]),
            unit=b.get("unit", "kilobyte"),
            description=b.get("description", ""),
        )
        for b in data.get("budgets", [])
    ]

    timings = [
        TimingBudget(
            metric=t["metric"],
            budget=float(t["budget"]),
            unit=t.get("unit", "millisecond"),
            description=t.get("description", ""),
        )
        for t in data.get("timings", [])
    ]

    return BudgetConfig(
        version=data.get("version", "unknown"),
        budgets=budgets,
        timings=timings,
        thresholds=data.get("thresholds", {}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Budget checking logic
# ──────────────────────────────────────────────────────────────────────────────


def check_resource_budgets(
    config: BudgetConfig,
    actual_metrics: Dict[str, float],
) -> List[BudgetResult]:
    """Compare actual resource sizes against budgets."""
    results: List[BudgetResult] = []
    warning_threshold = config.thresholds.get("warning", 0.9)

    resource_lookup: Dict[str, float] = {}
    for key, value in actual_metrics.items():
        if key.startswith("resource:"):
            rt = key.replace("resource:", "")
            resource_lookup[rt] = value

    for budget in config.budgets:
        actual = resource_lookup.get(budget.resource_type, 0.0)

        # Determine status
        ratio = actual / budget.budget if budget.budget > 0 else 0.0
        if ratio > 1.0:
            status = "fail"
        elif ratio > warning_threshold:
            status = "warning"
        else:
            status = "pass"

        detail = f"{actual:.1f} / {budget.budget} {budget.unit} ({ratio*100:.0f}%)"

        results.append(
            BudgetResult(
                name=f"resource:{budget.resource_type}",
                budget=budget.budget,
                actual=actual,
                unit=budget.unit,
                status=status,
                detail=detail,
            )
        )

    return results


def check_timing_budgets(
    config: BudgetConfig,
    actual_metrics: Dict[str, float],
) -> List[BudgetResult]:
    """Compare actual timing metrics against budgets."""
    results: List[BudgetResult] = []
    warning_threshold = config.thresholds.get("warning", 0.9)

    for timing in config.timings:
        actual = actual_metrics.get(timing.metric, 0.0)

        ratio = actual / timing.budget if timing.budget > 0 else 0.0
        if ratio > 1.0:
            status = "fail"
        elif ratio > warning_threshold:
            status = "warning"
        else:
            status = "pass"

        unit_label = timing.unit if timing.unit != "unitless" else ""
        detail = f"{actual:.1f} / {timing.budget} {unit_label} ({ratio*100:.0f}%)"

        results.append(
            BudgetResult(
                name=timing.metric,
                budget=timing.budget,
                actual=actual,
                unit=timing.unit,
                status=status,
                detail=detail,
            )
        )

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Lighthouse execution
# ──────────────────────────────────────────────────────────────────────────────


def run_lighthouse(
    url: str,
    output_path: Path,
    device: str = "desktop",
    timeout: int = 60,
) -> Path:
    """Run Lighthouse and return the path to the JSON report."""
    cmd = [
        "npx",
        "lighthouse",
        url,
        f"--preset={device}",
        "--output=json",
        f"--output-path={output_path}",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
        "--only-categories=performance",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode not in (0, 1):  # LH returns 1 for score below 90
        print(f"Lighthouse stderr: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"Lighthouse failed with code {result.returncode}")

    return output_path


def run_lighthouse_ci(
    budget_path: Path,
    url: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, float]:
    """Run via @lhci/cli for CI integration."""
    cmd = ["npx", "lhci", "collect"]
    if url:
        cmd.extend(["--url", url])
    if config_path:
        cmd.extend(["--config", str(config_path)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # lhci collect stores reports in .lighthouseci/
    lhci_dir = Path(".lighthouseci")
    json_reports = sorted(lhci_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_reports:
        raise RuntimeError("No Lighthouse reports found after lhci collect")

    return parse_lighthouse_report(json_reports[0])


# ──────────────────────────────────────────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────────────────────────────────────────


def generate_markdown_report(report: PerformanceReport) -> str:
    """Generate a Markdown report of the budget check."""
    status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}[report.overall_status]

    lines = [
        "# Fabric_4L Performance Budget Report",
        "",
        f"**URL:** {report.url}  ",
        f"**Generated:** {report.generated_at}  ",
        f"**Overall Status:** {status_icon} {report.overall_status.upper()}  ",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Passed  | {report.passed} |",
        f"| Warnings | {report.warnings} |",
        f"| Failures | {report.failures} |",
        f"| Total Checks | {len(report.results)} |",
        "",
        "---",
        "",
        "## Resource Budgets",
        "",
        "| Resource | Budget | Actual | Status | Detail |",
        "|----------|--------|--------|--------|--------|",
    ]

    for r in sorted(report.results, key=lambda x: (x.status != "fail", x.status != "warning", x.name)):
        if r.name.startswith("resource:"):
            lines.append(
                f"| {r.name} | {r.budget} {r.unit} | {r.actual:.1f} {r.unit} | "
                f"{r.status_icon} {r.status.upper()} | {r.detail} |"
            )

    lines.extend([
        "",
        "## Timing Budgets",
        "",
        "| Metric | Budget | Actual | Status | Detail |",
        "|--------|--------|--------|--------|--------|",
    ])

    for r in sorted(report.results, key=lambda x: (x.status != "fail", x.status != "warning", x.name)):
        if not r.name.startswith("resource:"):
            lines.append(
                f"| {r.name} | {r.budget} {r.unit} | {r.actual:.1f} {r.unit} | "
                f"{r.status_icon} {r.status.upper()} | {r.detail} |"
            )

    if report.failures > 0:
        lines.extend([
            "",
            "---",
            "",
            "## ❌ Failures Detail",
            "",
            "The following budgets were exceeded:",
            "",
        ])
        for r in report.results:
            if r.status == "fail":
                lines.append(f"- **{r.name}**: {r.detail} (+{r.diff_percent:.1f}% over budget)")

    lines.extend([
        "",
        "---",
        "",
        f"*Report generated by Fabric_4L Performance Budget Enforcer v{__version__}*",
    ])

    return "\n".join(lines)


def generate_json_report(report: PerformanceReport) -> Dict[str, Any]:
    """Generate a JSON-serializable report."""
    return {
        "version": __version__,
        "generated_at": report.generated_at,
        "url": report.url,
        "metadata": report.metadata,
        "summary": {
            "status": report.overall_status,
            "total": len(report.results),
            "passed": report.passed,
            "warnings": report.warnings,
            "failures": report.failures,
        },
        "results": [
            {
                "name": r.name,
                "budget": r.budget,
                "actual": round(r.actual, 2),
                "unit": r.unit,
                "status": r.status,
                "diff_percent": round(r.diff_percent, 2),
                "detail": r.detail,
            }
            for r in report.results
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_performance_budget",
        description="Fabric_4L Performance Budget Enforcer",
    )
    parser.add_argument(
        "--budget", "-b",
        type=Path,
        default=Path("apps/web/performance-budget.json"),
        help="Path to performance-budget.json",
    )
    parser.add_argument(
        "--lighthouse-report",
        type=Path,
        default=None,
        help="Path to a pre-generated Lighthouse JSON report",
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default="",
        help="URL to audit (runs Lighthouse if --lighthouse-report not given)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="Write Markdown report to this path",
    )
    parser.add_argument(
        "--json", "-j",
        type=str,
        default="",
        help="Write JSON report to this path",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="desktop",
        choices=["desktop", "mobile"],
        help="Lighthouse device preset",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Treat warnings as failures",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    # Load budget config
    if not args.budget.exists():
        print(f"error: Budget file not found: {args.budget}", file=sys.stderr)
        return 2

    config = load_budget_config(args.budget)

    if args.verbose:
        print(f"Loaded budget config v{config.version}", file=sys.stderr)
        print(f"  Resources: {len(config.budgets)}", file=sys.stderr)
        print(f"  Timings:   {len(config.timings)}", file=sys.stderr)

    # Get actual metrics
    if args.lighthouse_report:
        if args.verbose:
            print(f"Parsing Lighthouse report: {args.lighthouse_report}", file=sys.stderr)
        actual_metrics = parse_lighthouse_report(args.lighthouse_report)
        url = f"file://{args.lighthouse_report}"
    elif args.url:
        if args.verbose:
            print(f"Running Lighthouse against: {args.url}", file=sys.stderr)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            run_lighthouse(args.url, tmp_path, device=args.device)
            actual_metrics = parse_lighthouse_report(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        url = args.url
    else:
        print("error: Must provide --lighthouse-report or --url", file=sys.stderr)
        return 2

    if not actual_metrics:
        print("error: No metrics extracted from Lighthouse report", file=sys.stderr)
        return 2

    if args.verbose:
        print(f"Extracted {len(actual_metrics)} metrics", file=sys.stderr)

    # Check budgets
    resource_results = check_resource_budgets(config, actual_metrics)
    timing_results = check_timing_budgets(config, actual_metrics)

    report = PerformanceReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version=__version__,
        url=url,
        results=resource_results + timing_results,
        metadata={
            "budget_version": config.version,
            "device": args.device,
        },
    )

    # Output markdown
    if args.output:
        md = generate_markdown_report(report)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md)
        if args.verbose:
            print(f"Markdown report: {out_path}", file=sys.stderr)

    # Output JSON
    if args.json:
        json_data = generate_json_report(report)
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(json_data, indent=2))
        if args.verbose:
            print(f"JSON report: {json_path}", file=sys.stderr)

    # Console output
    print("\n" + "=" * 60)
    print("PERFORMANCE BUDGET CHECK")
    print("=" * 60)
    print(f"URL:   {url}")
    print(f"Total: {len(report.results)} checks")
    print(f"  ✅ Passed:   {report.passed}")
    print(f"  ⚠️  Warnings: {report.warnings}")
    print(f"  ❌ Failures: {report.failures}")
    print("=" * 60)

    for r in report.results:
        icon = r.status_icon
        print(f"  {icon} {r.name:40s} {r.detail}")

    # Exit code
    if report.failures > 0:
        print("\n❌ FAIL: Budget exceeded for one or more metrics")
        return 1
    if args.fail_on_warning and report.warnings > 0:
        print("\n⚠️ FAIL: Warnings treated as failures (--fail-on-warning)")
        return 1
    print("\n✅ PASS: All metrics within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
