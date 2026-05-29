#!/usr/bin/env python3
"""
CI guard for value_fabric.layer* facade imports.

This script checks for legacy facade imports and reports them.
Initially runs in non-failing mode to establish baseline.
Can be switched to failing mode once migration is complete.

Usage:
    # Non-failing mode (default) - report only
    python scripts/ci/check_value_fabric_facade_imports.py
    
    # Failing mode - enforce no new imports
    python scripts/ci/check_value_fabric_facade_imports.py --fail

Exit codes:
    0 - Success (no imports or within threshold)
    1 - Failure (imports found when in failing mode)
"""

import argparse
import sys
from pathlib import Path

# Import the inventory scanner
sys.path.insert(0, str(Path(__file__).parent.parent))
from ci.inventory_value_fabric_facade import scan_directory, REPO_ROOT


def main():
    parser = argparse.ArgumentParser(description="Check for value_fabric.layer* facade imports")
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Fail CI if facade imports are found (enforcement mode)"
    )
    parser.add_argument(
        "--max-allowed",
        type=int,
        default=0,
        help="Maximum allowed facade imports (default: 0)"
    )
    args = parser.parse_args()
    
    print("Checking for value_fabric.layer* facade imports...")
    
    # Run scan
    results = scan_directory(REPO_ROOT)
    
    total_files = results["total_files"]
    total_imports = results["total_imports"]
    
    print(f"Files with facade imports: {total_files}")
    print(f"Total facade import statements: {total_imports}")
    print(f"By layer: {dict(results['by_layer'])}")
    print(f"By file type: {dict(results['by_file_type'])}")
    
    # Check if we should fail
    if args.fail:
        if total_imports > args.max_allowed:
            print(f"\n❌ FAILED: Found {total_imports} facade imports (max allowed: {args.max_allowed})")
            print("Run 'python scripts/ci/inventory_value_fabric_facade.py' for detailed report")
            return 1
        else:
            print(f"\n✅ PASSED: Facade imports within threshold ({total_imports} <= {args.max_allowed})")
            return 0
    else:
        # Non-failing mode - just report
        print("\n⚠️  WARNING: Running in non-failing mode (report only)")
        print("To enable enforcement, run with --fail flag")
        print("Detailed report: reports/value-fabric-facade-inventory.md")
        return 0


if __name__ == "__main__":
    sys.exit(main())
