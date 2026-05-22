"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Shared utilities for API routes.

Common helpers for validation, parsing, and formatting.
"""

import re

from fastapi import HTTPException

from ...auth.api_keys import APIKey


def get_tenant_id_from_api_key(api_key: APIKey) -> str:
    """Resolve tenant ID from authenticated API-key metadata; fail closed if absent.

    Single source of truth for API-key tenant extraction across L3 routes.

    Raises HTTPException(401) for any of: missing metadata attr, non-dict metadata,
    None metadata, missing tenant_id key, non-string tenant_id, empty string, or
    whitespace-only tenant_id.
    """
    raw = getattr(api_key, "metadata", None)
    metadata = raw if isinstance(raw, dict) else {}
    raw_tenant_id = metadata.get("tenant_id")
    if not isinstance(raw_tenant_id, str):
        raise HTTPException(status_code=401, detail="Invalid tenant context")
    tenant_id = raw_tenant_id.strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid tenant context")
    return tenant_id


def parse_semver(version: str) -> tuple[int, int, int, str | None, str | None]:
    """Parse semver string into components.

    Returns: (major, minor, patch, prerelease, build_metadata)
    Handles: 1.2.3, 1.2.3-beta, 1.2.3+build, 1.2.3-beta+build
    """
    # Remove build metadata first
    build = None
    if "+" in version:
        version, build = version.rsplit("+", 1)

    # Extract prerelease
    prerelease = None
    if "-" in version:
        version, prerelease = version.split("-", 1)

    # Parse core version
    parts = version.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        return (0, 0, 0, prerelease, build)

    return (major, minor, patch, prerelease, build)


def semver_key(version: str) -> tuple[int, int, int]:
    """Convert semver to sortable tuple (ignores prerelease/build).

    Invalid versions sort to (0, 0, 0).
    """
    major, minor, patch, _, _ = parse_semver(version)
    return (major, minor, patch)


def is_valid_semver(version: str) -> bool:
    """Validate semver format (X.Y.Z[-prerelease][+build])."""
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?$"
    return bool(re.match(pattern, version))


def increment_patch_version(version: str) -> str:
    """Increment patch version, preserving prerelease/build format.

    Examples:
        1.2.3 -> 1.2.4
        1.2.3-beta -> 1.2.4-beta
        1.0 -> 1.0.1 (handles partial versions)
    """
    major, minor, patch, prerelease, build = parse_semver(version)

    # Construct new version
    new_version = f"{major}.{minor}.{patch + 1}"
    if prerelease:
        new_version += f"-{prerelease}"
    if build:
        new_version += f"+{build}"

    return new_version
