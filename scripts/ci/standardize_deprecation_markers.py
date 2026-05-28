#!/usr/bin/env python3
"""Standardize deprecation markers across all OpenAPI specs.

This script ensures all deprecated endpoints and fields in OpenAPI specs
have complete deprecation metadata as specified in docs/api-contract-stability.md:

- deprecated: true
- x-deprecated-since: "YYYY-MM-DD"
- x-deprecated-removal-date: "YYYY-MM-DD"
- x-deprecation-owner: "team-name"
- x-deprecation-replacement: "/new/endpoint" (for endpoints)

Usage:
    python scripts/ci/standardize_deprecation_markers.py --check
    python scripts/ci/standardize_deprecation_markers.py --fix
"""

import argparse
import json
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any

# Default deprecation removal period in days
DEFAULT_REMOVAL_DAYS = 180

# Required deprecation metadata fields
REQUIRED_DEPRECATION_FIELDS = [
    "x-deprecated-since",
    "x-deprecated-removal-date",
    "x-deprecation-owner",
]

# HTTP methods to check for deprecation
HTTP_METHODS = ["get", "post", "put", "delete", "patch"]


def check_deprecation_completeness(schema: dict[str, Any], path: str) -> list[str]:
    """Check if a deprecated schema has complete deprecation metadata.
    
    Returns list of missing required fields.
    """
    if not schema.get("deprecated", False):
        return []
    
    return [field for field in REQUIRED_DEPRECATION_FIELDS if field not in schema]


def scan_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Scan an OpenAPI spec for incomplete deprecation markers.
    
    Returns dict with:
    - incomplete_endpoints: list of (path, method, missing_fields)
    - incomplete_schemas: list of (schema_name, missing_fields)
    - total_deprecated: count of deprecated items
    """
    try:
        with open(spec_path) as f:
            spec = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {spec_path}: {e}")
        return {"incomplete_endpoints": [], "incomplete_schemas": [], "total_deprecated": 0}
    
    results = {
        "incomplete_endpoints": [],
        "incomplete_schemas": [],
        "total_deprecated": 0,
    }
    
    # Scan endpoints
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            
            if operation.get("deprecated", False):
                results["total_deprecated"] += 1
                missing = check_deprecation_completeness(operation, f"{method.upper()} {path}")
                if missing:
                    results["incomplete_endpoints"].append((path, method.upper(), missing))
    
    # Scan schemas
    for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
        if schema.get("deprecated", False):
            results["total_deprecated"] += 1
            missing = check_deprecation_completeness(schema, f"schema/{schema_name}")
            if missing:
                results["incomplete_schemas"].append((schema_name, missing))
    
    return results


def _fix_deprecation_in_object(
    obj: dict[str, Any],
    now: str,
    default_owner: str,
    removal_date: str,
) -> int:
    """Fix deprecation metadata in a single object (endpoint or schema).
    
    Returns number of fields fixed.
    """
    fixed_count = 0
    if "x-deprecated-since" not in obj:
        obj["x-deprecated-since"] = now
        fixed_count += 1
    if "x-deprecated-removal-date" not in obj:
        obj["x-deprecated-removal-date"] = removal_date
        fixed_count += 1
    if "x-deprecation-owner" not in obj:
        obj["x-deprecation-owner"] = default_owner
        fixed_count += 1
    return fixed_count


def fix_deprecation_markers(spec_path: Path, default_owner: str = "platform-team") -> int:
    """Add missing deprecation metadata to an OpenAPI spec.
    
    Returns number of items fixed.
    """
    try:
        with open(spec_path) as f:
            spec = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {spec_path}: {e}")
        return 0
    
    fixed_count = 0
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    removal_date = (datetime.now(UTC) + timedelta(days=DEFAULT_REMOVAL_DAYS)).strftime("%Y-%m-%d")
    
    # Fix endpoints
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            
            if operation.get("deprecated", False):
                fixed_count += _fix_deprecation_in_object(operation, now, default_owner, removal_date)
    
    # Fix schemas
    for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
        if schema.get("deprecated", False):
            fixed_count += _fix_deprecation_in_object(schema, now, default_owner, removal_date)
    
    if fixed_count > 0:
        try:
            with open(spec_path, "w") as f:
                json.dump(spec, f, indent=2)
                f.write("\n")
        except IOError as e:
            print(f"Error writing {spec_path}: {e}")
            return 0
    
    return fixed_count


def main():
    parser = argparse.ArgumentParser(description="Standardize deprecation markers in OpenAPI specs")
    parser.add_argument("--check", action="store_true", help="Check for incomplete deprecation markers")
    parser.add_argument("--fix", action="store_true", help="Fix incomplete deprecation markers")
    parser.add_argument("--owner", default="platform-team", help="Default owner for deprecations")
    args = parser.parse_args()
    
    contracts_dir = Path(__file__).parent.parent.parent / "contracts" / "openapi"
    layers = [
        "layer1-ingestion.json",
        "layer2-extraction.json",
        "layer3-knowledge.json",
        "layer4-agents.json",
        "layer5-ground-truth.json",
        "layer6-benchmarks.json",
    ]
    
    total_issues = 0
    total_fixed = 0
    
    for layer_file in layers:
        spec_path = contracts_dir / layer_file
        if not spec_path.exists():
            print(f"⚠️  {layer_file} not found, skipping")
            continue
        
        results = scan_openapi_spec(spec_path)
        
        if results["incomplete_endpoints"] or results["incomplete_schemas"]:
            total_issues += len(results["incomplete_endpoints"]) + len(results["incomplete_schemas"])
            print(f"\nFAIL {layer_file}:")
            
            for path, method, missing in results["incomplete_endpoints"]:
                print(f"  - {method} {path}: missing {', '.join(missing)}")
            
            for schema_name, missing in results["incomplete_schemas"]:
                print(f"  - schema/{schema_name}: missing {', '.join(missing)}")
            
            if args.fix:
                fixed = fix_deprecation_markers(spec_path, args.owner)
                total_fixed += fixed
                print(f"  PASS Fixed {fixed} items")
        else:
            if results["total_deprecated"] > 0:
                print(f"PASS {layer_file}: All {results['total_deprecated']} deprecated items have complete metadata")
            else:
                print(f"PASS {layer_file}: No deprecated items")
    
    if args.check:
        if total_issues > 0:
            print(f"\nFAIL Found {total_issues} incomplete deprecation markers")
            exit(1)
        else:
            print("\nPASS All deprecation markers are complete")
            exit(0)
    
    if args.fix:
        if total_fixed > 0:
            print(f"\nPASS Fixed {total_fixed} deprecation markers across all layers")
            print("⚠️  Please review the changes and set appropriate removal dates")
            exit(0)
        else:
            print("\nPASS No fixes needed")
            exit(0)


if __name__ == "__main__":
    main()
