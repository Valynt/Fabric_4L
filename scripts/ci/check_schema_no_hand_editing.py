#!/usr/bin/env python3
"""
CI gate: detect hand-editing of generated schemas without corresponding source change.

For every schema record with authoring_direction == CODE_FIRST_WITH_GENERATED_SCHEMA,
this script compares the last-modified time (or git commit) of the schema artifact
against its declared source_of_truth. If the artifact is newer than the source,
it is flagged as a potential unregenerated hand-edit.

In CI, this relies on git history. In local dev, it relies on file mtimes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "packages" / "platform-contract" / "src" / "python"))

from schema_registry.loader import RegistryLoader
from schema_registry.models import AuthoringDirection


def _git_last_commit_time(path: Path, repo_root: Path) -> int | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return None


def _file_mtime(path: Path) -> int | None:
    try:
        return int(os.path.getmtime(path))
    except OSError:
        return None


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

    errors: list[str] = []
    warnings: list[str] = []

    for record in catalog.schemas:
        if record.authoring_direction != AuthoringDirection.CODE_FIRST_WITH_GENERATED_SCHEMA:
            continue
        if not record.source_of_truth:
            warnings.append(f"No source_of_truth for CODE_FIRST schema {record.key()}; skipping.")
            continue

        artifact_path = repo_root / record.artifact
        source_path = repo_root / record.source_of_truth

        if not artifact_path.exists():
            errors.append(f"Generated artifact missing for {record.key()}: {artifact_path}")
            continue
        if not source_path.exists():
            warnings.append(f"Source of truth missing for {record.key()}: {source_path}")
            continue

        # Try git commit times first; fall back to mtime
        artifact_time = _git_last_commit_time(artifact_path, repo_root) or _file_mtime(artifact_path)
        source_time = _git_last_commit_time(source_path, repo_root) or _file_mtime(source_path)

        if artifact_time is None or source_time is None:
            warnings.append(f"Could not compare times for {record.key()}; skipping hand-edit check.")
            continue

        if artifact_time > source_time:
            errors.append(
                f"Artifact {record.artifact} appears newer than source {record.source_of_truth} "
                f"for {record.key()}. Possible unregenerated hand-edit. Regenerate from source and re-commit."
            )

    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[FAIL] {e}")

    if errors:
        print(f"\nHand-editing check FAILED with {len(errors)} violation(s).")
        return 1

    print("Hand-editing check PASSED.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema No-Hand-Editing Gate")
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    return run(args.registry, args.policy, args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
