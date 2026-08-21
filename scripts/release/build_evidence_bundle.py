#!/usr/bin/env python3
"""V1 release factory — build and schema-validate the candidate evidence manifest.

Composes step records produced by certify_candidate.py plus the EXISTING
release-evidence packet generator (scripts/ci/generate_release_evidence_packet.py,
invoked candidate-scoped with --release-sha). Fails closed on schema violation,
missing step records, a record/packet SHA mismatch, or a malformed candidate
SHA — before any side effect. Writes only under artifacts/release/<sha>/
(generated evidence is never committed).

Exit status is fail-closed: nonzero unless the manifest certifies the
candidate, or --package-noncertified-diagnostics is passed explicitly to build
a diagnostics-only bundle.

Usage:
    python scripts/release/build_evidence_bundle.py <candidate_sha> [--out-dir DIR]
    make build-release-evidence RELEASE_SHA=<sha>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
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
# The gitignore content of this directory is the observed clean-tree baseline
# for clean_environment; no generated evidence may ever be committed here.
GENERATED_ARTIFACT_PREFIXES = ("artifacts/release",)
CANDIDATE_SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


def require_full_sha(candidate_sha: str) -> str:
    """Fail closed on anything that is not an immutable 40-char hex SHA."""
    if not CANDIDATE_SHA_PATTERN.fullmatch(candidate_sha):
        raise SystemExit(
            f"candidate sha {candidate_sha!r} is not a 40-character lowercase hex "
            "SHA; evidence bundles are bound to immutable candidates only "
            "(fail closed)."
        )
    return candidate_sha


def tracked_generated_artifacts() -> list[str]:
    """List tracked files under generated-evidence prefixes.

    Output paths are relative to the current working directory so callers can
    point the check at a temporary scratch repo in tests.
    """
    proc = subprocess.run(
        ["git", "ls-files", "--", *GENERATED_ARTIFACT_PREFIXES],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in proc.stdout.splitlines() if line]


def _manifest_gate(gate: dict, out_dir: Path | None = None) -> dict:
    """Project a certification step record onto the manifest gate schema.

    certification.json carries richer internal fields (log, criterion,
    classification); the manifest schema permits only the deterministic
    gate identity fields, so anything else must be dropped and the log
    path renamed and normalized to a portable path
    (additionalProperties is false).

    When *out_dir* is given, log paths inside that directory are stored as
    bare file names so that the manifest stays portable regardless of where
    the evidence directory lives on the runner filesystem.
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
        projected["log_path"] = _portable_log_path(Path(log_path), out_dir)
    return projected


def _portable_log_path(log_path: Path, out_dir: Path | None = None) -> str:
    """Return a portable log path: basename when inside *out_dir*, else repo-relative."""
    if out_dir is not None:
        try:
            return str(log_path.relative_to(out_dir))
        except ValueError:
            pass
    return _repo_relative(log_path)


def _repo_relative(path: Path) -> str:
    """Prefer repo-relative evidence paths; fall back to the file name.

    An absolute fallback leaks runner-specific filesystem layout into the
    manifest; the file name alone stays portable while remaining resolvable
    within the candidate evidence directory.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path.name


def build_release_evidence_packet(candidate_sha: str, out_dir: Path) -> Path:
    """Generate the canonical release evidence packet under artifacts/release/<sha>/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    template = yaml.safe_load(RELEASE_EVIDENCE_MANIFEST_TEMPLATE.read_text(encoding="utf-8"))
    if not isinstance(template, dict):
        raise SystemExit(
            f"evidence manifest template {RELEASE_EVIDENCE_MANIFEST_TEMPLATE} must "
            "parse to a YAML mapping (fail closed)."
        )
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


def _sha256_tree(root: Path) -> str:
    """Deterministic digest over every file under root (relpath + contents)."""
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for path in files:
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def verify_evidence_packet(candidate_sha: str, packet_dir: Path) -> str:
    """Bind the generated packet to the candidate; return its SHA-256 digest.

    Fails closed when the packet is missing, empty, records no release SHA,
    or records a different release SHA than the candidate being evidenced.
    """
    if not packet_dir.is_dir():
        raise SystemExit(
            f"evidence packet directory {packet_dir} was not generated (fail closed)."
        )
    files = [p for p in packet_dir.rglob("*") if p.is_file()]
    if not files:
        raise SystemExit(
            f"evidence packet directory {packet_dir} is empty (fail closed)."
        )
    packet_shas = set()
    for path in files:
        if path.suffix not in {".yaml", ".yml", ".json"}:
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(payload, dict):
            for key in ("release_candidate_sha", "release_sha"):
                value = payload.get(key)
                if isinstance(value, str):
                    packet_shas.add(value)
    # A packet that records no release SHA cannot be verified as bound to the
    # candidate; that is indistinguishable from an unbound packet (fail closed).
    if not packet_shas:
        raise SystemExit(
            f"evidence packet at {packet_dir} records no release SHA; the packet "
            f"cannot be verified as bound to candidate {candidate_sha} (fail closed)."
        )
    mismatched = {sha for sha in packet_shas if sha != candidate_sha}
    if mismatched:
        raise SystemExit(
            f"evidence packet at {packet_dir} records release sha(s) "
            f"{sorted(mismatched)} that do not match candidate {candidate_sha}; "
            "the packet must be bound to the exact immutable candidate "
            "(fail closed)."
        )
    return _sha256_tree(packet_dir)


def _certification_record(candidate_sha: str, out_dir: Path) -> dict:
    record_path = out_dir / "certification.json"
    if not record_path.exists():
        raise SystemExit(
            f"no certification step records at {record_path}; run certify_candidate.py first"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    recorded_sha = record.get("sha", "")
    if recorded_sha != candidate_sha:
        raise SystemExit(
            f"certification records at {record_path} were produced for "
            f"{recorded_sha or '<missing sha>'}, not candidate {candidate_sha}; "
            "the evidence manifest must be bound to the exact immutable candidate "
            "(fail closed)."
        )
    return record


def _image_digests(out_dir: Path) -> list[dict]:
    """Recorded image digests from the docker-build step, or [] when absent.

    The manifest never invents digests: they exist only when the
    04b-docker-build step recorded an image-digests.txt file with
    'image@sha256:<digest>' lines.
    """
    digests_file = out_dir / "image-digests.txt"
    if not digests_file.exists():
        return []
    digests = []
    for line in digests_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "@" not in line:
            continue
        image, _, digest = line.rpartition("@")
        digests.append({"image": image, "digest": digest})
    return digests


def _clean_environment(record: dict, gates: list[dict]) -> bool:
    """True only with recorded evidence; never assumed.

    Requires the certifier's clean-checkout verification (recorded at run
    time), no failed gates, and no generated evidence tracked in git.
    """
    failed = [
        g["gate"]
        for g in gates
        if g["exit_code"] != 0 and g["exit_code"] != NOT_RUN_EXIT_CODE
    ]
    return (
        bool(record.get("clean_tree_verified"))
        and not failed
        and not tracked_generated_artifacts()
    )


def build_manifest(
    candidate_sha: str,
    out_dir: Path,
    packet_digest: str | None = None,
    record: dict | None = None,
) -> Path:
    """Assemble artifacts/release/<sha>/candidate-manifest.json from step records.

    Callers that already validated the certification record (e.g. main(), which
    fails closed before generating the packet) pass it in so the manifest is
    built from the exact record that passed pre-side-effect validation.
    """
    require_full_sha(candidate_sha)
    if record is None:
        record = _certification_record(candidate_sha, out_dir)
    gates = record["gates"]
    not_run = [g["gate"] for g in gates if g["exit_code"] == NOT_RUN_EXIT_CODE]
    # Any exit other than success or the explicit not-run sentinel is a failure
    # (including negative codes from signal-terminated processes).
    failed = [
        g["gate"]
        for g in gates
        if g["exit_code"] != 0 and g["exit_code"] != NOT_RUN_EXIT_CODE
    ]
    certified = not failed and not not_run
    # Distinguish a run that FAILED (at least one gate exited nonzero) from an
    # inconclusive run that is NOT_CERTIFIED (no failures, but required steps
    # never ran — live-only without CERTIFY_LIVE=1 or unimplemented). Both are
    # non-certified; neither may ever be presented as certified.
    if certified:
        status = "certified"
    elif failed:
        status = "failed"
    else:
        status = "not_certified"

    # The branch was captured by certify_candidate.py at certification time and
    # written into the record; do not re-derive it from the current checkout.
    branch = record.get("branch", "")
    if not branch:
        raise SystemExit(
            f"certification records at {out_dir / 'certification.json'} carry no "
            "source branch; the manifest must reflect the certified checkout "
            "(fail closed)."
        )
    version_file = REPO_ROOT / "version.txt"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else ""

    clean_environment = _clean_environment(record, gates)
    notes = []
    if not clean_environment:
        notes.append(
            "the manifest records clean_environment=false rather than "
            "asserting an unverified clean checkout"
        )
    if certified:
        note = "All gates passed in a live staging certification."
    elif failed:
        note = f"Not certified. failed={failed} not_run={not_run} (fail closed)."
    else:
        note = (
            f"Not certified: inconclusive. No gate failed, but required steps "
            f"never ran: not_run={not_run} (fail closed)."
        )
    if notes:
        note = f"{note} Note: {'; '.join(notes)}."

    manifest = {
        "schema_version": 1,
        "candidate": {
            "sha": candidate_sha,
            "created_at": utc_now(),
            "source_branch": branch,
            "version": version,
            "image_digests": _image_digests(out_dir),
        },
        "gates": [_manifest_gate(g, out_dir) for g in gates],
        "evidence": {
            "test_reports": sorted(
                _repo_relative(p) for p in out_dir.glob("*.log")
            ),
            "rollback_instructions": "docs/runbooks/deployment/rollback-production-release.md",
            "migration_record": (
                _repo_relative(out_dir / "07-migrations-empty-db.log")
                if (out_dir / "07-migrations-empty-db.log").exists()
                else ""
            ),
            **(
                {"evidence_packet_digest": packet_digest}
                if packet_digest is not None
                else {}
            ),
            **(
                {"sbom": _repo_relative(out_dir / "fabric-4l-source-sbom.cdx.json")}
                if (out_dir / "fabric-4l-source-sbom.cdx.json").exists()
                or (
                    (REPO_ROOT / "artifacts" / "supply-chain" / "fabric-4l-source-sbom.cdx.json").exists()
                    and shutil.copy2(
                        REPO_ROOT / "artifacts" / "supply-chain" / "fabric-4l-source-sbom.cdx.json",
                        out_dir / "fabric-4l-source-sbom.cdx.json",
                    )
                )
                else {}
            ),
            **(
                {"provenance": _repo_relative(out_dir / "provenance.json")}
                if (out_dir / "provenance.json").exists()
                or (
                    (REPO_ROOT / "artifacts" / "supply-chain" / "provenance.json").exists()
                    and shutil.copy2(
                        REPO_ROOT / "artifacts" / "supply-chain" / "provenance.json",
                        out_dir / "provenance.json",
                    )
                )
                else {}
            ),
        },
        "certification": {
            "status": status,
            "certifier": "release-certifier",
            "clean_environment": clean_environment,
            "remediation_during_certification": False,
            "notes": note,
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
    parser.add_argument(
        "--package-noncertified-diagnostics",
        action="store_true",
        help=(
            "build the diagnostics bundle for an uncertified run and exit 0; "
            "without this flag any non-certified manifest exits nonzero "
            "(fail closed)"
        ),
    )
    args = parser.parse_args(argv)

    # Validate the candidate identity before ANY side effect (directory
    # creation, packet generation, manifest writes).
    candidate_sha = require_full_sha(args.candidate_sha)
    out_dir = args.out_dir or (REPO_ROOT / "artifacts" / "release" / candidate_sha)
    # Fail before the packet-generation side effect when the certification
    # record is missing or bound to another SHA; the same validated record is
    # passed to build_manifest so the manifest reflects exactly what passed
    # this pre-side-effect validation.
    record = _certification_record(candidate_sha, out_dir)
    packet_dir = build_release_evidence_packet(candidate_sha, out_dir)
    packet_digest = verify_evidence_packet(candidate_sha, packet_dir)
    manifest_path = build_manifest(
        candidate_sha, out_dir, packet_digest=packet_digest, record=record
    )
    status = json.loads(manifest_path.read_text(encoding="utf-8"))["certification"]["status"]
    print(f"Evidence manifest written and schema-validated: {manifest_path}")
    print(f"certification status: {status}")
    if status != "certified" and not args.package_noncertified_diagnostics:
        print(
            "FAIL: candidate is not certified; refusing to report success for "
            "non-certified packaging (fail closed). Re-run with "
            "--package-noncertified-diagnostics to build a diagnostics-only "
            "bundle that exits 0.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
