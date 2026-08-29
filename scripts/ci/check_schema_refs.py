#!/usr/bin/env python3
"""
CI gate: verify all $ref values in published schema artifacts resolve within the registry bundle.

This script loads every PUBLISHED schema artifact, collects $refs, and ensures each
ref is either:
- A canonical $id present in another published schema artifact, or
- A well-known external reference explicitly allowed by policy.

External refs are forbidden by default for PUBLISHED schemas to guarantee reproducible bundles.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "packages" / "platform-contract" / "src" / "python"))

from schema_registry.bundler import _collect_refs
from schema_registry.loader import RegistryLoader
from schema_registry.models import LifecycleStatus


# Allowlist for external refs that are standard/meta schemas.
EXTERNAL_REF_ALLOWLIST = {
    "https://json-schema.org/draft/2020-12/schema",
    "https://json-schema.org/draft/2019-09/schema",
    "https://json-schema.org/draft-07/schema",
}


def run(
    registry_path: Path | None = None,
    policy_path: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    loader = RegistryLoader(registry_path, policy_path, repo_root)
    repo_root = loader.repo_root

    try:
        catalog = loader.load_catalog()
    except Exception as exc:
        print(f"[FAIL] Cannot load registry: {exc}")
        return 1

    # Build set of all published $ids
    published_ids: set[str] = set()
    for record in catalog.schemas:
        if record.status == LifecycleStatus.PUBLISHED:
            try:
                artifact = loader.load_artifact(record)
            except FileNotFoundError:
                continue
            schema_id = artifact.get("$id")
            if schema_id:
                published_ids.add(schema_id)

    errors: list[str] = []

    for record in catalog.schemas:
        if record.status != LifecycleStatus.PUBLISHED:
            continue
        try:
            artifact = loader.load_artifact(record)
        except FileNotFoundError:
            errors.append(f"Artifact missing for published schema {record.key()}")
            continue
        refs = _collect_refs(artifact)
        for ref in refs:
            if ref in EXTERNAL_REF_ALLOWLIST:
                continue
            if ref in published_ids:
                continue
            # If ref is a relative path within repo, also allow if it resolves to a published artifact
            # Heuristic: if ref starts with ./ or ../, resolve it
            if ref.startswith("./") or ref.startswith("../"):
                resolved = (repo_root / record.artifact).parent / ref
                try:
                    if resolved.resolve().exists():
                        continue
                except OSError:
                    pass
            errors.append(f"Unresolved $ref in {record.key()}: {ref}")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        print(f"\nSchema $ref check FAILED with {len(errors)} unresolved reference(s).")
        return 1

    print("Schema $ref check PASSED.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema $ref Resolution Gate")
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    return run(args.registry, args.policy, args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
