#!/usr/bin/env python3
"""V1 release factory — fail-closed certification of an immutable candidate SHA.

Thin orchestrator (INV-FACTORY-001): composes the EXISTING canonical gates in
the sequence defined by release/v1/launch-contract.yaml. It records evidence
under artifacts/release/<sha>/ and never modifies source. The certifier may
not remediate failures during certification; the first blocking failure stops
the run and the candidate is marked failed.

Steps that require live staging infrastructure execute only when
CERTIFY_LIVE=1; otherwise they are recorded as not-run and the candidate
CANNOT be certified (fail closed), only rehearsed.

Usage:
    python scripts/release/certify_candidate.py <candidate_sha>
    make certify-release-candidate RELEASE_SHA=<sha>

Output:
    artifacts/release/<sha>/certification.json
    artifacts/release/<sha>/candidate-manifest.json (via build_evidence_bundle)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_evidence_bundle import build_manifest
from models import RunRecord
from steps import CERTIFICATION_STEPS, REPO_ROOT, run_step


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_sha", help="immutable candidate SHA to certify")
    args = parser.parse_args(argv)

    live = os.environ.get("CERTIFY_LIVE", "0") == "1"
    head = _git("rev-parse", "HEAD")
    candidate = _git("rev-parse", args.candidate_sha)

    if candidate != head:
        print(
            f"ERROR: checkout HEAD {head} does not match candidate {candidate}; "
            "certification runs only against the exact immutable candidate.",
            file=sys.stderr,
        )
        return 2
    if _git("status", "--short"):
        print(
            "ERROR: working tree is dirty; certification requires a clean, "
            "read-only checkout (no remediation during certification).",
            file=sys.stderr,
        )
        return 2

    out_dir = REPO_ROOT / "artifacts" / "release" / candidate
    out_dir.mkdir(parents=True, exist_ok=True)
    record = RunRecord(
        kind="candidate-certification",
        sha=candidate,
        branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
        # Verified above: HEAD matches the candidate and the tree is clean.
        clean_tree_verified=True,
    )

    print(f"Certifying candidate {candidate} (live={live}) -> {out_dir}")
    aborted = False
    for step in CERTIFICATION_STEPS:
        result = run_step(step, out_dir, live=live)
        record.results.append(result)
        # Not-run results (live-only steps without CERTIFY_LIVE=1, and
        # unimplemented release operations) do not abort the run — later steps
        # still produce evidence — but they always leave the candidate
        # uncertified (fail closed, enforced below and in build_manifest).
        if step.blocking and not result.passed and not result.not_run:
            print(
                f"❌ certification failed at {step.name}. The certifier may not "
                f"remediate; candidate {candidate} is NOT certified.",
                file=sys.stderr,
            )
            aborted = True
            break

    record.write(out_dir / "certification.json")
    manifest_path = build_manifest(candidate, out_dir)
    print(f"Evidence manifest: {manifest_path}")

    if aborted or record.failed:
        return 1
    if record.not_run_steps:
        names = ", ".join(r.gate for r in record.not_run_steps)
        print(
            f"⚠️  Steps recorded as not-run ({names}): live-only steps need "
            "CERTIFY_LIVE=1 in staging, and unimplemented release operations "
            "block until they exist. The candidate stays uncertified (fail closed)."
        )
        return 1
    print(f"✅ all certification steps passed for {candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
