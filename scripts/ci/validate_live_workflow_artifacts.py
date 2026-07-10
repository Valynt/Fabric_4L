#!/usr/bin/env python3
"""Validate Fabric_4L live workflow validation artifact contracts.

This checker is intentionally lightweight and dependency-free so it can run in local
sandboxes and GitHub Actions before reviewers trust a live-validation artifact set.
It validates the machine-readable evidence emitted by
``scripts/ci/run_live_workflow_validation.sh`` without requiring a live stack.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ALLOWED_STATUSES = {"PASS", "FAIL", "BLOCKED"}
REQUIRED_SUMMARY_KEYS = {
    "generatedAt",
    "status",
    "detail",
    "composeFile",
    "frontendUrl",
    "backendUrl",
    "seedRequested",
    "playwrightRequested",
    "artifacts",
    "artifactPresence",
}
REQUIRED_ARTIFACT_KEYS = {
    "markdownSummary",
    "jsonSummary",
    "manifest",
    "log",
    "composeConfig",
    "containerStatus",
    "healthStatus",
    "endpointProbes",
    "serviceLogs",
    "seedReportJson",
    "playwrightArtifacts",
}
REQUIRED_MANIFEST_KEYS = {"generatedAt", "status", "artifactRoot", "entries"}
REQUIRED_ENDPOINT_COLUMNS = ["name", "url", "status_code"]
MAX_TEXT_SCAN_BYTES = 2_000_000
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip", ".gz", ".br"}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----"),
    ),
    (
        "bearer token assignment",
        re.compile(r"(?i)\bAuthorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    ),
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AssertionError(f"required JSON artifact is missing: {path}") from None
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_summary(artifact_dir: Path) -> dict[str, Any]:
    summary_path = artifact_dir / "live-workflow-validation-summary.json"
    summary = load_json(summary_path)
    require(isinstance(summary, dict), "summary JSON must be an object")

    missing = REQUIRED_SUMMARY_KEYS - set(summary)
    require(not missing, f"summary JSON missing keys: {sorted(missing)}")
    require(summary["status"] in ALLOWED_STATUSES, f"invalid summary status: {summary['status']!r}")
    require(
        isinstance(summary["detail"], str) and summary["detail"].strip(),
        "summary detail must be non-empty",
    )
    require(isinstance(summary["seedRequested"], bool), "seedRequested must be boolean")
    require(isinstance(summary["playwrightRequested"], bool), "playwrightRequested must be boolean")
    require(isinstance(summary["artifacts"], dict), "summary artifacts must be an object")
    require(isinstance(summary["artifactPresence"], dict), "summary artifactPresence must be an object")

    missing_artifacts = REQUIRED_ARTIFACT_KEYS - set(summary["artifacts"])
    require(not missing_artifacts, f"summary artifacts missing keys: {sorted(missing_artifacts)}")
    for key in ("markdownSummary", "jsonSummary", "manifest", "log", "composeConfig"):
        require(summary["artifactPresence"].get(key) is True, f"required artifactPresence.{key} must be true")
    return summary


def validate_manifest(artifact_dir: Path, expected_status: str) -> dict[str, Any]:
    manifest_path = artifact_dir / "artifact-manifest.json"
    manifest = load_json(manifest_path)
    require(isinstance(manifest, dict), "artifact manifest must be an object")

    missing = REQUIRED_MANIFEST_KEYS - set(manifest)
    require(not missing, f"artifact manifest missing keys: {sorted(missing)}")
    require(manifest["status"] == expected_status, "manifest status must match summary status")
    require(isinstance(manifest["entries"], list), "artifact manifest entries must be a list")

    entry_paths = set()
    for entry in manifest["entries"]:
        require(isinstance(entry, dict), "manifest entry must be an object")
        require({"path", "type", "bytes"} <= set(entry), f"manifest entry missing required fields: {entry!r}")
        require(entry["type"] in {"file", "directory"}, f"invalid manifest entry type: {entry['type']!r}")
        require(
            isinstance(entry["bytes"], int) and entry["bytes"] >= 0,
            "manifest entry bytes must be non-negative integer",
        )
        entry_paths.add(entry["path"])

    for required in (
        "live-workflow-validation-summary.md",
        "live-workflow-validation-summary.json",
        "artifact-manifest.json",
        "docker-compose.live.resolved.yml",
    ):
        require(required in entry_paths, f"artifact manifest missing required path: {required}")
    return manifest


def validate_endpoint_probes(artifact_dir: Path, *, required_when_present: bool) -> None:
    probes_path = artifact_dir / "endpoint-probes.tsv"
    if not probes_path.exists():
        require(not required_when_present, "endpoint probes artifact is required but missing")
        return

    lines = [line.rstrip("\n") for line in probes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(lines, "endpoint probes file is empty")
    require(lines[0].split("\t") == REQUIRED_ENDPOINT_COLUMNS, "endpoint probes header is invalid")
    for index, line in enumerate(lines[1:], start=2):
        columns = line.split("\t")
        require(len(columns) == 3, f"endpoint probes line {index} must have 3 tab-separated fields")
        require(
            columns[2].isdigit() and len(columns[2]) == 3,
            f"endpoint probe line {index} has invalid status code: {columns[2]!r}",
        )


def validate_seed_report(artifact_dir: Path, *, required: bool) -> None:
    seed_path = artifact_dir / "seed-report.json"
    if not seed_path.exists():
        require(not required, "seed report was requested but seed-report.json is missing")
        return

    seed = load_json(seed_path)
    require(isinstance(seed, dict), "seed report must be an object")
    for key in ("generatedAt", "backendUrl", "strictSeed", "status", "rows"):
        require(key in seed, f"seed report missing key: {key}")
    require(
        seed["status"] in {"present", "partial", "blocked", "missing"},
        f"invalid seed report status: {seed['status']!r}",
    )
    require(isinstance(seed["rows"], list), "seed report rows must be a list")


def iter_text_artifacts(artifact_dir: Path) -> Iterable[Path]:
    for path in artifact_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        if path.stat().st_size > MAX_TEXT_SCAN_BYTES:
            continue
        yield path


def scan_secret_patterns(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return [label for label, pattern in SECRET_PATTERNS if pattern.search(text)]


def validate_no_obvious_secrets(artifact_dir: Path) -> None:
    findings: list[str] = []
    for path in iter_text_artifacts(artifact_dir):
        relative = path.relative_to(artifact_dir)
        findings.extend(f"{relative}: {label}" for label in scan_secret_patterns(path))
    require(not findings, "obvious secret material found in artifacts: " + "; ".join(findings[:10]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate live workflow validation artifacts")
    parser.add_argument(
        "artifact_dir",
        nargs="?",
        default="artifacts/live-workflow-validation",
        help="Artifact directory to validate",
    )
    parser.add_argument("--require-endpoint-probes", action="store_true", help="Require endpoint-probes.tsv to exist")
    parser.add_argument("--require-seed-report", action="store_true", help="Require seed-report.json to exist")
    parser.add_argument("--skip-secret-scan", action="store_true", help="Skip high-confidence secret-pattern checks")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir).resolve()
    try:
        require(artifact_dir.exists(), f"artifact directory does not exist: {artifact_dir}")
        summary = validate_summary(artifact_dir)
        validate_manifest(artifact_dir, summary["status"])
        validate_endpoint_probes(artifact_dir, required_when_present=args.require_endpoint_probes)
        validate_seed_report(artifact_dir, required=args.require_seed_report or bool(summary.get("seedRequested")))
        if not args.skip_secret_scan:
            validate_no_obvious_secrets(artifact_dir)
    except AssertionError as exc:
        print(f"live artifact validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"live artifact validation passed: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
