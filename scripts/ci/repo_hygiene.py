#!/usr/bin/env python3
"""Repository Hygiene Validator for Fabric_4L / Value Fabric.

Enforces the config/canonical-paths.yaml manifest by scanning CI workflows,
Dependabot, CODEOWNERS, and selected scripts for references to obsolete
or deleted directories.

Exit codes:
    0 — No violations
    1 — One or more violations found
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# We try to import yaml; if unavailable we fail gracefully.
try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"ERROR: PyYAML is required: {exc}")
    sys.exit(1)


@dataclass
class Violation:
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    suggestion: str


@dataclass
class HygieneReport:
    repo_root: str
    manifest_version: str
    violations: list[Violation] = field(default_factory=list)
    passed: bool = True


def load_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / "config" / "canonical-paths.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Canonical path manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def check_canonical_paths_exist(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Ensure every canonical path in the manifest exists on disk."""
    violations: list[Violation] = []
    canonical = manifest.get("canonical", {})

    def check_path(path_str: str, category: str) -> None:
        p = repo_root / path_str
        if not p.exists():
            violations.append(
                Violation(
                    rule_id="canonical_docs_exist",
                    severity="error",
                    file="config/canonical-paths.yaml",
                    line=0,
                    message=f"Canonical {category} path does not exist: {path_str}",
                    suggestion="Update the manifest or restore the missing directory.",
                )
            )

    for app in canonical.get("applications", {}).get("entries", []):
        check_path(app["path"], "application")
        for df in app.get("dockerfiles", []):
            if not (repo_root / df).exists():
                violations.append(
                    Violation(
                        rule_id="canonical_docs_exist",
                        severity="error",
                        file="config/canonical-paths.yaml",
                        line=0,
                        message=f"Canonical Dockerfile does not exist: {df}",
                        suggestion="Update the manifest or restore the missing Dockerfile.",
                    )
                )

    for svc in canonical.get("services", {}).get("entries", []):
        check_path(svc["path"], "service")
        for df in svc.get("dockerfiles", []):
            if not (repo_root / df).exists():
                violations.append(
                    Violation(
                        rule_id="canonical_docs_exist",
                        severity="error",
                        file="config/canonical-paths.yaml",
                        line=0,
                        message=f"Canonical Dockerfile does not exist: {df}",
                        suggestion="Update the manifest or restore the missing Dockerfile.",
                    )
                )

    for pkg in canonical.get("packages", {}).get("entries", []):
        check_path(pkg["path"], "package")

    for doc in canonical.get("documentation", {}).get("sub_roots", []):
        check_path(doc["path"], "documentation")

    for ctr in canonical.get("contracts", {}).get("entries", []):
        check_path(ctr["path"], "contract")

    for root_key in ("tests", "sdk", "k8s", "monitoring", "packs"):
        if root_key in canonical:
            check_path(canonical[root_key].get("root", root_key + "/"), root_key)

    return violations


def obsolete_roots(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a mapping of obsolete path prefix -> metadata."""
    mapping: dict[str, dict[str, Any]] = {}
    for item in manifest.get("obsolete", []):
        path = item["path"]
        if not path.endswith("/"):
            path = path + "/"
        mapping[path] = item
    return mapping


def is_allowed_reference(line: str, obsolete_item: dict[str, Any]) -> bool:
    """Heuristic: does the line match an allowed-reference pattern?"""
    allowed = obsolete_item.get("allowed_references", [])
    if not allowed:
        return False
    # Match full allowed phrases (case-insensitive substring) rather than
    # individual tokens, to avoid false negatives from common words.
    lower = line.lower()
    for phrase in allowed:
        if phrase.lower() in lower:
            return True
    return False


def scan_workflows(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Scan GitHub workflow files for obsolete path references."""
    violations: list[Violation] = []
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        return violations

    obs = obsolete_roots(manifest)

    # Patterns that indicate a filesystem path reference in workflow YAML
    path_patterns = [
        re.compile(r"^\s*-\s+'([^']+)'\s*$"),  # list items like - 'path/**'
        re.compile(r"^\s*-\s+\"([^\"]+)\"\s*$"),  # list items like - "path/**"
        re.compile(r"^\s*([\w-]+)\s*[=:]\s*'([^']+)'\s*$"),  # key: 'path' or key='path'
        re.compile(r"^\s*([\w-]+)\s*[=:]\s*\"([^\"]+)\"\s*$"),  # key: "path"
        re.compile(r"^\s*([\w-]+)\s*[=:]\s*([^#'\"\s][^#'\"]*)\s*$"),  # unquoted values
    ]

    for wf_file in workflows_dir.glob("*.yml"):
        content = wf_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(("service:", "owner:", "escalation:", "EKS_CLUSTER_NAME:")):
                continue

            # Extract candidate path strings from the line
            candidates: list[str] = []
            for pat in path_patterns:
                for m in pat.finditer(line):
                    candidates.append(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1))

            for candidate in candidates:
                for obs_prefix, obs_item in obs.items():
                    obs_name = obs_prefix.rstrip("/")
                    # Skip if this is an allowed contextual reference
                    if is_allowed_reference(line, obs_item):
                        continue

                    # Match literal prefix (e.g., "frontend/" or "services/")
                    if candidate.startswith(obs_prefix) or candidate == obs_name:
                        severity = obs_item.get("severity", "error")
                        # Warnings for value-fabric in specific allowed contexts
                        if obs_name == "value-fabric":
                            # Allow docker-compose.yml references temporarily
                            if "docker-compose" in candidate or "docker compose" in line:
                                continue
                            # Allow ADR/doc references
                            if "/ADRs/" in candidate or "/docs/" in candidate:
                                continue
                            # Allow test references inside services/tests (temporary)
                            if "/tests/" in candidate:
                                continue
                            # Allow scripts references
                            if "/scripts/" in candidate:
                                continue
                            # Disallow docker build contexts, eslint working dirs, etc.
                            disallowed = obs_item.get("disallowed_in", [])
                            if "docker_build_contexts" in disallowed:
                                if "context" in line.lower() or "dockerfile" in line.lower():
                                    severity = "error"
                            if "path_filters_for_service_code" in disallowed:
                                if "paths:" in line.lower() or (stripped.startswith("-") and ("/**" in candidate or "*." in candidate)):
                                    severity = "error"
                            if "eslint_working_directories" in disallowed:
                                if "working-directory" in line.lower() and ("eslint" in line.lower() or "lint" in line.lower()):
                                    severity = "error"
                            if "npm_cache_dependency_paths" in disallowed:
                                if "cache-dependency-path" in line.lower():
                                    severity = "error"

                        violations.append(
                            Violation(
                                rule_id="no_obsolete_path_filters"
                                if stripped.startswith("-")
                                else "no_obsolete_working_directories",
                                severity=severity,
                                file=str(wf_file.relative_to(repo_root)).replace("\\", "/"),
                                line=lineno,
                                message=f"Workflow references obsolete path '{obs_name}': {candidate}",
                                suggestion=f"Migrate reference from '{obs_name}/' to its canonical location (see config/canonical-paths.yaml).",
                            )
                        )
                        break  # one violation per line is enough
    return violations


def scan_dependabot(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Scan dependabot.yml for obsolete directory entries."""
    violations: list[Violation] = []
    dependabot_path = repo_root / ".github" / "dependabot.yml"
    if not dependabot_path.exists():
        return violations

    obs = obsolete_roots(manifest)
    content = dependabot_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("directory:"):
            continue
        # Extract the path value
        parts = stripped.split(":", 1)
        if len(parts) != 2:
            continue
        val = parts[1].strip().strip("'\"").lstrip("/")
        if not val:
            continue
        val_prefix = val if val.endswith("/") else val + "/"
        for obs_prefix, obs_item in obs.items():
            if val_prefix.startswith(obs_prefix.rstrip("/") + "/") or val == obs_prefix.rstrip("/"):
                violations.append(
                    Violation(
                        rule_id="dependabot_no_obsolete_dirs",
                        severity=obs_item.get("severity", "error"),
                        file=".github/dependabot.yml",
                        line=lineno,
                        message=f"Dependabot scans obsolete directory: /{val}",
                        suggestion=f"Remove or update the obsolete directory entry in dependabot.yml.",
                    )
                )
                break
    return violations


def scan_codeowners(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Scan CODEOWNERS for obsolete directory assignments."""
    violations: list[Violation] = []
    codeowners_path = repo_root / ".github" / "CODEOWNERS"
    if not codeowners_path.exists():
        return violations

    obs = obsolete_roots(manifest)
    content = codeowners_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # First token is the path pattern
        path_pat = stripped.split()[0]
        # Normalize: remove leading slash and trailing wildcards
        normalized = path_pat.lstrip("/").rstrip("*")
        if not normalized:
            continue
        for obs_prefix, obs_item in obs.items():
            obs_name = obs_prefix.rstrip("/")
            if normalized.startswith(obs_name + "/") or normalized == obs_name:
                # Allow global fallback or comments about migration
                if is_allowed_reference(line, obs_item):
                    continue
                violations.append(
                    Violation(
                        rule_id="codeowners_no_obsolete_dirs",
                        severity=obs_item.get("severity", "warn"),
                        file=".github/CODEOWNERS",
                        line=lineno,
                        message=f"CODEOWNERS assigns reviewers to obsolete path: {path_pat}",
                        suggestion=f"Update CODEOWNERS to point to the canonical location (e.g., apps/web/ instead of frontend/).",
                    )
                )
                break
    return violations


def scan_shell_scripts(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Scan selected shell scripts for hard-coded obsolete paths."""
    violations: list[Violation] = []
    obs = obsolete_roots(manifest)

    scripts_to_scan = [
        repo_root / ".github" / "scripts" / "validate-no-hardcoded-secrets.sh",
    ]

    for script_path in scripts_to_scan:
        if not script_path.exists():
            continue
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for lineno, line in enumerate(lines, start=1):
            for obs_prefix, obs_item in obs.items():
                obs_name = obs_prefix.rstrip("/")
                if obs_name in line:
                    if is_allowed_reference(line, obs_item):
                        continue
                    violations.append(
                        Violation(
                            rule_id="no_obsolete_working_directories",
                            severity=obs_item.get("severity", "error"),
                            file=str(script_path.relative_to(repo_root)).replace("\\", "/"),
                            line=lineno,
                            message=f"Script references obsolete path '{obs_name}'",
                            suggestion=f"Update script to use canonical path (e.g., apps/web/ instead of frontend/).",
                        )
                    )
                    break
    return violations


def scan_monitoring_runbooks(repo_root: Path, manifest: dict[str, Any]) -> list[Violation]:
    """Check that monitoring alert rule runbook URLs point to canonical doc paths."""
    violations: list[Violation] = []
    rules_path = repo_root / "monitoring" / "alerting" / "rules.yml"
    if not rules_path.exists():
        return violations

    content = rules_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    for lineno, line in enumerate(lines, start=1):
        if "runbook_url" not in line:
            continue
        # Look for docs/runbooks/ that is NOT docs/runbooks/operational/
        m = re.search(r"docs/runbooks/([^\s\"']+)", line)
        if not m:
            continue
        runbook_path = m.group(1)
        if runbook_path.startswith("operational/"):
            continue
        violations.append(
            Violation(
                rule_id="no_obsolete_path_filters",
                severity="error",
                file="monitoring/alerting/rules.yml",
                line=lineno,
                message=f"Alert rule references legacy runbook path: docs/runbooks/{runbook_path}",
                suggestion="Move runbook to docs/troubleshooting/runbooks/ and update the URL.",
            )
        )
    return violations


def scan_production_frontend_client_references(repo_root: Path) -> list[Violation]:
    """Fail on new production references to legacy frontend/client paths."""
    violations: list[Violation] = []
    files_to_scan = [
        repo_root / "README.md",
        repo_root / "docs" / "how-to-guides" / "setup-local-dev.md",
        repo_root / "docs" / "getting-started" / "environment.md",
        repo_root / "docs" / "operations" / "COMMAND_REFERENCE.md",
        repo_root / "scripts" / "infisical" / "bootstrap-dev.sh",
        repo_root / "scripts" / "infisical" / "bootstrap-dev.ps1",
    ]
    patterns = ("frontend/client", "frontend/")

    for file_path in files_to_scan:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if "apps/web/" in line and "instead of frontend/" in line:
                continue
            if "OBSOLETE" in line.upper() or "legacy frontend" in line.lower():
                continue
            if "legacy commands" in line.lower() and "canonical paths" in line.lower():
                continue
            if any(pattern in line for pattern in patterns):
                violations.append(
                    Violation(
                        rule_id="no_legacy_frontend_client_refs",
                        severity="error",
                        file=str(file_path.relative_to(repo_root)).replace("\\", "/"),
                        line=lineno,
                        message="Production docs/scripts reference legacy frontend path.",
                        suggestion="Update reference to apps/web/ and point readers to apps/web/README.md.",
                    )
                )
    return violations


def scan_extensionless_frontend_files(repo_root: Path) -> list[Violation]:
    """Flag extensionless files in apps/web that are not executable scripts."""
    violations: list[Violation] = []
    frontend_root = repo_root / "apps" / "web"
    if not frontend_root.exists():
        return violations

    allowed_extensionless_files = {"Dockerfile"}
    for file_path in frontend_root.rglob("*"):
        if not file_path.is_file():
            continue
        if "node_modules" in file_path.parts or ".git" in file_path.parts:
            continue
        if file_path.suffix:
            continue
        if file_path.name.startswith("."):
            continue
        if file_path.name in allowed_extensionless_files:
            continue
        if file_path.stat().st_mode & 0o111:
            continue

        violations.append(
            Violation(
                rule_id="frontend_extensionless_file_policy",
                severity="warn",
                file=str(file_path.relative_to(repo_root)).replace("\\", "/"),
                line=0,
                message="Extensionless file under apps/web is not executable.",
                suggestion="Add a descriptive extension, move the artifact to reports/, or make it an executable script if intentional.",
            )
        )
    return violations




def load_root_binary_allowlist(repo_root: Path) -> set[str]:
    """Load root-level binary allowlist entries."""
    allowlist_path = repo_root / "scripts" / "ci" / "root_binary_allowlist.txt"
    if not allowlist_path.exists():
        return set()

    entries: set[str] = set()
    for raw_line in allowlist_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def appears_binary(path: Path) -> bool:
    """Best-effort binary detection using NUL-byte heuristic."""
    chunk = path.read_bytes()[:4096]
    return b"\x00" in chunk


def scan_root_binary_blobs(repo_root: Path) -> list[Violation]:
    """Block unapproved root-level binary blobs."""
    violations: list[Violation] = []
    allowlist = load_root_binary_allowlist(repo_root)

    for path in repo_root.iterdir():
        if path.name.startswith('.') and path.name not in allowlist:
            continue
        if not path.is_file():
            continue

        relative = path.relative_to(repo_root).as_posix()
        if relative in allowlist:
            continue
        if path.suffix in {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".lock", ".sh", ".py", ".js", ".ts", ".tsx", ".jsx", ".ini", ".cfg", ".xml", ".env", ".csv", ".svg"}:
            continue
        if not appears_binary(path):
            continue

        violations.append(
            Violation(
                rule_id="root_binary_blob_policy",
                severity="error",
                file=relative,
                line=0,
                message="Unapproved root-level binary blob detected.",
                suggestion=(
                    "Move the file into a governed artifact location (for example artifacts/non-runtime/) "
                    "or publish it via the release asset process, then add an explicit allowlist entry only if needed."
                ),
            )
        )
    return violations

def main() -> int:
    parser = argparse.ArgumentParser(description="Repository hygiene validator")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fail-on-warnings", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    try:
        manifest = load_manifest(repo_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    manifest_version = manifest.get("metadata", {}).get("version", "unknown")
    all_violations: list[Violation] = []

    all_violations.extend(check_canonical_paths_exist(repo_root, manifest))
    all_violations.extend(scan_workflows(repo_root, manifest))
    all_violations.extend(scan_dependabot(repo_root, manifest))
    all_violations.extend(scan_codeowners(repo_root, manifest))
    all_violations.extend(scan_shell_scripts(repo_root, manifest))
    all_violations.extend(scan_monitoring_runbooks(repo_root, manifest))
    all_violations.extend(scan_production_frontend_client_references(repo_root))
    all_violations.extend(scan_extensionless_frontend_files(repo_root))
    all_violations.extend(scan_root_binary_blobs(repo_root))

    errors = [v for v in all_violations if v.severity == "error"]
    warnings = [v for v in all_violations if v.severity == "warn"]

    passed = len(errors) == 0
    if args.fail_on_warnings and warnings:
        passed = False

    report = HygieneReport(
        repo_root=str(repo_root),
        manifest_version=manifest_version,
        violations=all_violations,
        passed=passed,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "repo_root": report.repo_root,
                    "manifest_version": report.manifest_version,
                    "passed": report.passed,
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "violations": [asdict(v) for v in report.violations],
                },
                indent=2,
            )
        )
    else:
        print(f"\n{'='*60}")
        print("REPO HYGIENE REPORT")
        print(f"{'='*60}")
        print(f"Repository : {report.repo_root}")
        print(f"Manifest   : v{report.manifest_version}")
        print(f"Status     : {'PASS' if report.passed else 'FAIL'}")
        print(f"Errors     : {len(errors)}")
        print(f"Warnings   : {len(warnings)}")
        print(f"{'='*60}\n")

        if errors:
            print("ERRORS:")
            for v in errors:
                print(f"  [{v.rule_id}] {v.file}:{v.line}")
                print(f"    {v.message}")
                print(f"    -> {v.suggestion}")
            print()

        if warnings:
            print("WARNINGS:")
            for v in warnings:
                print(f"  [{v.rule_id}] {v.file}:{v.line}")
                print(f"    {v.message}")
                print(f"    -> {v.suggestion}")
            print()

        if report.passed:
            print("[PASS] Repository layout is canonical. No obsolete path references found.")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
