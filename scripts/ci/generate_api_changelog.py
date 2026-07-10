#!/usr/bin/env python3
"""
Fabric 4L — API Changelog Generator
====================================

Compares OpenAPI specifications between two git references (tags, branches, or
commits), detects changes (added/removed endpoints, modified schemas),
classifies them by severity, and generates a Markdown changelog.

Can optionally post the changelog as GitHub Release notes.

Usage:
    python generate_api_changelog.py --from v1.0.0 --to v1.1.0 --output CHANGELOG-API.md
    python generate_api_changelog.py --from v1.0.0 --to HEAD --github-release --repo fabric-4l/api

Exit codes:
    0 — success, no breaking changes
    1 — success, breaking changes detected
    2 — runtime error
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

FABRIC_LAYERS = ["l1-gateway", "l2-auth", "l3-core", "l4-compute", "l5-data", "l6-observability"]
OPENAPI_DIR = "contracts/openapi"
GITHUB_API_URL = "https://api.github.com"


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

class ChangeType(Enum):
    """Classification of API changes."""
    ADDED = "added"                     # New endpoint or field
    REMOVED = "removed"                 # Deleted endpoint or field
    MODIFIED = "modified"               # Changed behavior (non-breaking)
    DEPRECATED = "deprecated"           # Marked deprecated
    BREAKING = "breaking"               # Breaking change


class Severity(Enum):
    """Severity levels for display and gating."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_EMOJI = {
    Severity.NONE: "",
    Severity.LOW: "🟢",
    Severity.MEDIUM: "🟡",
    Severity.HIGH: "🟠",
    Severity.CRITICAL: "🔴",
}

CHANGE_EMOJI = {
    ChangeType.ADDED: "➕",
    ChangeType.REMOVED: "➖",
    ChangeType.MODIFIED: "📝",
    ChangeType.DEPRECATED: "⚠️",
    ChangeType.BREAKING: "🚨",
}


@dataclasses.dataclass(frozen=True)
class Change:
    """A single detected API change."""
    change_type: ChangeType
    layer: str
    path: str                # API path, e.g., "/v1/users"
    method: str | None       # HTTP method, e.g., "GET"
    description: str
    severity: Severity
    details: str = ""        # Additional context (diff, schema change, etc.)

    @property
    def emoji(self) -> str:
        return CHANGE_EMOJI.get(self.change_type, "❓")

    @property
    def severity_emoji(self) -> str:
        return SEVERITY_EMOJI.get(self.severity, "")


@dataclasses.dataclass
class ChangelogReport:
    """Aggregated changelog report."""
    from_ref: str
    to_ref: str
    generated_at: datetime
    changes: list[Change]

    @property
    def breaking_changes(self) -> list[Change]:
        return [c for c in self.changes if c.change_type == ChangeType.BREAKING]

    @property
    def additions(self) -> list[Change]:
        return [c for c in self.changes if c.change_type == ChangeType.ADDED]

    @property
    def deprecations(self) -> list[Change]:
        return [c for c in self.changes if c.change_type == ChangeType.DEPRECATED]

    @property
    def removals(self) -> list[Change]:
        return [c for c in self.changes if c.change_type == ChangeType.REMOVED]

    @property
    def modifications(self) -> list[Change]:
        return [c for c in self.changes if c.change_type == ChangeType.MODIFIED]

    @property
    def has_breaking(self) -> bool:
        return len(self.breaking_changes) > 0

    def summary(self) -> str:
        return (
            f"Breaking: {len(self.breaking_changes)} | "
            f"Added: {len(self.additions)} | "
            f"Deprecated: {len(self.deprecations)} | "
            f"Removed: {len(self.removals)} | "
            f"Modified: {len(self.modifications)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Git Operations
# ─────────────────────────────────────────────────────────────────────────────

def run_git(*args: str, cwd: str | None = None) -> str:
    """Execute a git command and return stdout."""
    cmd = ["git", *args]
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def resolve_ref(ref: str, repo_path: str) -> str:
    """Resolve a git ref to a commit SHA."""
    return run_git("rev-parse", ref, cwd=repo_path)


def get_tag_date(tag: str, repo_path: str) -> datetime:
    """Get the date of a git tag."""
    ts = run_git("log", "-1", "--format=%ci", tag, cwd=repo_path)
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S %z")


def checkout_file(ref: str, file_path: str, repo_path: str) -> str | None:
    """Get file contents at a specific git ref. Returns None if file does not exist."""
    try:
        return run_git("show", f"{ref}:{file_path}", cwd=repo_path)
    except subprocess.CalledProcessError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI Parsing
# ─────────────────────────────────────────────────────────────────────────────

def load_openapi(content: str | None) -> dict[str, Any]:
    """Parse OpenAPI JSON content. Returns empty dict if None."""
    if content is None:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def get_endpoints(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract endpoints from OpenAPI spec as {(path, method): operation}."""
    endpoints: dict[str, dict[str, Any]] = {}
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                key = f"{method.upper()} {path}"
                endpoints[key] = operation or {}
    return endpoints


def get_schemas(spec: dict[str, Any]) -> dict[str, Any]:
    """Extract schemas from OpenAPI spec components."""
    return spec.get("components", {}).get("schemas", {})


def get_parameters(spec: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract parameters per endpoint."""
    params: dict[str, list[dict[str, Any]]] = {}
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            key = f"{method.upper()} {path}"
            op_params = operation.get("parameters", []) if operation else []
            path_params = methods.get("parameters", [])
            all_params = list(op_params) + list(path_params)
            params[key] = all_params
    return params


# ─────────────────────────────────────────────────────────────────────────────
# Change Detection
# ─────────────────────────────────────────────────────────────────────────────

BREAKING_INDICATORS = [
    "required",
    "type",
    "format",
    "minimum",
    "maximum",
    "enum",
    "pattern",
    "maxLength",
    "minLength",
]


def classify_schema_change(
    old_schema: Any, new_schema: Any, path: str = ""
) -> list[Change]:
    """Recursively classify changes between two schemas."""
    changes: list[Change] = []

    if old_schema is None and new_schema is not None:
        changes.append(Change(
            change_type=ChangeType.ADDED,
            layer="",
            path=path,
            method=None,
            description=f"Schema field added: `{path}`",
            severity=Severity.LOW,
        ))
        return changes

    if old_schema is not None and new_schema is None:
        changes.append(Change(
            change_type=ChangeType.BREAKING,
            layer="",
            path=path,
            method=None,
            description=f"Schema field removed: `{path}`",
            severity=Severity.CRITICAL,
        ))
        return changes

    if type(old_schema) != type(new_schema):
        changes.append(Change(
            change_type=ChangeType.BREAKING,
            layer="",
            path=path,
            method=None,
            description=f"Schema type changed at `{path}`: {type(old_schema).__name__} → {type(new_schema).__name__}",
            severity=Severity.CRITICAL,
        ))
        return changes

    if isinstance(old_schema, dict):
        all_keys = set(old_schema.keys()) | set(new_schema.keys())
        for key in all_keys:
            child_path = f"{path}.{key}" if path else key
            if key in BREAKING_INDICATORS and key in old_schema and key in new_schema:
                if old_schema[key] != new_schema[key]:
                    is_breaking = key in ("required", "type", "format")
                    changes.append(Change(
                        change_type=ChangeType.BREAKING if is_breaking else ChangeType.MODIFIED,
                        layer="",
                        path=child_path,
                        method=None,
                        description=f"Schema property `{key}` changed: `{old_schema[key]}` → `{new_schema[key]}`",
                        severity=Severity.CRITICAL if is_breaking else Severity.MEDIUM,
                    ))
            elif key not in old_schema:
                changes.append(Change(
                    change_type=ChangeType.ADDED,
                    layer="",
                    path=child_path,
                    method=None,
                    description=f"Schema property added: `{child_path}`",
                    severity=Severity.LOW,
                ))
            elif key not in new_schema:
                changes.append(Change(
                    change_type=ChangeType.BREAKING,
                    layer="",
                    path=child_path,
                    method=None,
                    description=f"Schema property removed: `{child_path}`",
                    severity=Severity.CRITICAL,
                ))
            else:
                changes.extend(classify_schema_change(
                    old_schema[key], new_schema[key], child_path
                ))

    elif isinstance(old_schema, list):
        max_len = max(len(old_schema), len(new_schema))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(old_schema):
                changes.append(Change(
                    change_type=ChangeType.ADDED,
                    layer="",
                    path=child_path,
                    method=None,
                    description=f"Array item added at `{child_path}`",
                    severity=Severity.LOW,
                ))
            elif i >= len(new_schema):
                changes.append(Change(
                    change_type=ChangeType.BREAKING,
                    layer="",
                    path=child_path,
                    method=None,
                    description=f"Array item removed at `{child_path}`",
                    severity=Severity.CRITICAL,
                ))
            else:
                changes.extend(classify_schema_change(
                    old_schema[i], new_schema[i], child_path
                ))

    elif old_schema != new_schema:
        changes.append(Change(
            change_type=ChangeType.MODIFIED,
            layer="",
            path=path,
            method=None,
            description=f"Value changed: `{old_schema}` → `{new_schema}`",
            severity=Severity.MEDIUM,
        ))

    return changes


def detect_endpoint_changes(
    layer: str,
    old_endpoints: dict[str, Any],
    new_endpoints: dict[str, Any],
) -> list[Change]:
    """Detect changes between two sets of endpoints."""
    changes: list[Change] = []
    old_keys = set(old_endpoints.keys())
    new_keys = set(new_endpoints.keys())

    # Added endpoints
    for key in sorted(new_keys - old_keys):
        method, path = key.split(" ", 1)
        op = new_endpoints[key]
        summary = op.get("summary", "")
        desc = op.get("description", "")
        changes.append(Change(
            change_type=ChangeType.ADDED,
            layer=layer,
            path=path,
            method=method,
            description=f"New endpoint: `{method} {path}`" + (f" — {summary}" if summary else ""),
            severity=Severity.LOW,
        ))

    # Removed endpoints
    for key in sorted(old_keys - new_keys):
        method, path = key.split(" ", 1)
        changes.append(Change(
            change_type=ChangeType.BREAKING,
            layer=layer,
            path=path,
            method=method,
            description=f"Endpoint removed: `{method} {path}`",
            severity=Severity.CRITICAL,
        ))

    # Modified endpoints
    for key in sorted(old_keys & new_keys):
        old_op = old_endpoints[key]
        new_op = new_endpoints[key]
        method, path = key.split(" ", 1)

        # Check for deprecation
        old_deprecated = old_op.get("deprecated", False)
        new_deprecated = new_op.get("deprecated", False)
        if not old_deprecated and new_deprecated:
            changes.append(Change(
                change_type=ChangeType.DEPRECATED,
                layer=layer,
                path=path,
                method=method,
                description=f"Endpoint deprecated: `{method} {path}`",
                severity=Severity.MEDIUM,
            ))

        # Check for summary/description changes
        for field in ("summary", "description"):
            old_val = old_op.get(field, "")
            new_val = new_op.get(field, "")
            if old_val != new_val and old_val and new_val:
                changes.append(Change(
                    change_type=ChangeType.MODIFIED,
                    layer=layer,
                    path=path,
                    method=method,
                    description=f"{field.capitalize()} updated for `{method} {path}`",
                    severity=Severity.LOW,
                ))

        # Check request body changes
        old_body = old_op.get("requestBody", {})
        new_body = new_op.get("requestBody", {})
        if old_body != new_body:
            old_required = old_body.get("required", False)
            new_required = new_body.get("required", False)
            if not old_required and new_required:
                changes.append(Change(
                    change_type=ChangeType.BREAKING,
                    layer=layer,
                    path=path,
                    method=method,
                    description=f"Request body made required: `{method} {path}`",
                    severity=Severity.CRITICAL,
                ))
            else:
                changes.append(Change(
                    change_type=ChangeType.MODIFIED,
                    layer=layer,
                    path=path,
                    method=method,
                    description=f"Request body modified: `{method} {path}`",
                    severity=Severity.MEDIUM,
                ))

        # Check response changes
        old_responses = old_op.get("responses", {})
        new_responses = new_op.get("responses", {})
        old_statuses = set(old_responses.keys())
        new_statuses = set(new_responses.keys())

        for status in sorted(new_statuses - old_statuses):
            changes.append(Change(
                change_type=ChangeType.ADDED,
                layer=layer,
                path=path,
                method=method,
                description=f"New response status `{status}` on `{method} {path}`",
                severity=Severity.LOW,
            ))

        for status in sorted(old_statuses - new_statuses):
            changes.append(Change(
                change_type=ChangeType.BREAKING,
                layer=layer,
                path=path,
                method=method,
                description=f"Response status `{status}` removed from `{method} {path}`",
                severity=Severity.CRITICAL,
            ))

    return changes


def detect_schema_changes(
    layer: str,
    old_schemas: dict[str, Any],
    new_schemas: dict[str, Any],
) -> list[Change]:
    """Detect changes between two sets of schemas."""
    changes: list[Change] = []
    old_keys = set(old_schemas.keys())
    new_keys = set(new_schemas.keys())

    for name in sorted(new_keys - old_keys):
        changes.append(Change(
            change_type=ChangeType.ADDED,
            layer=layer,
            path=f"#/components/schemas/{name}",
            method=None,
            description=f"New schema: `{name}`",
            severity=Severity.LOW,
        ))

    for name in sorted(old_keys - new_keys):
        changes.append(Change(
            change_type=ChangeType.BREAKING,
            layer=layer,
            path=f"#/components/schemas/{name}",
            method=None,
            description=f"Schema removed: `{name}`",
            severity=Severity.CRITICAL,
        ))

    for name in sorted(old_keys & new_keys):
        schema_changes = classify_schema_change(
            old_schemas[name], new_schemas[name], path=name
        )
        for sc in schema_changes:
            # Reconstruct with proper layer
            changes.append(Change(
                change_type=sc.change_type,
                layer=layer,
                path=f"#/components/schemas/{sc.path}",
                method=sc.method,
                description=sc.description,
                severity=sc.severity,
            ))

    return changes


# ─────────────────────────────────────────────────────────────────────────────
# Changelog Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_markdown(report: ChangelogReport) -> str:
    """Generate a Markdown changelog from a report."""
    lines: list[str] = []
    lines.append(f"# API Changelog: `{report.from_ref}` → `{report.to_ref}`")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at.isoformat()}Z")
    lines.append(f"**Summary:** {report.summary()}")
    lines.append("")

    if report.has_breaking:
        lines.append("> **⚠️ BREAKING CHANGES DETECTED** — Consumers must update before upgrading."
        )
        lines.append("")

    # Breaking changes
    if report.breaking_changes:
        lines.append("## 🔴 Breaking Changes")
        lines.append("")
        for change in report.breaking_changes:
            lines.append(f"### {change.emoji} `{change.layer}` — {change.description}")
            lines.append(f"- **Severity:** {change.severity.value.upper()}")
            lines.append(f"- **Path:** `{change.path}`")
            if change.details:
                lines.append(f"- **Details:** {change.details}")
            lines.append("")

    # Added
    if report.additions:
        lines.append("## ➕ Additions")
        lines.append("")
        for change in report.additions:
            lines.append(f"- **{change.layer}:** {change.description}")
        lines.append("")

    # Deprecations
    if report.deprecations:
        lines.append("## ⚠️ Deprecations")
        lines.append("")
        lines.append("The following will be removed in a future version. Migrate soon.")
        lines.append("")
        for change in report.deprecations:
            lines.append(f"- **{change.layer}:** `{change.method} {change.path}` — {change.description}")
        lines.append("")

    # Removals
    if report.removals:
        lines.append("## ➖ Removals")
        lines.append("")
        for change in report.removals:
            lines.append(f"- **{change.layer}:** `{change.method} {change.path}` — {change.description}")
        lines.append("")

    # Modifications
    if report.modifications:
        lines.append("## 📝 Modifications")
        lines.append("")
        for change in report.modifications:
            lines.append(f"- **{change.layer}:** {change.description}")
        lines.append("")

    # Per-layer breakdown
    lines.append("## Layer Breakdown")
    lines.append("")
    layers = sorted(set(c.layer for c in report.changes))
    for layer in layers:
        layer_changes = [c for c in report.changes if c.layer == layer]
        breaking = len([c for c in layer_changes if c.change_type == ChangeType.BREAKING])
        added = len([c for c in layer_changes if c.change_type == ChangeType.ADDED])
        deprecated = len([c for c in layer_changes if c.change_type == ChangeType.DEPRECATED])
        removed = len([c for c in layer_changes if c.change_type == ChangeType.REMOVED])
        modified = len([c for c in layer_changes if c.change_type == ChangeType.MODIFIED])
        lines.append(f"### {layer}")
        lines.append(f"| Breaking | Added | Deprecated | Removed | Modified |")
        lines.append(f"|----------|-------|------------|---------|----------|")
        lines.append(f"| {breaking} | {added} | {deprecated} | {removed} | {modified} |")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated by Fabric 4L API Changelog Generator v1.2.0*")
    lines.append(f"*For questions, contact #api-support*")

    return "\n".join(lines)


def generate_github_release_body(report: ChangelogReport) -> str:
    """Generate GitHub release notes body (Markdown)."""
    lines: list[str] = []
    lines.append(f"## API Changes: `{report.from_ref}` → `{report.to_ref}`")
    lines.append("")
    lines.append(f"**Summary:** {report.summary()}")
    lines.append("")

    if report.has_breaking:
        lines.append("### 🚨 Breaking Changes")
        lines.append("")
        for c in report.breaking_changes:
            lines.append(f"- `{c.layer}` — {c.description}")
        lines.append("")
        lines.append("> ⚠️ **Action Required:** Review breaking changes before upgrading.")
        lines.append("")

    if report.additions:
        lines.append("### ➕ New Endpoints & Features")
        lines.append("")
        for c in report.additions:
            lines.append(f"- `{c.layer}` — {c.description}")
        lines.append("")

    if report.deprecations:
        lines.append("### ⚠️ Deprecations")
        lines.append("")
        for c in report.deprecations:
            lines.append(f"- `{c.layer}` — `{c.method} {c.path}`")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# GitHub API Integration
# ─────────────────────────────────────────────────────────────────────────────

def create_github_release(
    repo: str,
    tag: str,
    body: str,
    token: str,
    target_commitish: str = "main",
    draft: bool = False,
    prerelease: bool = False,
) -> dict[str, Any]:
    """Create a GitHub release via the API."""
    import urllib.request
    import urllib.error

    url = f"{GITHUB_API_URL}/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "tag_name": tag,
        "target_commitish": target_commitish,
        "name": f"Release {tag}",
        "body": body,
        "draft": draft,
        "prerelease": prerelease,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"GitHub API error: {e.code} — {error_body}")


def update_github_release(
    repo: str,
    release_id: int,
    body: str,
    token: str,
) -> dict[str, Any]:
    """Update an existing GitHub release body."""
    import urllib.request

    url = f"{GITHUB_API_URL}/repos/{repo}/releases/{release_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"body": body}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fabric 4L API Changelog Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --from v1.0.0 --to v1.1.0 --output CHANGELOG-API.md
  %(prog)s --from v1.0.0 --to HEAD --github-release --repo my-org/fabric-4l
  %(prog)s --from origin/main --to HEAD --output /tmp/changes.md
        """,
    )
    parser.add_argument(
        "--from", "-f", dest="from_ref", required=True,
        help="Git reference (tag, branch, or commit) for the base version",
    )
    parser.add_argument(
        "--to", "-t", dest="to_ref", default="HEAD",
        help="Git reference for the new version (default: HEAD)",
    )
    parser.add_argument(
        "--output", "-o", default="CHANGELOG-API.md",
        help="Output file path for the changelog (default: CHANGELOG-API.md)",
    )
    parser.add_argument(
        "--repo-path", default=".",
        help="Path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--github-release", action="store_true",
        help="Create or update a GitHub release with the changelog",
    )
    parser.add_argument(
        "--repo", default=os.getenv("GITHUB_REPOSITORY", ""),
        help="GitHub repository slug (owner/repo). Required with --github-release",
    )
    parser.add_argument(
        "--github-token", default=os.getenv("GITHUB_TOKEN", ""),
        help="GitHub personal access token. Defaults to GITHUB_TOKEN env var",
    )
    parser.add_argument(
        "--tag",
        help="Git tag for the GitHub release (defaults to --to if a tag)",
    )
    parser.add_argument(
        "--prerelease", action="store_true",
        help="Mark the GitHub release as a prerelease",
    )
    parser.add_argument(
        "--draft", action="store_true",
        help="Create the GitHub release as a draft",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output report as JSON (to stdout)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress non-error output",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"Error: {repo_path} is not a git repository", file=sys.stderr)
        return 2

    # Resolve refs
    try:
        from_sha = resolve_ref(args.from_ref, repo_path)
        to_sha = resolve_ref(args.to_ref, repo_path)
    except subprocess.CalledProcessError as e:
        print(f"Error resolving git ref: {e}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"Comparing {args.from_ref} ({from_sha[:8]}) → {args.to_ref} ({to_sha[:8]})")

    # Collect changes per layer
    all_changes: list[Change] = []

    for layer in FABRIC_LAYERS:
        openapi_file = f"{OPENAPI_DIR}/{layer}.openapi.json"

        old_content = checkout_file(from_sha, openapi_file, repo_path)
        new_content = checkout_file(to_sha, openapi_file, repo_path)

        if old_content is None and new_content is None:
            continue  # No OpenAPI spec for this layer at either ref

        old_spec = load_openapi(old_content)
        new_spec = load_openapi(new_content)

        if old_spec and not new_spec:
            all_changes.append(Change(
                change_type=ChangeType.BREAKING,
                layer=layer,
                path=openapi_file,
                method=None,
                description=f"OpenAPI spec for `{layer}` was removed entirely",
                severity=Severity.CRITICAL,
            ))
            continue

        if new_spec and not old_spec:
            all_changes.append(Change(
                change_type=ChangeType.ADDED,
                layer=layer,
                path=openapi_file,
                method=None,
                description=f"OpenAPI spec for `{layer}` is new",
                severity=Severity.LOW,
            ))

        old_endpoints = get_endpoints(old_spec)
        new_endpoints = get_endpoints(new_spec)
        all_changes.extend(detect_endpoint_changes(layer, old_endpoints, new_endpoints))

        old_schemas = get_schemas(old_spec)
        new_schemas = get_schemas(new_spec)
        all_changes.extend(detect_schema_changes(layer, old_schemas, new_schemas))

    # Build report
    report = ChangelogReport(
        from_ref=args.from_ref,
        to_ref=args.to_ref,
        generated_at=datetime.now(timezone.utc),
        changes=all_changes,
    )

    if not args.quiet:
        print(f"Detected {len(all_changes)} changes: {report.summary()}")

    # Generate outputs
    markdown = generate_markdown(report)

    # Write changelog file
    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    if not args.quiet:
        print(f"Changelog written to: {output_path}")

    # JSON output
    if args.json:
        json_report = {
            "from_ref": report.from_ref,
            "to_ref": report.to_ref,
            "generated_at": report.generated_at.isoformat(),
            "summary": report.summary(),
            "has_breaking": report.has_breaking,
            "changes": [
                {
                    "type": c.change_type.value,
                    "layer": c.layer,
                    "path": c.path,
                    "method": c.method,
                    "description": c.description,
                    "severity": c.severity.value,
                }
                for c in report.changes
            ],
        }
        print(json.dumps(json_report, indent=2))

    # GitHub release
    if args.github_release:
        token = args.github_token
        if not token:
            print("Error: GitHub token required. Set GITHUB_TOKEN env var or use --github-token", file=sys.stderr)
            return 2

        repo = args.repo
        if not repo:
            print("Error: GitHub repo required. Set GITHUB_REPOSITORY env var or use --repo", file=sys.stderr)
            return 2

        tag = args.tag or args.to_ref
        # Ensure tag is a valid git tag, not a branch or commit
        try:
            run_git("show-ref", "--verify", f"refs/tags/{tag}", cwd=repo_path)
        except subprocess.CalledProcessError:
            print(f"Warning: {tag} is not a tag, using {args.to_ref} as release tag", file=sys.stderr)
            tag = args.to_ref

        body = generate_github_release_body(report)

        try:
            release = create_github_release(
                repo=repo,
                tag=tag,
                body=body,
                token=token,
                draft=args.draft,
                prerelease=args.prerelease,
            )
            if not args.quiet:
                print(f"GitHub release created: {release['html_url']}")
        except RuntimeError as e:
            print(f"Error creating GitHub release: {e}", file=sys.stderr)
            return 2

    # Exit code signals breaking changes
    return 1 if report.has_breaking else 0


if __name__ == "__main__":
    sys.exit(main())
