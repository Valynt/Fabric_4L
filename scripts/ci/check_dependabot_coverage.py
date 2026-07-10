#!/usr/bin/env python3
"""Validate that every active package manifest and Dockerfile has a Dependabot entry.

Exits non-zero and prints a report if any manifest or Dockerfile directory is
not covered by .github/dependabot.yml.

Usage:
    python scripts/ci/check_dependabot_coverage.py
    python scripts/ci/check_dependabot_coverage.py --root /path/to/repo
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Directories to exclude from discovery.
#
# Add a directory here when it intentionally has no Dependabot entry:
#   - Legacy/obsolete roots (services, frontend) — canonical structure
#   - Test fixture files (tests/) — requirements.txt there is a test helper,
#     not a deployable package; its deps are covered by the service entries
#   - Generated/tooling dirs — devcontainer, prototypes, archive
# ---------------------------------------------------------------------------
EXCLUDE_DIRS = frozenset(
    [
        ".git",
        ".tmp",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        # Legacy / obsolete roots — canonical structure
        "value-fabric",
        "frontend",
        "archive",
        "prototypes",
        # Devcontainer — base image managed separately from application images
        ".devcontainer",
        # Test fixture requirements — not a deployable package
        "tests",
    ]
)

# Manifest filenames that indicate a pip-managed directory
PIP_MANIFESTS = {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"}

# Manifest filenames that indicate an npm-managed directory
NPM_MANIFESTS = {"package.json"}

# package.json files under these directories are build outputs rather than package roots.
NPM_SKIP_PARENTS = {"dist", "build", ".next", "coverage", "out"}


def _repo_directory(path: Path, root: Path) -> str:
    """Return Dependabot's leading-slash directory form for a repo path."""
    rel = path.relative_to(root).as_posix()
    return f"/{rel}" if rel != "." else "/"


def discover_manifest_dirs(root: Path) -> tuple[set[str], set[str], set[str]]:
    """Return pip, npm, and docker manifest directories using one pruned walk.

    The previous implementation performed separate recursive glob traversals for
    pip manifests, npm manifests, and Dockerfiles. A single ``os.walk`` with
    in-place directory pruning avoids revisiting the same large subtrees while
    preserving the same exclusion rules.
    """
    pip_dirs: set[str] = set()
    npm_dirs: set[str] = set()
    docker_dirs: set[str] = set()

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [directory for directory in dirs if directory not in EXCLUDE_DIRS]
        current_path = Path(current_root)
        parts = set(current_path.relative_to(root).parts)
        file_names = set(files)

        if file_names & PIP_MANIFESTS:
            pip_dirs.add(_repo_directory(current_path, root))

        if file_names & NPM_MANIFESTS and not (parts & NPM_SKIP_PARENTS):
            npm_dirs.add(_repo_directory(current_path, root))

        if any(name == "Dockerfile" or name.startswith("Dockerfile.") for name in files):
            docker_dirs.add(_repo_directory(current_path, root))

    return pip_dirs, npm_dirs, docker_dirs


def discover_pip_dirs(root: Path) -> set[str]:
    """Return repo-relative directory paths that contain a pip manifest."""
    return discover_manifest_dirs(root)[0]


def discover_npm_dirs(root: Path) -> set[str]:
    """Return repo-relative directory paths that contain a package.json."""
    return discover_manifest_dirs(root)[1]


def discover_docker_dirs(root: Path) -> set[str]:
    """Return repo-relative directory paths that contain a Dockerfile."""
    return discover_manifest_dirs(root)[2]


def load_dependabot_entries(dependabot_path: Path) -> dict[str, set[str]]:
    """Parse dependabot.yml and return {ecosystem: {directory, ...}}."""
    data = yaml.safe_load(dependabot_path.read_text()) or {}
    covered: dict[str, set[str]] = {}
    for entry in data.get("updates", []):
        ecosystem = entry.get("package-ecosystem", "")
        directory = entry.get("directory", "")
        covered.setdefault(ecosystem, set()).add(directory)
    return covered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=None,
        help="Repository root (default: two levels above this script)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    dependabot_path = root / ".github" / "dependabot.yml"

    if not dependabot_path.exists():
        print(f"ERROR: {dependabot_path} not found", file=sys.stderr)
        return 1

    covered = load_dependabot_entries(dependabot_path)
    pip_covered = covered.get("pip", set())
    npm_covered = covered.get("npm", set())
    docker_covered = covered.get("docker", set())

    pip_dirs, npm_dirs, docker_dirs = discover_manifest_dirs(root)

    missing_pip = sorted(pip_dirs - pip_covered)
    missing_npm = sorted(npm_dirs - npm_covered)
    missing_docker = sorted(docker_dirs - docker_covered)

    # Report
    ok = True

    if missing_pip:
        ok = False
        print("pip manifests with no Dependabot entry:")
        for d in missing_pip:
            print(f"  {d}  (add pip entry for directory: {d})")

    if missing_npm:
        ok = False
        print("npm manifests with no Dependabot entry:")
        for d in missing_npm:
            print(f"  {d}  (add npm entry for directory: {d})")

    if missing_docker:
        ok = False
        print("Dockerfile directories with no Dependabot entry:")
        for d in missing_docker:
            print(f"  {d}  (add docker entry for directory: {d})")

    if ok:
        total = len(pip_dirs) + len(npm_dirs) + len(docker_dirs)
        print(
            f"dependabot coverage OK — {len(pip_dirs)} pip, "
            f"{len(npm_dirs)} npm, {len(docker_dirs)} docker "
            f"({total} total manifest locations covered)"
        )
        return 0

    print(
        "\nUpdate .github/dependabot.yml to add the missing entries above.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
