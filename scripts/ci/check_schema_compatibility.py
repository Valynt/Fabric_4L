#!/usr/bin/env python3
"""
CI gate: check compatibility of changed schemas against their latest PUBLISHED version.

This script expects to be run in a CI context where changed files are known.
It loads the registry, finds the previous published version of any changed schema,
and runs the additive-within-major compatibility checker.

Exit 0 if no violations, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "packages" / "platform-contract" / "src" / "python"))

from schema_registry.loader import RegistryLoader
from schema_registry.compatibility import CompatibilityChecker
from schema_registry.models import LifecycleStatus


def _detect_changed_artifacts(repo_root: Path, changed_paths: list[Path]) -> dict[str, Path]:
    """Map schema_id -> changed artifact path for files under contracts/jsonschema/."""
    mapping: dict[str, Path] = {}
    for p in changed_paths:
        if str(p).startswith(str(repo_root / "contracts" / "jsonschema")):
            # Try to resolve schema_id from registry later; just collect candidates
            mapping[p.name] = p
    return mapping


def run(
    changed_files: list[str] | None = None,
    registry_path: Path | None = None,
    policy_path: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    loader = RegistryLoader(registry_path, policy_path, repo_root)
    repo_root = loader.repo_root

    if changed_files is None:
        # Accept space-separated list from env var or git diff
        changed_raw = os.environ.get("CHANGED_SCHEMA_FILES", "").strip()
        if changed_raw:
            changed_files = changed_raw.split()
        else:
            print("[SKIP] No changed schema files provided (set CHANGED_SCHEMA_FILES or --changed-files).")
            return 0

    changed_paths = [Path(f) for f in changed_files]

    try:
        catalog = loader.load_catalog()
    except Exception as exc:
        print(f"[FAIL] Cannot load registry: {exc}")
        return 1

    checker = CompatibilityChecker(policy_doc=catalog.policies)
    errors: list[str] = []

    # For each changed artifact, find the matching schema record and its previous published version
    for record in catalog.schemas:
        artifact_path = repo_root / record.artifact
        if str(artifact_path) not in [str(p.resolve()) for p in changed_paths]:
            continue
        # Only check PUBLISHED or DEPRECATED schemas (already committed)
        if record.status not in (LifecycleStatus.PUBLISHED, LifecycleStatus.DEPRECATED):
            continue
        # Find previous published version
        previous = None
        candidates = [
            s
            for s in catalog.schemas
            if s.schema_id == record.schema_id
            and s.status == LifecycleStatus.PUBLISHED
            and s.version != record.version
        ]
        if candidates:
            # Semver sort descending
            previous = max(candidates, key=lambda s: tuple(int(x) for x in s.version.split(".")))

        if previous is None:
            print(f"[INFO] No previous PUBLISHED version for {record.key()}; skipping compatibility check.")
            continue

        try:
            old_schema = loader.load_artifact(previous)
            new_schema = loader.load_artifact(record)
        except Exception as exc:
            errors.append(f"Cannot load artifacts for {record.key()}: {exc}")
            continue

        result = checker.check(previous, record, old_schema, new_schema)
        if not result.ok():
            errors.append(f"Compatibility violations for {record.key()} vs {previous.key()}:")
            for err in result.errors:
                errors.append(f"  - {err}")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        print(f"\nSchema compatibility check FAILED with {len(errors)} violation(s).")
        return 1

    print("Schema compatibility check PASSED.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema Compatibility Gate")
    parser.add_argument("--changed-files", nargs="*", default=None, help="List of changed artifact paths")
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    return run(args.changed_files, args.registry, args.policy, args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
