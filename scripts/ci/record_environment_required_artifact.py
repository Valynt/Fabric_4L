#!/usr/bin/env python3
"""Record a missing environment-required artifact in the readiness evidence file."""

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: record_environment_required_artifact.py <path> <label> <pattern>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    label = sys.argv[2]
    pattern = sys.argv[3]

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"status": "REQUIRES_ENVIRONMENT", "missing": []}

    data["missing"].append({"label": label, "pattern": pattern})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
