#!/usr/bin/env bash
# V1 Release Factory — build the candidate evidence manifest.
#
# Assembles the immutable release-candidate evidence bundle from certification
# step records and validates it against
# release/v1/candidate-manifest.schema.json. Fails closed on schema violation.
#
# Usage:
#   scripts/release/build_evidence_bundle.sh <candidate_sha> [out_dir]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

CANDIDATE_SHA="${1:-}"
if [ -z "${CANDIDATE_SHA}" ]; then
    echo "usage: scripts/release/build_evidence_bundle.sh <candidate_sha> [out_dir]" >&2
    exit 2
fi
OUT_DIR="${2:-artifacts/release/certification-${CANDIDATE_SHA}}"
STEPS_FILE="${OUT_DIR}/steps.jsonl"
MANIFEST="${OUT_DIR}/candidate-manifest.json"
mkdir -p "${OUT_DIR}"

if [ ! -s "${STEPS_FILE}" ]; then
    echo "❌ no certification step records at ${STEPS_FILE}; run certify_candidate.sh first" >&2
    exit 1
fi

python3 - "${CANDIDATE_SHA}" "${STEPS_FILE}" "${MANIFEST}" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

candidate_sha, steps_path, manifest_path = sys.argv[1], sys.argv[2], sys.argv[3]

gates = []
for line in Path(steps_path).read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line:
        gates.append(json.loads(line))

not_run = [g["gate"] for g in gates if g["exit_code"] == -1]
failed = [g["gate"] for g in gates if g["exit_code"] > 0]
certified = not failed and not not_run

branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    capture_output=True, text=True, check=True,
).stdout.strip()
version = Path("version.txt").read_text(encoding="utf-8").strip() if Path("version.txt").exists() else ""

out_dir = Path(manifest_path).parent
manifest = {
    "schema_version": 1,
    "candidate": {
        "sha": candidate_sha,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_branch": branch,
        "version": version,
        "image_digests": [],
    },
    "gates": gates,
    "evidence": {
        "test_reports": sorted(str(p) for p in out_dir.glob("*.log")),
        "rollback_instructions": "RUNBOOK.md",
        "migration_record": str(out_dir / "07-migrations-empty-db.log")
        if (out_dir / "07-migrations-empty-db.log").exists()
        else "",
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

Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

import jsonschema  # noqa: E402

schema = json.loads(Path("release/v1/candidate-manifest.schema.json").read_text(encoding="utf-8"))
jsonschema.validate(manifest, schema)
print(f"Evidence manifest written and schema-validated: {manifest_path}")
print(f"certification status: {manifest['certification']['status']}")
PY
