#!/usr/bin/env python3
"""Generate a manifest registry for dependency scanning.

This script walks the repository to find all Python and Node manifests
and outputs a JSON registry that can be used to set the matrix in the
dependency-scan workflow.
"""

import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "docs/archive",
    ".tmp",
    ".agents",
    ".claude",
    ".codex",
    ".deployments",
    ".devcontainer",
    ".gemini",
    ".githooks",
    ".github",
    ".hypothesis",
    ".jr",
    ".kimi",
    ".pytest_cache",
    ".roo",
    ".ruff_cache",
    ".semgrep",
    ".tmp",
    ".venv",
    ".windsurf",
    ".zap",
    # Also exclude the output of the script itself if it's in the repo
    "scripts/ci/generate_manifest_registry.py",
}

# Mapping from directory to service name for Python projects
PYTHON_SERVICE_MAP = {
    "services": lambda parts: parts[1] if len(parts) > 1 else None,
    "packages": lambda parts: {
        "shared": "shared",
        "platform-contract": "platform-contract",
    }.get(parts[1], None) if len(parts) > 1 else None,
    "sdk": lambda parts: "sdk" if len(parts) > 1 else None,
}

# Mapping from directory to service name for Node projects
NODE_SERVICE_MAP = {
    "apps": lambda parts: parts[1] if len(parts) > 1 else None,
    "services": lambda parts: {
        "value-studio": "value-studio",
    }.get(parts[1], None) if len(parts) > 1 else None,
    "packages": lambda parts: {
        "config": "config",
        "eslint-plugin-fabric-contracts": "eslint-plugin-fabric-contracts",
    }.get(parts[1], None) if len(parts) > 1 else None,
}


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded."""
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def find_manifests():
    """Find all Python and Node manifests."""
    python_manifests = []  # each entry: (service_name, directory)
    node_manifests = []    # each entry: (service_name, directory)

    for root, dirs, files in os.walk(REPO_ROOT):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]

        root_path = Path(root)
        if should_exclude(root_path):
            continue

        # Check for Python manifests
        pyproject = root_path / "pyproject.toml"
        setup_py = root_path / "setup.py"
        req_txt = root_path / "requirements.txt"
        # We'll consider a directory as a Python project if it has pyproject.toml or setup.py
        # and optionally a lock file (uv.lock, requirements.txt, etc.)
        if pyproject.is_file() or setup_py.is_file():
            # Determine service name
            service_name = None
            # Get the relative path from REPO_ROOT
            try:
                rel_path = root_path.relative_to(REPO_ROOT)
            except ValueError:
                # Should not happen
                continue
            parts = rel_path.parts
            if parts:
                first = parts[0]
                if first in PYTHON_SERVICE_MAP:
                    mapping = PYTHON_SERVICE_MAP[first]
                    if callable(mapping):
                        service_name = mapping(parts)
                    else:
                        service_name = mapping
            if service_name:
                python_manifests.append((service_name, str(root_path)))

        # Check for Node manifests
        package_json = root_path / "package.json"
        pnpm_lock = root_path / "pnpm-lock.yaml"
        if package_json.is_file():
            service_name = None
            try:
                rel_path = root_path.relative_to(REPO_ROOT)
            except ValueError:
                continue
            parts = rel_path.parts
            if parts:
                first = parts[0]
                if first in NODE_SERVICE_MAP:
                    mapping = NODE_SERVICE_MAP[first]
                    if callable(mapping):
                        service_name = mapping(parts)
                    else:
                        service_name = mapping
            if service_name:
                node_manifests.append((service_name, str(root_path)))

    return python_manifests, node_manifests


def main():
    python_manifests, node_manifests = find_manifests()

    # Build the registry
    registry = {
        "python": [],
        "node": [],
    }

    # Deduplicate by service name (take the first occurrence)
    seen_python = set()
    for service_name, directory in python_manifests:
        # Skip the legacy billing service
        if service_name == "billing":
            continue
        # Convert absolute path to relative
        try:
            rel_dir = os.path.relpath(directory, REPO_ROOT)
        except ValueError:
            # Should not happen
            rel_dir = directory
        if service_name not in seen_python:
            seen_python.add(service_name)
            registry["python"].append({
                "name": service_name,
                "path": rel_dir,
            })

    seen_node = set()
    for service_name, directory in node_manifests:
        # Skip the legacy billing service (though it's unlikely to appear in node)
        if service_name == "billing":
            continue
        # Convert absolute path to relative
        try:
            rel_dir = os.path.relpath(directory, REPO_ROOT)
        except ValueError:
            rel_dir = directory
        if service_name not in seen_node:
            seen_node.add(service_name)
            registry["node"].append({
                "name": service_name,
                "path": rel_dir,
            })

    # Sort by name for deterministic output
    registry["python"].sort(key=lambda x: x["name"])
    registry["node"].sort(key=lambda x: x["name"])

    # Output JSON
    json.dump(registry, sys.stdout, indent=2)
    print()  # newline


if __name__ == "__main__":
    main()