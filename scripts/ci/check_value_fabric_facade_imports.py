#!/usr/bin/env python3
"""
CI guard for value_fabric.layer* facade imports.

This script checks for legacy facade imports against an allowlist.
Imports not in the allowlist will cause CI to fail in enforcement mode.

Usage:
    # Non-failing mode (default) - report only
    python scripts/ci/check_value_fabric_facade_imports.py

    # Failing mode - enforce allowlist
    python scripts/ci/check_value_fabric_facade_imports.py --fail

Exit codes:
    0 - Success (all imports in allowlist)
    1 - Failure (imports not in allowlist when in failing mode)
"""

import argparse
import sys
from pathlib import Path
from fnmatch import fnmatch

# Import the inventory scanner
sys.path.insert(0, str(Path(__file__).parent.parent))
from ci.inventory_value_fabric_facade import scan_directory, REPO_ROOT

ALLOWLIST_PATH = REPO_ROOT / "config" / "ci" / "facade-import-allowlist.yaml"


def load_allowlist():
    """Load the facade import allowlist from YAML."""
    import yaml

    if not ALLOWLIST_PATH.exists():
        print(f"⚠️  WARNING: Allowlist file not found at {ALLOWLIST_PATH}")
        print("All facade imports will be treated as violations")
        return {}

    with open(ALLOWLIST_PATH) as f:
        return yaml.safe_load(f) or {}


def is_in_allowlist(file_path, allowlist):
    """Check if a file path is in the allowlist (supports glob patterns)."""
    rel_path = str(file_path.relative_to(REPO_ROOT)).replace("\\", "/")

    for pattern in allowlist.keys():
        # Support glob patterns like "services/layer3-knowledge/**"
        if fnmatch(rel_path, pattern):
            return True, allowlist[pattern]

    return False, None


def main():
    parser = argparse.ArgumentParser(description="Check for value_fabric.layer* facade imports")
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Fail CI if facade imports are not in allowlist (enforcement mode)"
    )
    args = parser.parse_args()

    print("Checking for value_fabric.layer* facade imports...")

    # Load allowlist
    allowlist = load_allowlist()
    print(f"Allowlist entries: {len(allowlist)}")

    # Run scan
    results = scan_directory(REPO_ROOT)

    total_files = results["total_files"]
    total_imports = results["total_imports"]
    by_file = results["by_file"]

    print(f"Files with facade imports: {total_files}")
    print(f"Total facade import statements: {total_imports}")
    print(f"By layer: {dict(results['by_layer'])}")
    print(f"By file type: {dict(results['by_file_type'])}")

    # Check against allowlist
    violations = []
    allowlisted_count = 0

    for file_path_str, imports in by_file.items():
        file_path = REPO_ROOT / file_path_str
        in_allowlist, entry = is_in_allowlist(file_path, allowlist)
        if in_allowlist:
            allowlisted_count += len(imports)
        else:
            violations.append((file_path, imports))

    print(f"\nAllowlisted imports: {allowlisted_count}")
    print(f"Unallowlisted imports: {total_imports - allowlisted_count}")

    if violations:
        print("\n❌ VIOLATIONS (imports not in allowlist):")
        for file_path, imports in violations:
            print(f"  {file_path}")
            for imp in imports:
                print(f"    {imp}")

    # Check if we should fail
    if args.fail:
        if violations:
            print(f"\n❌ FAILED: Found {len(violations)} files with unallowlisted facade imports")
            print(f"Add these files to {ALLOWLIST_PATH} or migrate to canonical imports")
            return 1
        else:
            print(f"\n✅ PASSED: All facade imports are allowlisted")
            return 0
    else:
        # Non-failing mode - just report
        if violations:
            print("\n⚠️  WARNING: Running in non-failing mode (report only)")
            print("To enable enforcement, run with --fail flag")
        else:
            print("\n✅ All facade imports are allowlisted")
        print("Detailed report: reports/value-fabric-facade-inventory.md")
        return 0


if __name__ == "__main__":
    sys.exit(main())
