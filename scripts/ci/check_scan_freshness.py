#!/usr/bin/env python3
"""Verify vulnerability scan coverage, configuration, and freshness for all 6 service layers."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

REQUIRED_LAYERS = (
    "layer1-ingestion",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "layer6-benchmarks",
)


def verify_workflow_schedules() -> list[str]:
    """Verify that required workflows have scheduled triggers covering all 6 layers."""
    errors = []

    supply_chain_wf = WORKFLOW_DIR / "supply-chain-integrity.yml"
    if not supply_chain_wf.exists():
        errors.append("supply-chain-integrity.yml is missing")
    else:
        content = supply_chain_wf.read_text(encoding="utf-8")
        if "schedule:" not in content or "cron:" not in content:
            errors.append("supply-chain-integrity.yml lacks a scheduled cron trigger")
        for layer in REQUIRED_LAYERS:
            if layer not in content:
                errors.append(f"supply-chain-integrity.yml is missing layer: {layer}")

    dep_scan_wf = WORKFLOW_DIR / "dependency-scan.yml"
    if not dep_scan_wf.exists():
        errors.append("dependency-scan.yml is missing")
    else:
        content = dep_scan_wf.read_text(encoding="utf-8")
        if "schedule:" not in content or "cron:" not in content:
            errors.append("dependency-scan.yml lacks a scheduled cron trigger")
        for layer in REQUIRED_LAYERS:
            if layer not in content:
                errors.append(
                    f"dependency-scan.yml is missing layer container scan for: {layer}"
                )

    return errors


def verify_sarif_freshness(sarif_files: list[Path], max_age_days: int = 7) -> list[str]:
    """Verify that existing SARIF scan artifacts are within the freshness threshold."""
    errors = []
    now = datetime.now(timezone.utc)

    for sarif_path in sarif_files:
        if not sarif_path.exists():
            continue
        try:
            mtime = datetime.fromtimestamp(sarif_path.stat().st_mtime, timezone.utc)
            age_days = (now - mtime).total_seconds() / 86400.0
            if age_days > max_age_days:
                errors.append(
                    f"SARIF file {sarif_path.name} is stale ({age_days:.1f} days old > {max_age_days} days)"
                )
        except Exception as exc:
            errors.append(f"Failed to check freshness of {sarif_path}: {exc}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-days", type=int, default=7, help="Maximum allowed scan age in days"
    )
    parser.add_argument(
        "--sarif-dir",
        type=Path,
        default=None,
        help="Directory containing SARIF reports to inspect",
    )
    args = parser.parse_args()

    errors = verify_workflow_schedules()

    if args.sarif_dir and args.sarif_dir.exists():
        sarif_files = list(args.sarif_dir.glob("**/*.sarif"))
        errors.extend(
            verify_sarif_freshness(sarif_files, max_age_days=args.max_age_days)
        )

    if errors:
        for err in errors:
            print(f"Scan Freshness Error: {err}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Scan freshness and schedule coverage verified for all {len(REQUIRED_LAYERS)} layers."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
