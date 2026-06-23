#!/usr/bin/env python3
"""Validate that the tenant-isolation bundle is green, fresh, and matches the current commit."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    bundle_path = Path("artifacts/security/tenant-isolation/bundle-latest.json")
    if not bundle_path.exists():
        print("ERROR: tenant-isolation bundle-latest.json is missing", file=sys.stderr)
        return 1

    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    if data.get("status") != "green":
        print("ERROR: latest tenant-isolation bundle is not green", file=sys.stderr)
        return 1

    ts = data.get("timestamp_utc")
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception as exc:
        print(f"ERROR: invalid timestamp_utc in tenant bundle: {ts!r} ({exc})", file=sys.stderr)
        return 1

    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if age_hours > 24:
        print(
            f"ERROR: latest tenant-isolation bundle is stale ({age_hours:.2f}h old; limit 24h)",
            file=sys.stderr,
        )
        return 1

    if data.get("commit_sha") != os.environ.get("GITHUB_SHA"):
        print(
            "ERROR: latest tenant-isolation bundle commit SHA does not match release candidate commit",
            file=sys.stderr,
        )
        return 1

    print(f"Tenant-isolation bundle freshness check passed: age={age_hours:.2f}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
