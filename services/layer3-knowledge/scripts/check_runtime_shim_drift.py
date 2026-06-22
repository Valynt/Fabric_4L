1#!/usr/bin/env python3
"""
Check for Layer 3 runtime compatibility shim drift.

This script verifies that the Layer 3 runtime shim has been deprecated/removed
per the migration to direct service access. The shim should NOT exist.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LAYER3_SHIM_PATH = REPO_ROOT / "value_fabric" / "layer3"


def main() -> int:
    """Run the drift check."""
    if LAYER3_SHIM_PATH.exists():
        print(
            f"ERROR: Layer 3 runtime shim still exists at {LAYER3_SHIM_PATH}. "
            "The shim should have been deprecated/removed per the migration to direct service access."
        )
        return 1

    print("OK: Layer 3 runtime shim is absent — migration verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
