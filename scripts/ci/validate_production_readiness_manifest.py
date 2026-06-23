#!/usr/bin/env python3
"""Validate the production-readiness gate evidence manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_REGRESSION_DOMAINS = {
    "architecture",
    "contracts",
    "operational-behavior",
    "security",
    "tenant-isolation",
}
ALLOWED_SUITE_STATUSES = {"passed", "failed", "not_run"}
ALLOWED_OVERALL_STATUSES = {"passed", "failed"}
ALLOWED_GATE_SCOPES = {"full", "subset"}
DEFAULT_MANIFEST = REPO_ROOT / "artifacts" / "production-readiness" / "manifest.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("manifest root must be a JSON object")
    return loaded


def _resolve_manifest_path(manifest_path: Path, artifact_path: str) -> Path:
    path = Path(artifact_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _validate_suite_entry(
    *,
    suite: Any,
    manifest_path: Path,
    artifact_dir: str,
) -> tuple[list[str], set[str], bool]:
    errors: list[str] = []

    if not isinstance(suite, dict):
        return ["suite entries must be objects"], set(), False

    name = suite.get("suite")
    status = suite.get("status")
    domains = suite.get("regression_domains")
    blocking = suite.get("blocking")
    returncode = suite.get("returncode")
    command = suite.get("command")
    junit_artifact = suite.get("junit_artifact")
    summary_artifact = suite.get("summary_artifact")

    label = name if isinstance(name, str) and name else "<unknown>"
    if not isinstance(name, str) or not name.strip():
        errors.append("suite entry missing non-empty suite")
    if status not in ALLOWED_SUITE_STATUSES:
        errors.append(f"{label}: invalid status {status!r}")
    if blocking is not True:
        errors.append(f"{label}: blocking must be true")
    if not isinstance(command, list) or not command:
        errors.append(f"{label}: command must be a non-empty list")
    if not isinstance(domains, list) or not domains:
        errors.append(f"{label}: regression_domains must be a non-empty list")
        domain_set: set[str] = set()
    else:
        domain_set = {domain for domain in domains if isinstance(domain, str)}
        invalid_domains = sorted(domain_set - REQUIRED_REGRESSION_DOMAINS)
        if len(domain_set) != len(domains):
            errors.append(f"{label}: regression_domains must contain strings only")
        if invalid_domains:
            errors.append(f"{label}: unknown regression domains {invalid_domains}")

    if status == "passed" and returncode != 0:
        errors.append(f"{label}: passed suite must have returncode 0")
    if status == "failed" and (not isinstance(returncode, int) or returncode == 0):
        errors.append(f"{label}: failed suite must have non-zero integer returncode")
    if status == "not_run" and returncode is not None:
        errors.append(f"{label}: not_run suite must have null returncode")

    executed = status in {"passed", "failed"}
    for key, artifact_value in (("junit_artifact", junit_artifact), ("summary_artifact", summary_artifact)):
        if not isinstance(artifact_value, str) or not artifact_value.strip():
            errors.append(f"{label}: {key} must be a non-empty string")
            continue

        artifact_path = _resolve_manifest_path(manifest_path, artifact_value)
        if executed and not artifact_path.exists():
            errors.append(f"{label}: {key} does not exist at {artifact_value}")

        normalized = artifact_value.replace("\\", "/")
        if not normalized.startswith(f"{artifact_dir.rstrip('/')}/"):
            errors.append(f"{label}: {key} must be under {artifact_dir}")

    return errors, domain_set if executed else set(), executed


def validate_manifest(path: Path) -> list[str]:
    manifest = _load_manifest(path)
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("gate") != "production-readiness-gate":
        errors.append("gate must be production-readiness-gate")
    if manifest.get("command") != "make production-readiness-gate":
        errors.append("command must be make production-readiness-gate")
    if manifest.get("overall_status") not in ALLOWED_OVERALL_STATUSES:
        errors.append(f"invalid overall_status {manifest.get('overall_status')!r}")
    if manifest.get("gate_scope") not in ALLOWED_GATE_SCOPES:
        errors.append(f"invalid gate_scope {manifest.get('gate_scope')!r}")
    if manifest.get("blocks_release_on_failure") is not True:
        errors.append("blocks_release_on_failure must be true")
    if not isinstance(manifest.get("release_authorizing"), bool):
        errors.append("release_authorizing must be a boolean")
    if not isinstance(manifest.get("generated_at_utc"), str) or not manifest["generated_at_utc"].endswith("Z"):
        errors.append("generated_at_utc must be an RFC3339 UTC string ending in Z")

    artifact_dir = manifest.get("artifact_dir")
    if not isinstance(artifact_dir, str) or not artifact_dir.strip():
        errors.append("artifact_dir must be a non-empty string")
        artifact_dir = "artifacts/production-readiness"

    required_domains = manifest.get("required_regression_domains")
    if set(required_domains if isinstance(required_domains, list) else []) != REQUIRED_REGRESSION_DOMAINS:
        errors.append(f"required_regression_domains must be exactly {sorted(REQUIRED_REGRESSION_DOMAINS)}")

    suites = manifest.get("suites")
    if not isinstance(suites, list) or not suites:
        return errors + ["suites must be a non-empty list"]

    suite_names: set[str] = set()
    duplicate_suites: set[str] = set()
    executed_domains: set[str] = set()
    statuses: list[str] = []
    executed_count = 0

    for suite in suites:
        suite_errors, suite_domains, executed = _validate_suite_entry(
            suite=suite,
            manifest_path=path,
            artifact_dir=artifact_dir,
        )
        errors.extend(suite_errors)
        if isinstance(suite, dict):
            name = suite.get("suite")
            status = suite.get("status")
            if isinstance(name, str):
                if name in suite_names:
                    duplicate_suites.add(name)
                suite_names.add(name)
            if isinstance(status, str):
                statuses.append(status)
        if executed:
            executed_count += 1
            executed_domains.update(suite_domains)

    if duplicate_suites:
        errors.append(f"duplicate suite entries: {sorted(duplicate_suites)}")

    covered_domains = manifest.get("covered_regression_domains")
    if set(covered_domains if isinstance(covered_domains, list) else []) != executed_domains:
        errors.append("covered_regression_domains must exactly match executed suite domains")

    overall_status = manifest.get("overall_status")
    stopped_on_failure = manifest.get("stopped_on_failure")
    gate_scope = manifest.get("gate_scope")
    release_authorizing = manifest.get("release_authorizing")
    if overall_status == "passed":
        if any(status != "passed" for status in statuses):
            errors.append("overall passed requires every suite status to be passed")
        if gate_scope == "full" and executed_domains != REQUIRED_REGRESSION_DOMAINS:
            errors.append("overall passed requires all required regression domains to be covered")
        if stopped_on_failure is not False:
            errors.append("overall passed requires stopped_on_failure=false")
    if release_authorizing is True and (gate_scope != "full" or overall_status != "passed"):
        errors.append("release_authorizing=true requires a full passed gate")
    if release_authorizing is True and executed_domains != REQUIRED_REGRESSION_DOMAINS:
        errors.append("release_authorizing=true requires all required regression domains to be covered")
    if gate_scope == "subset" and release_authorizing is not False:
        errors.append("subset manifests must set release_authorizing=false")
    if overall_status == "failed":
        if "failed" not in statuses and "not_run" not in statuses:
            errors.append("overall failed requires at least one failed or not_run suite")
        if "not_run" in statuses and stopped_on_failure is not True:
            errors.append("not_run suites require stopped_on_failure=true")
        if executed_count == 0:
            errors.append("overall failed manifest must include evidence from at least one executed suite")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    manifest_path = args.manifest if args.manifest.is_absolute() else REPO_ROOT / args.manifest
    if not manifest_path.exists():
        print(f"production readiness manifest not found: {manifest_path}")
        return 1

    try:
        errors = validate_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 - CLI should surface parse failures clearly.
        print(f"failed to parse production readiness manifest: {exc}")
        return 1

    if errors:
        print("production readiness manifest validation failed:")
        print("\n".join(f"  - {error}" for error in errors))
        return 1

    print("production readiness manifest schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
