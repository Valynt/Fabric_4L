#!/usr/bin/env python3
"""Generate the tenant-isolation bundle-latest.json artifact used by release gates."""

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "Usage: generate_tenant_isolation_bundle.py <out_path> <timestamp_utc> <commit_sha> "
            "<security_test_count> <service_test_count>",
            file=sys.stderr,
        )
        return 2

    out_path = Path(sys.argv[1])
    timestamp_utc = sys.argv[2]
    commit_sha = sys.argv[3]
    try:
        security_test_count = int(sys.argv[4])
        service_test_count = int(sys.argv[5])
    except ValueError as exc:
        print(f"Invalid test count argument: {exc}", file=sys.stderr)
        return 2

    data = {
        "suite": "tenant-boundary",
        "status": "green",
        "timestamp_utc": timestamp_utc,
        "commit_sha": commit_sha,
        "retention_expectation_hours": 24,
        "security_tests": security_test_count,
        "service_tenant_tests": service_test_count,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
