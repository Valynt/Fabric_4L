#!/usr/bin/env python3
"""
Validate Dependabot Coverage (H-07 Audit Fix)

Ensures every package manifest and Dockerfile has:
1. A corresponding entry in dependabot.yml
2. An owner defined in CODEOWNERS
3. No stale Dependabot entry pointing at a missing or non-manifest directory
4. Dependabot reviewers align with CODEOWNERS owners for the same path
5. CODEOWNERS directory patterns resolve to existing directories

Exit codes:
    0 - All packages have coverage
    1 - Missing dependabot entries, stale dependabot entries, ownership drift,
        or stale CODEOWNERS paths
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# File patterns that indicate a package needs dependabot coverage
PACKAGE_PATTERNS = {
    "pip": ["pyproject.toml", "requirements.txt", "setup.py"],
    "npm": ["package.json"],
    "docker": ["Dockerfile", "Dockerfile.*"],
}

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".tmp",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    ".tox",
    "archive",
    "dist",
    "build",
    ".next",
    "*.egg-info",
    "prototypes",  # Prototypes are temporary/experimental and don't need automated updates
    ".worktrees",  # Git worktrees are not part of the canonical source tree
    ".codex-worktrees",  # Codex-linked worktrees are not part of the canonical source tree
}


def load_dependabot_config() -> Dict:
    """Load and parse dependabot.yml configuration."""
    config_path = REPO_ROOT / ".github" / "dependabot.yml"
    if not config_path.exists():
        print(f"::error::dependabot.yml not found at {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_codeowners() -> str:
    """Load CODEOWNERS file content."""
    codeowners_path = REPO_ROOT / ".github" / "CODEOWNERS"
    if not codeowners_path.exists():
        print(f"::error::CODEOWNERS not found at {codeowners_path}")
        sys.exit(1)

    with open(codeowners_path, "r") as f:
        return f.read()


def normalize_path(path: str) -> str:
    """Normalize path to use forward slashes with ``.`` representing the repo root."""
    normalized = path.replace("\\", "/").strip("/")
    return normalized or "."


def _pattern_matches_path(pattern: str, path_str: str) -> bool:
    """Return True if a normalized CODEOWNERS pattern matches the given path."""
    if pattern.endswith("/"):
        prefix = pattern.rstrip("/")
        return path_str == prefix or path_str.startswith(prefix + "/")
    if pattern == "*":
        return True
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        return path_str.endswith(suffix) or suffix in path_str
    if pattern in path_str:
        return True
    return False


def _dependabot_updates(config):
    """Return the updates list whether the YAML root is a dict or a list."""
    if isinstance(config, list):
        return config
    if isinstance(config, dict):
        return config.get("updates", []) or []
    return []


def get_dependabot_entries(config: Dict) -> Dict[str, Set[str]]:
    """
    Extract dependabot entries by ecosystem.
    Returns: {ecosystem: set_of_directories}
    """
    entries = {"pip": set(), "npm": set(), "docker": set(), "github-actions": set()}

    for update in _dependabot_updates(config):
        ecosystem = update.get("package-ecosystem")
        directory = update.get("directory", "")

        if ecosystem in entries:
            # Normalize directory path (remove leading slash, ensure consistent format)
            normalized = normalize_path(directory)
            entries[ecosystem].add(normalized)

    return entries


def get_dependabot_entries_with_reviewers(config: Dict) -> List[Tuple[str, str, List[str]]]:
    """
    Extract dependabot entries with their reviewers.
    Returns: [(ecosystem, directory, reviewers), ...]
    """
    entries: List[Tuple[str, str, List[str]]] = []
    for update in _dependabot_updates(config):
        ecosystem = update.get("package-ecosystem", "")
        directory = update.get("directory", "")
        reviewers = update.get("reviewers", [])
        entries.append((ecosystem, normalize_path(directory), reviewers))
    return entries


def parse_codeowners_patterns(codeowners: str) -> List[Tuple[str, List[str]]]:
    """
    Parse CODEOWNERS into a list of (pattern, owners) tuples.
    Skips comments and empty lines.
    """
    patterns: List[Tuple[str, List[str]]] = []
    for line in codeowners.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern = parts[0].lstrip("/")
        owners = parts[1:]
        patterns.append((pattern, owners))
    return patterns


def get_codeowners_owners_for_path(patterns: List[Tuple[str, List[str]]], path_str: str) -> Set[str]:
    """
    Return all CODEOWNERS owners whose patterns match the given path.
    """
    owners: Set[str] = set()
    for pattern, pattern_owners in patterns:
        if _pattern_matches_path(pattern, path_str):
            owners.update(pattern_owners)
    return owners


def get_reviewer_owner_lookup_paths(ecosystem: str, directory: str) -> List[str]:
    """Return CODEOWNERS paths that represent a Dependabot entry."""
    if ecosystem == "npm":
        manifest = "package.json"
    elif ecosystem == "pip":
        manifest = "pyproject.toml"
    elif ecosystem == "docker":
        manifest = "Dockerfile"
    elif ecosystem == "github-actions":
        manifest = "workflows"
    else:
        return [directory]

    if directory == ".":
        return [directory, manifest]

    return [directory, f"{directory}/{manifest}"]


def validate_reviewer_ownership(
    dependabot_entries: List[Tuple[str, str, List[str]]],
    codeowners_patterns: List[Tuple[str, List[str]]],
) -> List[str]:
    """
    Validate that every dependabot entry has at least one reviewer
    that is also a CODEOWNERS owner for the same path.
    """
    mismatches: List[str] = []
    for ecosystem, directory, reviewers in dependabot_entries:
        # Normalize reviewers to bare team names (strip @ if present)
        normalized_reviewers = {r.lstrip("@") for r in reviewers}
        owners: Set[str] = set()
        for lookup_path in get_reviewer_owner_lookup_paths(ecosystem, directory):
            owners.update(get_codeowners_owners_for_path(codeowners_patterns, lookup_path))
        normalized_owners = {o.lstrip("@") for o in owners}
        if not normalized_reviewers & normalized_owners:
            mismatches.append(
                f"{ecosystem}: {directory or '/'} (reviewers {reviewers} do not match CODEOWNERS owners {sorted(owners)})"
            )
    return mismatches


def validate_codeowners_paths_exist(codeowners: str) -> List[str]:
    """
    Validate that non-glob CODEOWNERS directory patterns (ending with /)
    resolve to existing directories in the repository.
    """
    stale: List[str] = []
    for line in codeowners.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern = parts[0]
        # Skip wildcard/glob patterns and file patterns
        if "*" in pattern or "?" in pattern or not pattern.endswith("/"):
            continue
        path_str = pattern.lstrip("/").rstrip("/")
        if path_str and not (REPO_ROOT / path_str).is_dir():
            stale.append(f"CODEOWNERS: {pattern} (directory does not exist)")
    return stale


def entry_path_exists(path_str: str) -> bool:
    """Return True when a normalized Dependabot directory exists in the repository."""
    if path_str in {"", "."}:
        return REPO_ROOT.exists()

    return (REPO_ROOT / path_str).is_dir()


def validate_stale_dependabot_entries(
    packages: Dict[str, Set[Path]], dependabot_entries: Dict[str, Set[str]]
) -> List[str]:
    """
    Validate that Dependabot entries target real, active package directories.

    A directory can exist but still be stale for a specific ecosystem when it no
    longer contains that ecosystem's manifest, so pip/npm/docker entries are
    checked against discovered package locations rather than filesystem
    existence alone. The GitHub Actions ecosystem is directory-scoped and is
    therefore validated by directory existence.
    """
    stale_entries: List[str] = []

    for ecosystem, dirs in dependabot_entries.items():
        if ecosystem == "github-actions":
            for path_str in sorted(dirs):
                if not entry_path_exists(path_str):
                    stale_entries.append(f"{ecosystem}: {path_str or '/'} (directory does not exist)")
            continue

        active_dirs = {normalize_path(str(path)) for path in packages.get(ecosystem, set())}
        for path_str in sorted(dirs):
            if not entry_path_exists(path_str):
                stale_entries.append(f"{ecosystem}: {path_str or '/'} (directory does not exist)")
            elif path_str not in active_dirs:
                stale_entries.append(f"{ecosystem}: {path_str or '/'} (no active {ecosystem} manifest found)")

    return stale_entries


def discover_packages(repo_root: Path | None = None) -> Dict[str, Set[Path]]:
    """
    Discover all packages in the repository by ecosystem.
    Returns: {ecosystem: set_of_package_paths}
    """
    root = repo_root or REPO_ROOT
    packages = {"pip": set(), "npm": set(), "docker": set()}

    for root_dir, dirs, files in os.walk(root):
        # Skip excluded directories
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS and not any(d.startswith(ex.lstrip("*")) for ex in EXCLUDE_DIRS if ex.startswith("*"))
        ]

        rel_root = Path(root_dir).relative_to(root)

        # Check for Python packages
        for pattern in PACKAGE_PATTERNS["pip"]:
            if pattern in files:
                packages["pip"].add(rel_root)
                break

        # Check for Node.js packages
        for pattern in PACKAGE_PATTERNS["npm"]:
            if pattern in files:
                packages["npm"].add(rel_root)
                break

        # Check for Dockerfiles
        for file in files:
            if file == "Dockerfile" or file.startswith("Dockerfile."):
                packages["docker"].add(rel_root)
                break

    return packages


def check_codeowners_ownership(codeowners: str, path_str: str) -> bool:
    """
    Check if a package path has an owner defined in CODEOWNERS.
    """
    # Check for exact match or parent directory match
    for line in codeowners.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Parse CODEOWNERS line: pattern owners...
        parts = line.split()
        if not parts:
            continue

        pattern = parts[0]
        owners = parts[1:]

        if not owners:
            continue

        # Normalize pattern and check match
        pattern = pattern.lstrip("/")
        if _pattern_matches_path(pattern, path_str):
            return True

    return False


def validate_coverage(
    packages: Dict[str, Set[Path]], dependabot_entries: Dict[str, Set[str]], codeowners: str
) -> Tuple[List[str], List[str], List[str]]:
    """
    Validate that all packages have dependabot entries and CODEOWNERS ownership.
    Returns: (missing_dependabot, missing_ownership, stale_dependabot)
    """
    missing_dependabot = []
    missing_ownership = []

    for ecosystem, package_paths in packages.items():
        if ecosystem not in dependabot_entries:
            continue

        dependabot_dirs = dependabot_entries[ecosystem]

        for package_path in package_paths:
            path_str = normalize_path(str(package_path))

            # Check dependabot coverage
            if path_str not in dependabot_dirs:
                missing_dependabot.append(f"{ecosystem}: {path_str}")

            # Check CODEOWNERS ownership
            if not check_codeowners_ownership(codeowners, path_str):
                missing_ownership.append(f"{ecosystem}: {path_str}")

    stale_dependabot = validate_stale_dependabot_entries(packages, dependabot_entries)

    return missing_dependabot, missing_ownership, stale_dependabot


def main():
    print("[SCAN] Validating Dependabot coverage and CODEOWNERS ownership...")
    print()

    # Load configurations
    print("Loading dependabot.yml...")
    dependabot_config = load_dependabot_config()

    print("Loading CODEOWNERS...")
    codeowners = load_codeowners()

    # Extract dependabot entries
    dependabot_entries = get_dependabot_entries(dependabot_config)
    print()
    print("Dependabot configured entries:")
    for ecosystem, dirs in dependabot_entries.items():
        print(f"  {ecosystem}: {len(dirs)} entries")
        for d in sorted(dirs):
            print(f"    - {d}")

    # Discover packages
    print()
    print("Discovering packages...")
    packages = discover_packages()
    print(f"  pip packages: {len(packages['pip'])}")
    print(f"  npm packages: {len(packages['npm'])}")
    print(f"  docker packages: {len(packages['docker'])}")

    for ecosystem, paths in packages.items():
        if paths:
            print(f"\n  {ecosystem} paths:")
            for p in sorted(paths):
                print(f"    - {p}")

    # Validate coverage
    print()
    print("Validating coverage...")
    missing_dependabot, missing_ownership, stale_dependabot = validate_coverage(
        packages, dependabot_entries, codeowners
    )

    # Validate reviewer ↔ CODEOWNERS ownership alignment
    print()
    print("Validating reviewer ownership alignment...")
    codeowners_patterns = parse_codeowners_patterns(codeowners)
    dependabot_with_reviewers = get_dependabot_entries_with_reviewers(dependabot_config)
    reviewer_mismatches = validate_reviewer_ownership(dependabot_with_reviewers, codeowners_patterns)

    # Validate CODEOWNERS paths exist
    print()
    print("Validating CODEOWNERS paths exist...")
    stale_codeowners = validate_codeowners_paths_exist(codeowners)

    # Report results
    exit_code = 0

    if missing_dependabot:
        print()
        print("::error::Missing dependabot.yml entries:")
        for item in missing_dependabot:
            print(f"  [FAIL] {item}")
        exit_code = 1
    else:
        print()
        print("[PASS] All packages have dependabot.yml entries")

    if stale_dependabot:
        print()
        print("::error::Stale dependabot.yml entries:")
        for item in stale_dependabot:
            print(f"  [FAIL] {item}")
        exit_code = 1
    else:
        print()
        print("[PASS] No stale dependabot.yml entries found")

    if missing_ownership:
        print()
        print("::error::Missing CODEOWNERS ownership:")
        for item in missing_ownership:
            print(f"  [FAIL] {item}")
        exit_code = 1
    else:
        print()
        print("[PASS] All packages have CODEOWNERS ownership")

    if reviewer_mismatches:
        print()
        print("::error::Dependabot reviewer / CODEOWNERS ownership mismatches:")
        for item in reviewer_mismatches:
            print(f"  [FAIL] {item}")
        exit_code = 1
    else:
        print()
        print("[PASS] All dependabot reviewers align with CODEOWNERS owners")

    if stale_codeowners:
        print()
        print("::error::Stale CODEOWNERS directory paths:")
        for item in stale_codeowners:
            print(f"  [FAIL] {item}")
        exit_code = 1
    else:
        print()
        print("[PASS] All CODEOWNERS directory patterns exist")

    # Summary
    print()
    print("=" * 60)
    if exit_code == 0:
        print("[SUCCESS] VALIDATION PASSED")
        print("All package manifests and Dockerfiles have current update owners.")
    else:
        print("[ERROR] VALIDATION FAILED")
        print("Some packages are missing dependabot coverage, have stale dependabot entries,")
        print("lack ownership, have reviewer mismatches, or have stale CODEOWNERS paths.")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
