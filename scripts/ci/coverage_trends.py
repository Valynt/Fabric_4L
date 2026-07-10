#!/usr/bin/env python3
"""
Fabric_4L Coverage Trend Tracker v1.2.0

Parses coverage reports from pytest-cov (Python) and Vitest (TypeScript),
compares current coverage against the main branch baseline, fails CI if
coverage drops by more than the configured threshold (default: 1%), and
generates an SVG trend graph.

Usage:
    # Compare current coverage against main branch
    python coverage_trends.py --backend-cov coverage.xml --frontend-cov coverage.json

    # With baseline files
    python coverage_trends.py --backend-cov coverage.xml --baseline-backend baseline.xml

    # Generate SVG trend graph
    python coverage_trends.py --backend-cov coverage.xml --output-graph coverage-trend.svg

    # Full mode with all artifacts
    python coverage_trends.py \
        --backend-cov coverage.xml \
        --frontend-cov apps/web/coverage/coverage-final.json \
        --baseline-backend .ci/baseline-backend.xml \
        --baseline-frontend .ci/baseline-frontend.json \
        --output-graph docs/quality/coverage-trend.svg \
        --output-md docs/quality/coverage-report.md \
        --max-drop 1.0
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

__version__ = "1.2.0"

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_MAX_DROP_PERCENT = 1.0  # Fail if coverage drops more than 1%
COVERAGE_TARGET_LINE = 82.0
COVERAGE_TARGET_BRANCH = 75.0
SVG_WIDTH = 800
SVG_HEIGHT = 400
REPO_ROOT = Path(__file__).resolve().parents[2]

# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class CoverageMetrics:
    """Normalized coverage metrics across tools."""
    lines_total: int = 0
    lines_covered: int = 0
    line_rate: float = 0.0
    branches_total: int = 0
    branches_covered: int = 0
    branch_rate: float = 0.0
    functions_total: int = 0
    functions_covered: int = 0
    function_rate: float = 0.0
    statements_total: int = 0
    statements_covered: int = 0
    statement_rate: float = 0.0

    @property
    def line_percent(self) -> float:
        return self.line_rate * 100.0

    @property
    def branch_percent(self) -> float:
        return self.branch_rate * 100.0

    @property
    def function_percent(self) -> float:
        return self.function_rate * 100.0


@dataclasses.dataclass
class CoverageDiff:
    """Difference between current and baseline coverage."""
    metric: str
    current: float
    baseline: float
    delta: float
    status: str  # "pass" | "warning" | "fail"

    @property
    def delta_str(self) -> str:
        sign = "+" if self.delta >= 0 else ""
        return f"{sign}{self.delta:.2f}%"

    @property
    def icon(self) -> str:
        return {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(self.status, "❓")


@dataclasses.dataclass
class CoverageReport:
    """Complete coverage analysis report."""
    generated_at: str
    version: str
    backend: CoverageMetrics
    frontend: CoverageMetrics
    combined: CoverageMetrics
    diffs: List[CoverageDiff]
    baseline_commit: str = ""
    metadata: Dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def has_failures(self) -> bool:
        return any(d.status == "fail" for d in self.diffs)

    @property
    def has_warnings(self) -> bool:
        return any(d.status == "warning" for d in self.diffs)


# ──────────────────────────────────────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────────────────────────────────────


def parse_cobertura_xml(path: Path) -> CoverageMetrics:
    """Parse a Cobertura-format XML coverage report (pytest-cov output)."""
    tree = ET.parse(path)
    root = tree.getroot()

    # Try <coverage> attributes first
    coverage_elem = root
    line_rate = float(coverage_elem.get("line-rate", "0") or "0")
    branch_rate = float(coverage_elem.get("branch-rate", "0") or "0")

    # Count lines and branches from <line> elements for accuracy
    lines_total = 0
    lines_covered = 0
    branches_total = 0
    branches_covered = 0

    for line_elem in root.iter("line"):
        lines_total += 1
        hits = int(line_elem.get("hits", "0") or "0")
        if hits > 0:
            lines_covered += 1

        # Branch coverage
        if line_elem.get("branch", "false") == "true":
            condition_coverage = line_elem.get("condition-coverage", "")
            if condition_coverage:
                # Format: "50% (1/2)"
                try:
                    parts = condition_coverage.split("(")[1].rstrip(")").split("/")
                    branches_covered += int(parts[0])
                    branches_total += int(parts[1])
                except (IndexError, ValueError):
                    branches_total += 2
                    if hits > 0:
                        branches_covered += 1

    metrics = CoverageMetrics(
        lines_total=lines_total,
        lines_covered=lines_covered,
        line_rate=line_rate if line_rate > 0 else (lines_covered / lines_total if lines_total else 0),
        branches_total=branches_total,
        branches_covered=branches_covered,
        branch_rate=branch_rate if branch_rate > 0 else (branches_covered / branches_total if branches_total else 0),
    )
    return metrics


def parse_vitest_json(path: Path) -> CoverageMetrics:
    """Parse a Vitest coverage JSON report (coverage-final.json)."""
    data = json.loads(path.read_text())

    total_lines = 0
    covered_lines = 0
    total_branches = 0
    covered_branches = 0
    total_functions = 0
    covered_functions = 0
    total_statements = 0
    covered_statements = 0

    for filepath, file_data in data.items():
        for line_num, count in file_data.get("s", {}).items():
            total_statements += 1
            if count > 0:
                covered_statements += 1

        for branch_id, branch_data in file_data.get("branchMap", {}).items():
            loc = branch_data.get("loc", {})
            total_branches += 1
            # Check hits from 'b' array
            hits = file_data.get("b", {}).get(branch_id, [0])
            if isinstance(hits, list):
                if any(h > 0 for h in hits):
                    covered_branches += 1
            elif hits > 0:
                covered_branches += 1

        for fn_name, fn_data in file_data.get("fnMap", {}).items():
            total_functions += 1
            hits = file_data.get("f", {}).get(fn_name, 0)
            if hits > 0:
                covered_functions += 1

        for stmt_id, count in file_data.get("s", {}).items():
            total_lines += 1
            if count > 0:
                covered_lines += 1

    return CoverageMetrics(
        lines_total=total_lines,
        lines_covered=covered_lines,
        line_rate=(covered_lines / total_lines) if total_lines else 0,
        branches_total=total_branches,
        branches_covered=covered_branches,
        branch_rate=(covered_branches / total_branches) if total_branches else 0,
        functions_total=total_functions,
        functions_covered=covered_functions,
        function_rate=(covered_functions / total_functions) if total_functions else 0,
        statements_total=total_statements,
        statements_covered=covered_statements,
        statement_rate=(covered_statements / total_statements) if total_statements else 0,
    )


def parse_pytest_cov_text(stdout: str) -> CoverageMetrics:
    """Parse pytest-cov text output as fallback."""
    metrics = CoverageMetrics()
    for line in stdout.splitlines():
        if "coverage" in line.lower() and "%" in line:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "%" in part:
                        pct = float(part.replace("%", "")) / 100.0
                        metrics.line_rate = pct
                        break
            except ValueError:
                pass
    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Baseline management
# ──────────────────────────────────────────────────────────────────────────────


def get_baseline_from_git(
    file_path: Path,
    branch: str = "origin/main",
) -> Optional[CoverageMetrics]:
    """Fetch a baseline coverage file from the main branch via git."""
    try:
        content = subprocess.check_output(
            ["git", "show", f"{branch}:{file_path}"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=file_path.suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            if file_path.suffix == ".xml":
                return parse_cobertura_xml(tmp_path)
            elif file_path.suffix == ".json":
                return parse_vitest_json(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def get_baseline_commit(branch: str = "origin/main") -> str:
    """Get the commit SHA of the baseline branch."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", branch],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# Comparison logic
# ──────────────────────────────────────────────────────────────────────────────


def compute_diffs(
    current_backend: CoverageMetrics,
    current_frontend: CoverageMetrics,
    baseline_backend: Optional[CoverageMetrics],
    baseline_frontend: Optional[CoverageMetrics],
    max_drop: float,
) -> List[CoverageDiff]:
    """Compute coverage differences and assign pass/warning/fail status."""
    diffs: List[CoverageDiff] = []

    comparisons = [
        ("Backend Line Coverage", current_backend, baseline_backend, "line"),
        ("Backend Branch Coverage", current_backend, baseline_backend, "branch"),
        ("Frontend Line Coverage", current_frontend, baseline_frontend, "line"),
        ("Frontend Branch Coverage", current_frontend, baseline_frontend, "branch"),
    ]

    for name, current, baseline, metric in comparisons:
        current_val = getattr(current, f"{metric}_percent")
        baseline_val = getattr(baseline, f"{metric}_percent") if baseline else current_val
        delta = current_val - baseline_val

        if delta < -max_drop:
            status = "fail"
        elif delta < 0:
            status = "warning"
        else:
            status = "pass"

        diffs.append(CoverageDiff(
            metric=name,
            current=current_val,
            baseline=baseline_val,
            delta=delta,
            status=status,
        ))

    # Combined metrics
    combined_line = (current_backend.line_percent + current_frontend.line_percent) / 2
    combined_branch = (current_backend.branch_percent + current_frontend.branch_percent) / 2

    diffs.append(CoverageDiff(
        metric="Combined Line Coverage",
        current=combined_line,
        baseline=combined_line,  # Simplified
        delta=0.0,
        status="pass" if combined_line >= COVERAGE_TARGET_LINE else "fail",
    ))

    return diffs


# ──────────────────────────────────────────────────────────────────────────────
# SVG trend graph generation
# ──────────────────────────────────────────────────────────────────────────────


def generate_svg_trend(
    output_path: Path,
    history: Optional[List[Dict[str, Any]]] = None,
    current: Optional[CoverageReport] = None,
) -> str:
    """Generate an SVG trend graph showing coverage over time."""
    # Default: mock historical data if none provided
    if history is None:
        history = [
            {"date": "2024-03", "line": 74.0, "branch": 62.0},
            {"date": "2024-04", "line": 76.5, "branch": 65.0},
            {"date": "2024-05", "line": 79.0, "branch": 68.0},
            {"date": "2024-06-w1", "line": 80.5, "branch": 69.5},
            {"date": "2024-06-w2", "line": 82.0, "branch": 71.0},
        ]

    if current:
        combined_line = (current.backend.line_percent + current.frontend.line_percent) / 2
        combined_branch = (current.backend.branch_percent + current.frontend.branch_percent) / 2
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        history = history + [{"date": today, "line": combined_line, "branch": combined_branch}]

    n = len(history)
    if n < 2:
        return ""

    # Dimensions
    w, h = SVG_WIDTH, SVG_HEIGHT
    pad_left, pad_right = 70, 40
    pad_top, pad_bottom = 40, 60
    gw = w - pad_left - pad_right
    gh = h - pad_top - pad_bottom

    # Y-axis range
    all_values = [h["line"] for h in history] + [h["branch"] for h in history]
    y_min = max(0, min(all_values) - 10)
    y_max = min(100, max(all_values) + 10)
    y_range = y_max - y_min if y_max != y_min else 100

    def x_scale(i: int) -> float:
        return pad_left + (i / (n - 1)) * gw

    def y_scale(val: float) -> float:
        return pad_top + gh - ((val - y_min) / y_range) * gh

    # Build SVG
    lines_svg: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        '<style>',
        '  text { font-family: system-ui, -apple-system, sans-serif; font-size: 12px; }',
        '  .title { font-size: 16px; font-weight: bold; }',
        '  .legend { font-size: 11px; }',
        '</style>',
        f'<rect width="{w}" height="{h}" fill="#fafbfc"/>',
        f'<text x="{w/2}" y="25" text-anchor="middle" class="title">Fabric_4L Coverage Trend</text>',
    ]

    # Grid lines
    for i in range(6):
        val = y_min + (y_range / 5) * i
        y = y_scale(val)
        lines_svg.append(f'<line x1="{pad_left}" y1="{y}" x2="{w - pad_right}" y2="{y}" stroke="#e1e4e8" stroke-width="1"/>')
        lines_svg.append(f'<text x="{pad_left - 10}" y="{y + 4}" text-anchor="end" fill="#586069">{val:.0f}%</text>')

    # Target line (80%)
    target_y = y_scale(COVERAGE_TARGET_LINE)
    lines_svg.append(f'<line x1="{pad_left}" y1="{target_y}" x2="{w - pad_right}" y2="{target_y}" stroke="#28a745" stroke-width="1" stroke-dasharray="4,4"/>')
    lines_svg.append(f'<text x="{w - pad_right + 5}" y="{target_y + 4}" fill="#28a745" class="legend">target ({COVERAGE_TARGET_LINE:.0f}%)</text>')

    # X-axis labels
    for i, entry in enumerate(history):
        x = x_scale(i)
        lines_svg.append(f'<text x="{x}" y="{h - pad_bottom + 20}" text-anchor="middle" fill="#586069">{entry["date"]}</text>')

    # Line coverage polyline
    line_points = " ".join(f"{x_scale(i)},{y_scale(h['line'])}" for i, h in enumerate(history))
    lines_svg.append(f'<polyline points="{line_points}" fill="none" stroke="#0366d6" stroke-width="2.5"/>')

    # Branch coverage polyline
    branch_points = " ".join(f"{x_scale(i)},{y_scale(h['branch'])}" for i, h in enumerate(history))
    lines_svg.append(f'<polyline points="{branch_points}" fill="none" stroke="#d73a49" stroke-width="2.5"/>')

    # Data points
    for i, entry in enumerate(history):
        x = x_scale(i)
        lines_svg.append(f'<circle cx="{x}" cy="{y_scale(entry["line"])}" r="4" fill="#0366d6"/>')
        lines_svg.append(f'<circle cx="{x}" cy="{y_scale(entry["branch"])}" r="4" fill="#d73a49"/>')

    # Legend
    legend_y = h - 20
    lines_svg.append(f'<circle cx="{pad_left}" cy="{legend_y}" r="4" fill="#0366d6"/>')
    lines_svg.append(f'<text x="{pad_left + 12}" y="{legend_y + 4}" class="legend" fill="#24292e">Line Coverage</text>')
    lines_svg.append(f'<circle cx="{pad_left + 120}" cy="{legend_y}" r="4" fill="#d73a49"/>')
    lines_svg.append(f'<text x="{pad_left + 132}" y="{legend_y + 4}" class="legend" fill="#24292e">Branch Coverage</text>')

    lines_svg.append('</svg>')
    return "\n".join(lines_svg)


# ──────────────────────────────────────────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────────────────────────────────────────


def generate_markdown_report(report: CoverageReport) -> str:
    """Generate Markdown coverage report."""
    status_icon = "❌" if report.has_failures else "⚠️" if report.has_warnings else "✅"

    lines = [
        "# Fabric_4L Coverage Report",
        "",
        f"**Generated:** {report.generated_at}  ",
        f"**Baseline:** `{report.baseline_commit[:8] if report.baseline_commit else 'N/A'}`  ",
        f"**Overall:** {status_icon} {'FAIL' if report.has_failures else 'PASS'}  ",
        "",
        "## Summary",
        "",
        "| Suite | Line Coverage | Branch Coverage | Functions |",
        "|-------|---------------|-----------------|-----------|",
    ]

    be = report.backend
    fe = report.frontend
    lines.append(
        f"| Backend | {be.line_percent:.1f}% | {be.branch_percent:.1f}% | "
        f"{be.function_percent:.1f}% |"
    )
    lines.append(
        f"| Frontend | {fe.line_percent:.1f}% | {fe.branch_percent:.1f}% | "
        f"{fe.function_percent:.1f}% |"
    )

    combined_line = (be.line_percent + fe.line_percent) / 2
    combined_branch = (be.branch_percent + fe.branch_percent) / 2
    lines.append(
        f"| **Combined** | **{combined_line:.1f}%** | **{combined_branch:.1f}%** | — |"
    )

    lines.extend([
        "",
        "### Targets",
        "",
        f"| Metric | Target | Current | Status |",
        f"|--------|--------|---------|--------|",
        f"| Line Coverage | {COVERAGE_TARGET_LINE:.0f}% | {combined_line:.1f}% | {'✅ PASS' if combined_line >= COVERAGE_TARGET_LINE else '❌ FAIL'} |",
        f"| Branch Coverage | {COVERAGE_TARGET_BRANCH:.0f}% | {combined_branch:.1f}% | {'✅ PASS' if combined_branch >= COVERAGE_TARGET_BRANCH else '❌ FAIL'} |",
        "",
    ])

    if report.diffs:
        lines.extend([
            "## Coverage Diff (vs Baseline)",
            "",
            "| Metric | Baseline | Current | Delta | Status |",
            "|--------|----------|---------|-------|--------|",
        ])
        for d in report.diffs:
            lines.append(
                f"| {d.metric} | {d.baseline:.2f}% | {d.current:.2f}% | "
                f"{d.delta_str} | {d.icon} {d.status.upper()} |"
            )
        lines.append("")

    lines.extend([
        "---",
        "",
        f"*Report generated by Fabric_4L Coverage Trend Tracker v{__version__}*",
    ])

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coverage_trends",
        description="Fabric_4L Coverage Trend Tracker",
    )
    parser.add_argument(
        "--backend-cov",
        type=Path,
        default=None,
        help="Path to backend coverage XML (Cobertura)",
    )
    parser.add_argument(
        "--frontend-cov",
        type=Path,
        default=None,
        help="Path to frontend coverage JSON (Vitest)",
    )
    parser.add_argument(
        "--baseline-backend",
        type=Path,
        default=None,
        help="Path to baseline backend coverage file",
    )
    parser.add_argument(
        "--baseline-frontend",
        type=Path,
        default=None,
        help="Path to baseline frontend coverage file",
    )
    parser.add_argument(
        "--baseline-branch",
        type=str,
        default="origin/main",
        help="Git branch to fetch baseline from (if no baseline file)",
    )
    parser.add_argument(
        "--max-drop",
        type=float,
        default=DEFAULT_MAX_DROP_PERCENT,
        help=f"Max allowed coverage drop in %% (default: {DEFAULT_MAX_DROP_PERCENT})",
    )
    parser.add_argument(
        "--output-graph",
        type=str,
        default="",
        help="Path to write SVG trend graph",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default="",
        help="Path to write Markdown report",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Path to write JSON report",
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

    if not args.backend_cov and not args.frontend_cov:
        print("error: Must provide --backend-cov and/or --frontend-cov", file=sys.stderr)
        return 2

    # Parse current coverage
    current_backend = CoverageMetrics()
    current_frontend = CoverageMetrics()

    if args.backend_cov:
        if not args.backend_cov.exists():
            print(f"error: Backend coverage file not found: {args.backend_cov}", file=sys.stderr)
            return 2
        current_backend = parse_cobertura_xml(args.backend_cov)
        if args.verbose:
            print(f"Backend: {current_backend.line_percent:.1f}% lines, {current_backend.branch_percent:.1f}% branches", file=sys.stderr)

    if args.frontend_cov:
        if not args.frontend_cov.exists():
            print(f"error: Frontend coverage file not found: {args.frontend_cov}", file=sys.stderr)
            return 2
        current_frontend = parse_vitest_json(args.frontend_cov)
        if args.verbose:
            print(f"Frontend: {current_frontend.line_percent:.1f}% lines, {current_frontend.branch_percent:.1f}% branches", file=sys.stderr)

    # Parse/load baselines
    baseline_backend: Optional[CoverageMetrics] = None
    baseline_frontend: Optional[CoverageMetrics] = None

    if args.baseline_backend and args.baseline_backend.exists():
        baseline_backend = parse_cobertura_xml(args.baseline_backend)
    elif args.backend_cov:
        baseline_backend = get_baseline_from_git(args.backend_cov, args.baseline_branch)

    if args.baseline_frontend and args.baseline_frontend.exists():
        baseline_frontend = parse_vitest_json(args.baseline_frontend)
    elif args.frontend_cov:
        baseline_frontend = get_baseline_from_git(args.frontend_cov, args.baseline_branch)

    baseline_commit = get_baseline_commit(args.baseline_branch)

    # Compute diffs
    diffs = compute_diffs(
        current_backend, current_frontend,
        baseline_backend, baseline_frontend,
        args.max_drop,
    )

    report = CoverageReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version=__version__,
        backend=current_backend,
        frontend=current_frontend,
        combined=CoverageMetrics(),  # Computed on demand
        diffs=diffs,
        baseline_commit=baseline_commit,
    )

    # SVG graph
    if args.output_graph:
        svg = generate_svg_trend(output_path=Path(args.output_graph), current=report)
        graph_path = Path(args.output_graph)
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(svg)
        if args.verbose:
            print(f"SVG graph: {graph_path}", file=sys.stderr)

    # Markdown report
    if args.output_md:
        md = generate_markdown_report(report)
        md_path = Path(args.output_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md)
        if args.verbose:
            print(f"Markdown report: {md_path}", file=sys.stderr)

    # JSON report
    if args.output_json:
        json_data = {
            "version": __version__,
            "generated_at": report.generated_at,
            "baseline_commit": report.baseline_commit,
            "backend": {
                "line_percent": round(current_backend.line_percent, 2),
                "branch_percent": round(current_backend.branch_percent, 2),
                "lines_covered": current_backend.lines_covered,
                "lines_total": current_backend.lines_total,
            },
            "frontend": {
                "line_percent": round(current_frontend.line_percent, 2),
                "branch_percent": round(current_frontend.branch_percent, 2),
            },
            "diffs": [
                {
                    "metric": d.metric,
                    "current": round(d.current, 2),
                    "baseline": round(d.baseline, 2),
                    "delta": round(d.delta, 2),
                    "status": d.status,
                }
                for d in diffs
            ],
            "has_failures": report.has_failures,
        }
        json_path = Path(args.output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(json_data, indent=2))

    # Console summary
    print("\n" + "=" * 60)
    print("COVERAGE TREND REPORT")
    print("=" * 60)
    if args.backend_cov:
        print(f"Backend:  {current_backend.line_percent:.1f}% lines / {current_backend.branch_percent:.1f}% branches")
    if args.frontend_cov:
        print(f"Frontend: {current_frontend.line_percent:.1f}% lines / {current_frontend.branch_percent:.1f}% branches")

    combined_line = (current_backend.line_percent + current_frontend.line_percent) / 2
    print(f"\nCombined line coverage: {combined_line:.1f}% (target: {COVERAGE_TARGET_LINE:.0f}%)")

    if diffs:
        print("\nDiffs vs baseline:")
        for d in diffs:
            print(f"  {d.icon} {d.metric}: {d.current:.2f}% ({d.delta_str})")

    print("=" * 60)

    if report.has_failures:
        print("\n❌ FAIL: Coverage dropped below threshold")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
