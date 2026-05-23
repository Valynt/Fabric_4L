#!/usr/bin/env python3
"""Sync deprecation register with OpenAPI spec deprecation markers.

This script extracts deprecation information from all OpenAPI specs and
updates the central deprecation register at contracts/deprecations/generated-contract-deprecations.json.

Usage:
    python scripts/ci/sync_deprecation_register.py --check
    python scripts/ci/sync_deprecation_register.py --update
"""

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


def extract_deprecations_from_spec(spec_path: Path) -> list[dict[str, Any]]:
    """Extract all deprecation entries from an OpenAPI spec."""
    with open(spec_path) as f:
        spec = json.load(f)
    
    deprecations = []
    
    # Extract endpoint deprecations
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            if operation.get("deprecated", False):
                deprecation = {
                    "key": f"{method.upper()} {path}",
                    "type": "endpoint",
                    "path": path,
                    "method": method.upper(),
                    "introduction_version": operation.get("x-deprecated-since", "unknown"),
                    "removal_target": operation.get("x-deprecated-removal-date", "unknown"),
                    "replacement": operation.get("x-deprecation-replacement", "none"),
                    "owner": operation.get("x-deprecation-owner", "unknown"),
                    "description": operation.get("description", ""),
                }
                deprecations.append(deprecation)
    
    # Extract schema deprecations
    for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
        if schema.get("deprecated", False):
            deprecation = {
                "key": f"schema/{schema_name}",
                "type": "schema",
                "path": f"components/schemas/{schema_name}",
                "method": "N/A",
                "introduction_version": schema.get("x-deprecated-since", "unknown"),
                "removal_target": schema.get("x-deprecated-removal-date", "unknown"),
                "replacement": schema.get("x-deprecation-replacement", "none"),
                "owner": schema.get("x-deprecation-owner", "unknown"),
                "description": schema.get("description", ""),
            }
            deprecations.append(deprecation)
    
    return deprecations


def load_deprecation_register() -> dict[str, Any]:
    """Load the current deprecation register."""
    register_path = Path(__file__).parent.parent.parent / "contracts" / "deprecations" / "generated-contract-deprecations.json"
    
    if not register_path.exists():
        return {
            "schema_version": "1.0",
            "current_contract_version": "v2.4",
            "entries": [],
        }
    
    with open(register_path) as f:
        return json.load(f)


def save_deprecation_register(register: dict[str, Any]) -> None:
    """Save the deprecation register."""
    register_path = Path(__file__).parent.parent.parent / "contracts" / "deprecations" / "generated-contract-deprecations.json"
    register_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(register_path, "w") as f:
        json.dump(register, f, indent=2)
        f.write("\n")


def sync_deprecation_register(register: dict[str, Any], all_deprecations: list[dict[str, Any]]) -> dict[str, Any]:
    """Sync the deprecation register with extracted deprecations."""
    existing_keys = {entry["key"] for entry in register.get("entries", [])}
    new_keys = {dep["key"] for dep in all_deprecations}
    
    # Add new deprecations
    for dep in all_deprecations:
        if dep["key"] not in existing_keys:
            register["entries"].append(dep)
    
    # Remove deprecations that are no longer in OpenAPI specs
    # (unless they have a specific removal date in the past or version target)
    now = datetime.now(UTC)
    register["entries"] = [
        entry for entry in register["entries"]
        if entry["key"] in new_keys or (
            entry.get("removal_target") != "unknown" and
            (
                # Handle version strings (e.g., "v2.5")
                entry.get("removal_target", "").startswith("v") or
                # Handle ISO date strings
                (
                    not entry.get("removal_target", "").startswith("v") and
                    datetime.fromisoformat(entry["removal_target"]) > now
                )
            )
        )
    ]
    
    # Update current contract version
    register["current_contract_version"] = "v2.4"
    register["last_synced"] = now.isoformat()
    
    return register


def main():
    parser = argparse.ArgumentParser(description="Sync deprecation register with OpenAPI specs")
    parser.add_argument("--check", action="store_true", help="Check if register is in sync")
    parser.add_argument("--update", action="store_true", help="Update the register")
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
    
    all_deprecations = []
    
    for layer_file in layers:
        spec_path = contracts_dir / layer_file
        if not spec_path.exists():
            print(f"⚠️  {layer_file} not found, skipping")
            continue
        
        deprecations = extract_deprecations_from_spec(spec_path)
        all_deprecations.extend(deprecations)
        print(f"✅ {layer_file}: {len(deprecations)} deprecations found")
    
    register = load_deprecation_register()
    
    if args.check:
        existing_keys = {entry["key"] for entry in register.get("entries", [])}
        new_keys = {dep["key"] for dep in all_deprecations}
        
        missing_in_register = new_keys - existing_keys
        obsolete_in_register = existing_keys - new_keys
        
        if missing_in_register or obsolete_in_register:
            print(f"\n❌ Deprecation register is out of sync:")
            if missing_in_register:
                print(f"  - {len(missing_in_register)} deprecations in OpenAPI but not in register")
                for key in list(missing_in_register)[:5]:
                    print(f"    {key}")
                if len(missing_in_register) > 5:
                    print(f"    ... and {len(missing_in_register) - 5} more")
            if obsolete_in_register:
                print(f"  - {len(obsolete_in_register)} deprecations in register but not in OpenAPI")
                for key in list(obsolete_in_register)[:5]:
                    print(f"    {key}")
                if len(obsolete_in_register) > 5:
                    print(f"    ... and {len(obsolete_in_register) - 5} more")
            exit(1)
        else:
            print(f"\n✅ Deprecation register is in sync ({len(all_deprecations)} deprecations)")
            exit(0)
    
    if args.update:
        updated_register = sync_deprecation_register(register, all_deprecations)
        save_deprecation_register(updated_register)
        print(f"\n✅ Updated deprecation register with {len(all_deprecations)} deprecations")
        exit(0)


if __name__ == "__main__":
    main()
