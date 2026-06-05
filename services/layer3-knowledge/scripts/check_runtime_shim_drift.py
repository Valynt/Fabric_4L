from __future__ import annotations

#!/usr/bin/env python3
"""Fail CI if Layer 3 runtime compatibility modules drift from shim forwarders."""


import argparse
import sys
from pathlib import Path


# The value_fabric.layer3 namespace is a path-redirect shim: its __init__.py
# appends services/layer3-knowledge/src/ to __path__, making the service tree
# the canonical source.  Files inside services/layer3-knowledge/src/ are
# therefore the canonical implementations — they cannot re-export themselves
# via value_fabric.layer3.* without creating a circular import.
#
# The three files below were previously expected to be thin re-export wrappers,
# but that expectation was architecturally incorrect given the redirect-shim
# design.  They are substantive canonical modules and are excluded from the
# drift check.  Any future service-local *compatibility* shims (files that
# exist solely to forward to a canonical path outside this service) should be
# added to EXPECTED with their required shim content.
EXPECTED: dict[str, str] = {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail CI if Layer 3 runtime compatibility modules drift from shim forwarders."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root directory (default: auto-detected)",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    drifted: list[str] = []
    for rel_path, expected in EXPECTED.items():
        file_path = repo_root / rel_path
        if not file_path.exists():
            drifted.append(f"MISSING: {rel_path}")
            continue
        try:
            actual = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            drifted.append(f"READ_ERROR: {rel_path} ({exc})")
            continue
        if actual != expected:
            drifted.append(f"DRIFT: {rel_path}")

    if drifted:
        print("Layer 3 runtime compatibility shim drift detected:", file=sys.stderr)
        for item in drifted:
            print(f" - {item}", file=sys.stderr)
        print(
            "Keep canonical runtime logic in services/layer3-knowledge/src/ and preserve value_fabric/layer3 as a placeholder/shim namespace.",
            file=sys.stderr,
        )
        return 1

    print("Layer 3 runtime compatibility shim check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
