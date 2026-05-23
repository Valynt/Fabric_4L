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
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


def check_deprecation_completeness(schema: dict[str, Any], path: str) -> list[str]:
    """Check if a deprecated schema has complete deprecation metadata.
    
    Returns list of missing required fields.
    """
    if not schema.get("deprecated", False):
        return []
    
    missing = []
    
    if "x-deprecated-since" not in schema:
        missing.append("x-deprecated-since")
    if "x-deprecated-removal-date" not in schema:
        missing.append("x-deprecated-removal-date")
    if "x-deprecation-owner" not in schema:
        missing.append("x-deprecation-owner")
    
    return missing


def scan_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Scan an OpenAPI spec for incomplete deprecation markers.
    
    Returns dict with:
    - incomplete_endpoints: list of (path, method, missing_fields)
    - incomplete_schemas: list of (schema_name, missing_fields)
    - total_deprecated: count of deprecated items
    """
    with open(spec_path) as f:
        spec = json.load(f)
    
    results = {
        "incomplete_endpoints": [],
        "incomplete_schemas": [],
        "total_deprecated": 0,
    }
    
    # Scan endpoints
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
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


def fix_deprecation_markers(spec_path: Path, default_owner: str = "platform-team") -> int:
    """Add missing deprecation metadata to an OpenAPI spec.
    
    Returns number of items fixed.
    """
    with open(spec_path) as f:
        spec = json.load(f)
    
    fixed_count = 0
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Fix endpoints
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            if operation.get("deprecated", False):
                if "x-deprecated-since" not in operation:
                    operation["x-deprecated-since"] = now
                    fixed_count += 1
                if "x-deprecated-removal-date" not in operation:
                    # Default to 6 months from now
                    from datetime import timedelta
                    removal = (datetime.now(UTC) + timedelta(days=180)).strftime("%Y-%m-%d")
                    operation["x-deprecated-removal-date"] = removal
                    fixed_count += 1
                if "x-deprecation-owner" not in operation:
                    operation["x-deprecation-owner"] = default_owner
                    fixed_count += 1
    
    # Fix schemas
    for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
        if schema.get("deprecated", False):
            if "x-deprecated-since" not in schema:
                schema["x-deprecated-since"] = now
                fixed_count += 1
            if "x-deprecated-removal-date" not in schema:
                from datetime import timedelta
                removal = (datetime.now(UTC) + timedelta(days=180)).strftime("%Y-%m-%d")
                schema["x-deprecated-removal-date"] = removal
                fixed_count += 1
            if "x-deprecation-owner" not in schema:
                schema["x-deprecation-owner"] = default_owner
                fixed_count += 1
    
    if fixed_count > 0:
        with open(spec_path, "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")
    
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
            print(f"\n❌ {layer_file}:")
            
            for path, method, missing in results["incomplete_endpoints"]:
                print(f"  - {method} {path}: missing {', '.join(missing)}")
            
            for schema_name, missing in results["incomplete_schemas"]:
                print(f"  - schema/{schema_name}: missing {', '.join(missing)}")
            
            if args.fix:
                fixed = fix_deprecation_markers(spec_path, args.owner)
                total_fixed += fixed
                print(f"  ✅ Fixed {fixed} items")
        else:
            if results["total_deprecated"] > 0:
                print(f"✅ {layer_file}: All {results['total_deprecated']} deprecated items have complete metadata")
            else:
                print(f"✅ {layer_file}: No deprecated items")
    
    if args.check:
        if total_issues > 0:
            print(f"\n❌ Found {total_issues} incomplete deprecation markers")
            exit(1)
        else:
            print("\n✅ All deprecation markers are complete")
            exit(0)
    
    if args.fix:
        if total_fixed > 0:
            print(f"\n✅ Fixed {total_fixed} deprecation markers across all layers")
            print("⚠️  Please review the changes and set appropriate removal dates")
            exit(0)
        else:
            print("\n✅ No fixes needed")
            exit(0)


if __name__ == "__main__":
    main()
