#!/usr/bin/env python3
"""Evidence producer for gate build.generated_client_reproducible.

Runs the generated API type assertion and produces a gate result JSON.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "artifacts" / "contract" / "generated-client-reproducibility.json"
ASSERT_SCRIPT = ROOT / "apps" / "web" / "scripts" / "quality" / "assert-generated-api-types-current.mjs"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_commit_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _hash_generated() -> str:
    import hashlib
    h = hashlib.sha256()
    files = sorted(
        set((ROOT / "apps" / "web" / "src" / "api" / "generated").rglob("*")).union(
            set((ROOT / "packages" / "platform-contract" / "src" / "typescript" / "generated").rglob("*"))
        )
    )
    for f in files:
        if f.is_file():
            h.update(f"{f.relative_to(ROOT)}\0".encode("utf-8"))
            h.update(f.read_bytes())
    return f"sha256:{h.hexdigest()}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "gate_id": "build.generated_client_reproducible",
        "command": "node scripts/quality/assert-generated-api-types-current.mjs",
        "owner": "value-fabric/frontend-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
        "generated_client_hash": _hash_generated(),
    }

    proc = subprocess.run(
        ["node", str(ASSERT_SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.returncode == 0:
        result["status"] = "PASS"
        result["reason"] = "Generated API clients are up to date and reproducible"
    else:
        result["status"] = "FAIL"
        result["reason"] = "Generated API clients are out of date or unreproducible"
        result["stderr_tail"] = proc.stderr.strip()[-1000:] if proc.stderr else ""
        result["stdout_tail"] = proc.stdout.strip()[-1000:] if proc.stdout else ""

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
