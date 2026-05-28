from __future__ import annotations

#!/usr/bin/env python3
"""Fail CI if Layer 3 backup compatibility shims drift from canonical forwarders."""


import argparse
import sys
from pathlib import Path


EXPECTED: dict[str, str] = {
    "services/layer3-knowledge/src/backup/backup_manager.py": (
        '"""Compatibility wrapper for value_fabric.layer3.backup.backup_manager."""\n\n'
        'from value_fabric.layer3.backup.backup_manager import *  # noqa: F401,F403\n'
    ),
    "services/layer3-knowledge/src/backup/__init__.py": (
        '"""Compatibility wrapper for ``value_fabric.layer3.backup``.\n\n'
        'Canonical implementation lives in ``value_fabric.layer3.backup``\n'
        'per ``docs/reference/layer-runtime-path-governance.md``.\n"""\n\n'
        'from value_fabric.layer3.backup import *  # noqa: F401,F403\n'
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail CI if Layer 3 backup compatibility shims drift from canonical forwarders."
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
        print("Layer 3 backup compatibility shim drift detected:", file=sys.stderr)
        for item in drifted:
            print(f" - {item}", file=sys.stderr)
        print(
            "Keep canonical logic in value_fabric/layer3/backup/ and preserve service wrappers as thin forwarders.",
            file=sys.stderr,
        )
        return 1

    print("Layer 3 backup compatibility shim check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
