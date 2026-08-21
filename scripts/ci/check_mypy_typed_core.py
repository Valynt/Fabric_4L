#!/usr/bin/env python3
"""Run mypy on the Layer 1 typed core and fail on any errors.

Typed core is the part of the codebase that must stay mypy-clean:
- orchestrator (stage handlers, coordinator, state machine, contracts)
- domain types and contracts

Usage:
    python scripts/ci/check_mypy_typed_core.py --service-dir services/layer1-ingestion
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TYPED_CORE_PATHS = [
    "src/layer1_ingestion/orchestrator",
    "src/layer1_ingestion/domain",
    "src/layer1_ingestion/shared/models.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-dir", required=True, type=Path)
    args = parser.parse_args()

    service_dir = args.service_dir.resolve()
    cmd = [sys.executable, "-m", "mypy", *TYPED_CORE_PATHS]
    result = subprocess.run(cmd, cwd=service_dir, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
