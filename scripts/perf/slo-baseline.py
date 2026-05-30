#!/usr/bin/env python3
"""Run and evaluate the critical-path k6 performance baseline.

The script is CI-friendly: it can either execute k6 or consume an existing k6
summary JSON, writes dashboard-ready artifacts under artifacts/performance, and
fails when the current run regresses 10% or more from the stored baseline.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("artifacts/performance")
DEFAULT_TEST_SCRIPT = Path("scripts/perf/load-test-critical-paths.js")
DEFAULT_REGRESSION_THRESHOLD = 0.10


@dataclass(frozen=True)
class PerformanceMetrics:
    http_req_duration_p95_ms: float
    http_req_failed_rate: float
    checks_rate: float | None = None
    iterations_count: int | None = None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "http_req_duration_p95_ms": self.http_req_duration_p95_ms,
            "http_req_failed_rate": self.http_req_failed_rate,
            "checks_rate": self.checks_rate,
            "iterations_count": self.iterations_count,
        }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metric_values(summary: dict[str, Any], metric_name: str) -> dict[str, Any]:
    try:
        values = summary["metrics"][metric_name]["values"]
    except KeyError as exc:
        raise KeyError(f"k6 summary is missing metric '{metric_name}' values") from exc
    if not isinstance(values, dict):
        raise TypeError(f"k6 summary metric '{metric_name}' values must be an object")
    return values


def count_value(summary: dict[str, Any], metric_name: str) -> int | None:
    metric = summary.get("metrics", {}).get(metric_name, {})
    value = metric.get("count") or metric.get("values", {}).get("count")
    return int(value) if value is not None else None


def extract_metrics(summary: dict[str, Any]) -> PerformanceMetrics:
    duration_values = metric_values(summary, "http_req_duration")
    failed_values = metric_values(summary, "http_req_failed")
    checks_values = summary.get("metrics", {}).get("checks", {}).get("values", {})

    return PerformanceMetrics(
        http_req_duration_p95_ms=float(duration_values["p(95)"]),
        http_req_failed_rate=float(failed_values["rate"]),
        checks_rate=float(checks_values["rate"]) if "rate" in checks_values else None,
        iterations_count=count_value(summary, "iterations"),
    )


def regression_limit(baseline_value: float, threshold: float) -> float:
    if baseline_value == 0:
        return 0.0
    return baseline_value * (1.0 + threshold)


def detect_regressions(
    current: PerformanceMetrics,
    baseline: PerformanceMetrics,
    threshold: float,
) -> list[dict[str, Any]]:
    regressions: list[dict[str, Any]] = []
    for metric_name in ("http_req_duration_p95_ms", "http_req_failed_rate"):
        current_value = float(getattr(current, metric_name))
        baseline_value = float(getattr(baseline, metric_name))
        limit = regression_limit(baseline_value, threshold)
        if current_value > limit:
            if baseline_value == 0:
                delta_percent = None
            else:
                delta_percent = ((current_value - baseline_value) / baseline_value) * 100.0
            regressions.append(
                {
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "allowed": limit,
                    "threshold_percent": threshold * 100.0,
                    "delta_percent": delta_percent,
                    "status": "regressed",
                }
            )
    return regressions


def run_k6(args: argparse.Namespace, summary_path: Path) -> None:
    k6_path = shutil.which(args.k6_binary)
    if not k6_path:
        raise RuntimeError(f"k6 binary '{args.k6_binary}' was not found on PATH")

    env_args = [
        "--summary-export",
        str(summary_path),
        "--env",
        f"BASE_URL={args.base_url}",
        "--env",
        f"K6_SUMMARY_PATH={summary_path}",
    ]
    if args.test_token:
        env_args.extend(["--env", f"TEST_TOKEN={args.test_token}"])
    if args.test_tenant_id:
        env_args.extend(["--env", f"TEST_TENANT_ID={args.test_tenant_id}"])

    command = [k6_path, "run", *env_args, str(args.test_script)]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)  # noqa: S603
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"k6 failed with exit code {completed.returncode}")


def build_baseline_payload(generated_at: str, metrics: PerformanceMetrics, source: str) -> dict[str, Any]:
    return {
        "version": 1,
        "generated_at": generated_at,
        "source": source,
        "metrics": metrics.as_dict(),
    }


def build_report(
    *,
    generated_at: str,
    current: PerformanceMetrics,
    baseline: PerformanceMetrics,
    baseline_path: Path,
    current_summary_path: Path,
    regressions: list[dict[str, Any]],
    baseline_created: bool,
    threshold: float,
) -> dict[str, Any]:
    status = "baseline_created" if baseline_created else "pass"
    if regressions:
        status = "regression"

    alerts = [
        {
            "severity": "critical",
            "message": (
                f"{item['metric']} regressed from {item['baseline']} to {item['current']} "
                f"(allowed <= {item['allowed']})"
            ),
            "metric": item["metric"],
        }
        for item in regressions
    ]

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": status,
        "all_passed": not regressions,
        "regression_threshold_percent": threshold * 100.0,
        "baseline_created": baseline_created,
        "baseline_path": str(baseline_path),
        "current_summary_path": str(current_summary_path),
        "metrics": current.as_dict(),
        "baseline": baseline.as_dict(),
        "regressions": regressions,
        "alerts": alerts,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run k6 and detect critical-path SLO baseline regressions")
    parser.add_argument("--summary", type=Path, help="Use an existing k6 summary JSON instead of running k6")
    parser.add_argument("--test-script", type=Path, default=DEFAULT_TEST_SCRIPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline", type=Path, help="Baseline JSON path (default: <output-dir>/baseline.json)")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--test-token", default=None)
    parser.add_argument("--test-tenant-id", default=None)
    parser.add_argument("--k6-binary", default="k6")
    parser.add_argument("--regression-threshold", type=float, default=DEFAULT_REGRESSION_THRESHOLD)
    parser.add_argument("--update-baseline", action="store_true", help="Replace the stored baseline with the current run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated_at = utc_now().isoformat()
    timestamp = generated_at.replace(":", "").replace("+00:00", "Z")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = args.baseline or output_dir / "baseline.json"
    current_summary_path = output_dir / f"k6-critical-paths-{timestamp}.json"

    if args.summary:
        source_summary_path = args.summary
        summary = read_json(source_summary_path)
        write_json(current_summary_path, summary)
    else:
        run_k6(args, current_summary_path)
        source_summary_path = current_summary_path
        summary = read_json(current_summary_path)

    current_metrics = extract_metrics(summary)

    baseline_created = False
    if args.update_baseline or not baseline_path.exists():
        write_json(baseline_path, build_baseline_payload(generated_at, current_metrics, str(source_summary_path)))
        baseline_created = True

    baseline_payload = read_json(baseline_path)
    baseline_metrics = PerformanceMetrics(**baseline_payload["metrics"])
    regressions = [] if baseline_created else detect_regressions(current_metrics, baseline_metrics, args.regression_threshold)

    report = build_report(
        generated_at=generated_at,
        current=current_metrics,
        baseline=baseline_metrics,
        baseline_path=baseline_path,
        current_summary_path=current_summary_path,
        regressions=regressions,
        baseline_created=baseline_created,
        threshold=args.regression_threshold,
    )

    latest_path = output_dir / "slo-baseline-latest.json"
    report_path = output_dir / f"slo-baseline-{timestamp}.json"
    write_json(report_path, report)
    write_json(latest_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))

    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
