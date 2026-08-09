#!/usr/bin/env python3
"""V1 release factory — build and schema-validate the candidate evidence manifest.

Composes step records produced by certify_candidate.py plus the EXISTING
release-evidence packet generator (make release-evidence-packet). Fails closed
on schema violation or missing step records. Writes only under
artifacts/release/<sha>/ (generated evidence is never committed).

Usage:
    python scripts/release/build_evidence_bundle.py <candidate_sha> [--out-dir DIR]
    make build-release-evidence RELEASE_SHA=<sha>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import NOT_RUN_EXIT_CODE, utc_now
from steps import REPO_ROOT

MANIFEST_SCHEMA = REPO_ROOT / "release" / "v1" / "schemas" / "candidate-manifest.schema.json"
RELEASE_EVIDENCE_MANIFEST_TEMPLATE = (
    REPO_ROOT / "docs" / "launch" / "evidence-manifest.example.yaml"
)


def _manifest_gate(gate: dict) -> dict:
    """Project a certification step record onto the manifest gate schema.

    certification.json carries richer internal fields (log, criterion,
    classification); the manifest schema permits only the deterministic
    gate identity fields, so anything else must be dropped and the log
    path renamed (additionalProperties is false).
    """
    projected = {
        "gate": gate["gate"],
        "command": gate["command"],
        "exit_code": gate["exit_code"],
        "started_at": gate["started_at"],
        "finished_at": gate["finished_at"],
    }
    log_path = gate.get("log_path") or gate.get("log")
    if log_path:
        projected["log_path"] = log_path
    return projected


def _repo_relative(path: Path) -> str:
    """Prefer repo-relative evidence paths; fall back to absolute if outside."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_release_evidence_packet(candidate_sha: str, out_dir: Path) -> Path:
    """Generate the canonical release evidence packet under artifacts/release/<sha>/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    template = yaml.safe_load(RELEASE_EVIDENCE_MANIFEST_TEMPLATE.read_text(encoding="utf-8"))
    template["release_candidate_sha"] = candidate_sha

    manifest_path = out_dir / "release-evidence-manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")

    packet_dir = out_dir / "release-evidence-packet"
    try:
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "ci" / "generate_release_evidence_packet.py"),
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(packet_dir),
                "--release-sha",
                candidate_sha,
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "release evidence packet generation failed for "
            f"{candidate_sha} (exit {exc.returncode})"
        ) from exc
    return packet_dir


def build_manifest(candidate_sha: str, out_dir: Path) -> Path:
    """Assemble artifacts/release/<sha>/candidate-manifest.json from step records."""
    record_path = out_dir / "certification.json"
    if not record_path.exists():
        raise SystemExit(
            f"no certification step records at {record_path}; run certify_candidate.py first"
        )
    gates = json.loads(record_path.read_text(encoding="utf-8"))["gates"]
    not_run = [g["gate"] for g in gates if g["exit_code"] == NOT_RUN_EXIT_CODE]
    failed = [g["gate"] for g in gates if g["exit_code"] > 0]
    certified = not failed and not not_run

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    version_file = REPO_ROOT / "version.txt"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else ""

    manifest = {
        "schema_version": 1,
        "candidate": {
            "sha": candidate_sha,
            "created_at": utc_now(),
            "source_branch": branch,
            "version": version,
            "image_digests": [],
        },
        "gates": [_manifest_gate(g) for g in gates],
        "evidence": {
            "test_reports": sorted(
                _repo_relative(p) for p in out_dir.glob("*.log")
            ),
            "rollback_instructions": "RUNBOOK.md",
            "migration_record": (
                _repo_relative(out_dir / "07-migrations-empty-db.log")
                if (out_dir / "07-migrations-empty-db.log").exists()
                else ""
            ),
        },
        "certification": {
            "status": "certified" if certified else "failed",
            "certifier": "release-certifier",
            "clean_environment": True,
            "remediation_during_certification": False,
            "notes": (
                "All gates passed in a live staging certification."
                if certified
                else f"Not certified. failed={failed} not_run={not_run} (fail closed)."
            ),
        },
        "authorization": {
            "production_authorized": False,
            "authorized_by": "",
        },
    }

    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)

    manifest_path = out_dir / "candidate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_sha")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    out_dir = args.out_dir or (REPO_ROOT / "artifacts" / "release" / args.candidate_sha)
    build_release_evidence_packet(args.candidate_sha, out_dir)
    manifest_path = build_manifest(args.candidate_sha, out_dir)
    status = json.loads(manifest_path.read_text(encoding="utf-8"))["certification"]["status"]
    print(f"Evidence manifest written and schema-validated: {manifest_path}")
    print(f"certification status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
