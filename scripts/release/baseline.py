#!/usr/bin/env python3
"""V1 release factory — Phase 1 classified baseline from a clean checkout.

Runs the canonical gates and records a classified baseline under
artifacts/release/<sha>/baseline.json. This script VALIDATES; it never
repairs, commits, or pushes, and it never writes into release/v1/ (generated
state is never committed — see launch-contract.yaml artifact_policy).

Failure classification is a human/Release-Director decision; failures default
to "unclassified" and MUST be triaged before any launch-readiness claim.
Flaky classification must come from the flakiness-tracker workflow output,
not local retries.

Usage:
    python scripts/release/baseline.py [--skip-setup]
    make release-baseline
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import RunRecord
from steps import BASELINE_STEPS, REPO_ROOT, run_step


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-setup", action="store_true")
    args = parser.parse_args(argv)

    if _git("status", "--short"):
        print("ERROR: baseline requires a clean checkout; working tree is dirty", file=sys.stderr)
        return 2

    sha = _git("rev-parse", "HEAD")
    out_dir = REPO_ROOT / "artifacts" / "release" / sha
    out_dir.mkdir(parents=True, exist_ok=True)

    record = RunRecord(
        kind="release-baseline",
        sha=sha,
        branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
        # Verified above: baseline runs only from a clean checkout.
        clean_tree_verified=True,
    )
    steps = [s for s in BASELINE_STEPS if not (args.skip_setup and s.name == "setup")]
    print(f"Release baseline for {sha} -> {out_dir}")
    for step in steps:
        record.results.append(run_step(step, out_dir, live=True))

    record.write(out_dir / "baseline.json")
    print(f"Baseline written to {out_dir / 'baseline.json'}")
    if record.failed:
        print(
            "⚠️  One or more baseline gates failed; triage and classify each "
            "failure before proceeding.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
