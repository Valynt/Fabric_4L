#!/usr/bin/env python3
"""Generate deterministic JSON Schema bundle and lockfile from the registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add repo root to path for platform-contract imports
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "packages" / "platform-contract" / "src" / "python"))

from schema_registry.bundler import BundleBuilder

DEFAULT_BUNDLE_PATH = _repo_root / "contracts" / "jsonschema" / "bundle.json"
DEFAULT_LOCKFILE_PATH = _repo_root / "contracts" / "jsonschema" / "bundle-lock.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate schema bundle and lockfile")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH, help="Bundle output path")
    parser.add_argument("--lockfile", type=Path, default=DEFAULT_LOCKFILE_PATH, help="Lockfile output path")
    args = parser.parse_args()

    builder = BundleBuilder()
    builder.write_bundle(args.bundle)
    builder.build_lockfile(output_path=args.lockfile)
    print(f"Bundle written to {args.bundle}")
    print(f"Lockfile written to {args.lockfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
