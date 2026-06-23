#!/usr/bin/env python3
"""Fail when the Layer 6 compatibility namespace grows runtime logic."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services/layer6-benchmarks/src"
COMPAT_NAMESPACE = ROOT / "value_fabric/layer6"
ALLOWED_COMPAT_FILES = {Path("__init__.py")}


def main() -> int:
    if not SERVICE_SRC.exists():
        print(f"Missing canonical Layer 6 source tree: {SERVICE_SRC.relative_to(ROOT)}")
        return 1

    if not COMPAT_NAMESPACE.exists():
        print("Layer 6 compatibility namespace not present; nothing to check.")
        return 0

    violations = [
        path.relative_to(COMPAT_NAMESPACE)
        for path in sorted(COMPAT_NAMESPACE.rglob("*.py"))
        if path.relative_to(COMPAT_NAMESPACE) not in ALLOWED_COMPAT_FILES
    ]

    if violations:
        print("Layer 6 compatibility namespace contains runtime Python files:")
        for rel in violations:
            print(f" - value_fabric/layer6/{rel.as_posix()}")
        print("\nCanonical Layer 6 runtime logic belongs in services/layer6-benchmarks/src/.")
        return 1

    print("Layer 6 compatibility namespace check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
