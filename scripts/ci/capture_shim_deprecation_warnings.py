"""Capture and archive namespace shim deprecation warnings from test runs.

This script runs pytest with deprecation warnings enabled for value_fabric shims,
captures the warnings, and generates a usage report for Phase 1 remediation tracking.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "shim-deprecation"


def parse_warnings(output: str) -> Dict[str, List[str]]:
    """Parse pytest warning output to extract shim deprecation warnings."""
    warnings_by_layer: Dict[str, List[str]] = {
        "layer1": [],
        "layer2": [],
        "layer3": [],
        "layer4": [],
        "layer5": [],
        "layer6": [],
    }

    lines = output.split("\n")
    for line in lines:
        if "value_fabric.layer" in line and "deprecated" in line.lower():
            for layer in warnings_by_layer:
                if f"value_fabric.{layer}" in line:
                    # Extract the file location if present
                    if ":" in line:
                        file_loc = line.split(":")[0]
                        warnings_by_layer[layer].append(file_loc)
                    else:
                        warnings_by_layer[layer].append("unknown_location")

    return warnings_by_layer


def run_tests_with_warnings_capture(test_path: str | None = None) -> tuple[int, str]:
    """Run pytest with warnings enabled."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-W",
        "default::DeprecationWarning:value_fabric",
        "--tb=no",
        "-q",
    ]

    if test_path:
        cmd.append(test_path)
    else:
        # Run all tests except slow/integration ones for baseline
        cmd.extend([
            "-m",
            "not slow and not requires_postgres and not requires_neo4j and not requires_redis",
            "tests/",
            "services/layer1-ingestion/tests/",
            "services/layer2-extraction/tests/",
            "services/layer3-knowledge/tests/",
            "services/layer4-agents/tests/",
            "services/layer5-ground-truth/tests/",
            "services/layer6-benchmarks/tests/",
        ])

    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    return result.returncode, result.stdout + result.stderr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture namespace shim deprecation warnings"
    )
    parser.add_argument(
        "--test-path",
        help="Specific test path to run (default: all non-slow tests)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline report with current findings",
    )
    args = parser.parse_args(argv)

    print("→ Running tests with deprecation warning capture...")
    returncode, output = run_tests_with_warnings_capture(args.test_path)

    print("→ Parsing deprecation warnings...")
    warnings_by_layer = parse_warnings(output)

    total_warnings = sum(len(v) for v in warnings_by_layer.values())
    print(f"\nFound {total_warnings} shim deprecation warnings:")

    for layer, locations in warnings_by_layer.items():
        if locations:
            print(f"  {layer}: {len(locations)} warning(s)")
            for loc in sorted(set(locations)):
                print(f"    - {loc}")

    # Generate report
    report = {
        "total_warnings": total_warnings,
        "by_layer": {k: len(set(v)) for k, v in warnings_by_layer.items()},
        "details": {k: sorted(set(v)) for k, v in warnings_by_layer.items()},
    }

    report_path = ARTIFACT_DIR / "deprecation-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n→ Report saved to {report_path}")

    # Generate human-readable summary
    summary_path = ARTIFACT_DIR / "deprecation-report.md"
    summary = f"# Namespace Shim Deprecation Warning Report\n\n"
    summary += f"**Total Warnings:** {total_warnings}\n\n"
    summary += "## By Layer\n\n"
    for layer, count in report["by_layer"].items():
        if count > 0:
            summary += f"- **{layer}:** {count} warning(s)\n"
    summary += "\n## Details\n\n"
    for layer, locations in report["details"].items():
        if locations:
            summary += f"### {layer}\n\n"
            for loc in locations:
                summary += f"- `{loc}`\n"
            summary += "\n"

    summary_path.write_text(summary, encoding="utf-8")
    print(f"→ Summary saved to {summary_path}")

    if args.update_baseline:
        baseline_path = ARTIFACT_DIR / "baseline.json"
        baseline_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"→ Baseline updated at {baseline_path}")

    return 0 if total_warnings == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
