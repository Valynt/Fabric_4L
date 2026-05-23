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

# Contract version for the deprecation register
CURRENT_CONTRACT_VERSION = "v2.4"

# HTTP methods to check for deprecation
HTTP_METHODS = ["get", "post", "put", "delete", "patch"]

# Default deprecation register structure
DEFAULT_REGISTER = {
    "schema_version": "1.0",
    "current_contract_version": CURRENT_CONTRACT_VERSION,
    "entries": [],
}

# OpenAPI spec files to process
LAYER_SPECS = [
    "layer1-ingestion.json",
    "layer2-extraction.json",
    "layer3-knowledge.json",
    "layer4-agents.json",
    "layer5-ground-truth.json",
    "layer6-benchmarks.json",
]

# Placeholder value for missing metadata
UNKNOWN_VALUE = "unknown"


def is_version_string(value: str) -> bool:
    """Check if a value is a version string (e.g., 'v2.5') rather than a date.
    
    Version strings start with 'v' followed by digits and optional dots.
    """
    if not value.startswith("v"):
        return False
    # Remove 'v' and check if remaining chars are digits/dots
    version_part = value[1:]
    if not version_part:
        return False
    return version_part.replace(".", "").isdigit()


def is_field_level_deprecation(key: str) -> bool:
    """Check if a deprecation key is for a field (not endpoint or schema).
    
    Field-level deprecations are manually curated and contain '.properties.' in the key.
    """
    return ".properties." in key


def is_removal_target_valid(entry: dict[str, Any], now: datetime) -> bool:
    """Check if a removal target is still valid (not yet reached).
    
    Version strings (e.g., 'v2.5') are always considered valid since removal
    happens when that version is released. Date strings are checked against
    the current time.
    """
    removal_target = entry.get("removal_target", UNKNOWN_VALUE)
    
    if removal_target == UNKNOWN_VALUE:
        return False
    
    # Version strings are always considered valid (removed when version is released)
    if is_version_string(removal_target):
        return True
    
    # Date strings: check if date is in the future
    try:
        return datetime.fromisoformat(removal_target) > now
    except ValueError:
        # Invalid date format, treat as invalid
        return False


def extract_deprecations_from_spec(spec_path: Path) -> list[dict[str, Any]]:
    """Extract all deprecation entries from an OpenAPI spec.
    
    Returns empty list if spec cannot be read.
    """
    try:
        with open(spec_path) as f:
            spec = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {spec_path}: {e}")
        return []
    
    deprecations = []
    
    # Extract endpoint deprecations
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            
            if operation.get("deprecated", False):
                deprecation = {
                    "key": f"{method.upper()} {path}",
                    "type": "endpoint",
                    "path": path,
                    "method": method.upper(),
                    "introduction_version": operation.get("x-deprecated-since", UNKNOWN_VALUE),
                    "removal_target": operation.get("x-deprecated-removal-date", UNKNOWN_VALUE),
                    "replacement": operation.get("x-deprecation-replacement", "none"),
                    "owner": operation.get("x-deprecation-owner", UNKNOWN_VALUE),
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
                "introduction_version": schema.get("x-deprecated-since", UNKNOWN_VALUE),
                "removal_target": schema.get("x-deprecated-removal-date", UNKNOWN_VALUE),
                "replacement": schema.get("x-deprecation-replacement", "none"),
                "owner": schema.get("x-deprecation-owner", UNKNOWN_VALUE),
                "description": schema.get("description", ""),
            }
            deprecations.append(deprecation)
    
    return deprecations


def load_deprecation_register() -> dict[str, Any]:
    """Load the current deprecation register.
    
    Returns default structure if file does not exist or cannot be read.
    """
    register_path = Path(__file__).parent.parent.parent / "contracts" / "deprecations" / "generated-contract-deprecations.json"
    
    if not register_path.exists():
        return DEFAULT_REGISTER.copy()
    
    try:
        with open(register_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading deprecation register: {e}")
        return DEFAULT_REGISTER.copy()


def save_deprecation_register(register: dict[str, Any]) -> bool:
    """Save the deprecation register.
    
    Returns True if successful, False otherwise.
    """
    register_path = Path(__file__).parent.parent.parent / "contracts" / "deprecations" / "generated-contract-deprecations.json"
    register_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(register_path, "w") as f:
            json.dump(register, f, indent=2)
            f.write("\n")
        return True
    except IOError as e:
        print(f"Error writing deprecation register: {e}")
        return False


def sync_deprecation_register(register: dict[str, Any], all_deprecations: list[dict[str, Any]]) -> dict[str, Any]:
    """Sync the deprecation register with extracted deprecations."""
    existing_keys = {entry["key"] for entry in register.get("entries", [])}
    new_keys = {dep["key"] for dep in all_deprecations}
    
    # Add new deprecations
    for dep in all_deprecations:
        if dep["key"] not in existing_keys:
            register["entries"].append(dep)
    
    # Remove deprecations that are no longer in OpenAPI specs
    # (unless they have a valid removal target that hasn't been reached yet)
    # Field-level deprecations are manually managed and should be preserved
    now = datetime.now(UTC)
    register["entries"] = [
        entry for entry in register["entries"]
        if entry["key"] in new_keys or is_field_level_deprecation(entry["key"]) or is_removal_target_valid(entry, now)
    ]
    
    # Update current contract version
    register["current_contract_version"] = CURRENT_CONTRACT_VERSION
    register["last_synced"] = now.isoformat()
    
    return register


def main() -> None:
    """Main entry point for the deprecation register sync script."""
    parser = argparse.ArgumentParser(description="Sync deprecation register with OpenAPI specs")
    parser.add_argument("--check", action="store_true", help="Check if register is in sync")
    parser.add_argument("--update", action="store_true", help="Update the register")
    args = parser.parse_args()
    
    contracts_dir = Path(__file__).parent.parent.parent / "contracts" / "openapi"
    
    all_deprecations = []
    
    for layer_file in LAYER_SPECS:
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
        
        # Separate field-level deprecations (manually managed) from endpoint/schema deprecations
        existing_field_keys = {k for k in existing_keys if is_field_level_deprecation(k)}
        existing_endpoint_schema_keys = existing_keys - existing_field_keys
        new_endpoint_schema_keys = {k for k in new_keys if not is_field_level_deprecation(k)}
        
        missing_in_register = new_endpoint_schema_keys - existing_endpoint_schema_keys
        obsolete_in_register = existing_endpoint_schema_keys - new_endpoint_schema_keys
        
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
            field_count = len(existing_field_keys)
            endpoint_count = len(new_endpoint_schema_keys)
            print(f"\n✅ Deprecation register is in sync ({endpoint_count} endpoint/schema deprecations, {field_count} field-level deprecations)")
            exit(0)
    
    if args.update:
        updated_register = sync_deprecation_register(register, all_deprecations)
        if save_deprecation_register(updated_register):
            print(f"\n✅ Updated deprecation register with {len(all_deprecations)} deprecations")
            exit(0)
        else:
            print("\n❌ Failed to update deprecation register")
            exit(1)


if __name__ == "__main__":
    main()
