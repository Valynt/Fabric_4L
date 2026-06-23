#!/usr/bin/env python3
"""Validate that WAL-G physical backups are enabled only with restore evidence.

The base PostgreSQL backup CronJob keeps physical WAL-G backup-push disabled
until a non-production restore drill has produced redacted evidence. This gate
allows platform owners to flip ENABLE_WALG_BACKUP to true only when the
corresponding evidence artifact proves backup-push, backup-fetch, integrity
checks, timing, and SRE approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CRONJOB = ROOT / "k8s/base/postgres-backup-cronjob.yaml"
DEFAULT_EVIDENCE = ROOT / "docs/launch/evidence/walg-restore-drill-evidence.json"
SCHEMA_VERSION = "walg-physical-backup-restore-evidence.v1"
PASS_STATUSES = {"pass", "PASS", "PASS_WITH_EVIDENCE"}
NON_PRODUCTION_ENVIRONMENTS = {"staging", "non-production", "non_production", "test", "drill"}


class GateError(ValueError):
    """Raised when WAL-G enablement evidence is missing or invalid."""


def _load_yaml_documents(path: Path) -> list[Any]:
    return list(yaml.safe_load_all(path.read_text(encoding="utf-8")))


def _iter_containers(document: dict[str, Any]) -> list[dict[str, Any]]:
    spec = document.get("spec") or {}
    job_template = spec.get("jobTemplate") or {}
    pod_spec = (((job_template.get("spec") or {}).get("template") or {}).get("spec") or {})
    containers = pod_spec.get("containers") or []
    return [container for container in containers if isinstance(container, dict)]


def walg_enabled(cronjob_path: Path) -> bool:
    if not cronjob_path.exists():
        raise GateError(f"CronJob manifest not found: {cronjob_path}")

    enabled_values: list[str] = []
    for document in _load_yaml_documents(cronjob_path):
        if not isinstance(document, dict):
            continue
        if document.get("kind") != "CronJob":
            continue
        metadata = document.get("metadata") or {}
        if metadata.get("name") != "postgres-backup":
            continue
        for container in _iter_containers(document):
            for env_var in container.get("env") or []:
                if isinstance(env_var, dict) and env_var.get("name") == "ENABLE_WALG_BACKUP":
                    value = str(env_var.get("value", "")).strip().lower()
                    if value:
                        enabled_values.append(value)

    return any(value == "true" for value in enabled_values)


def _require_mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def _require_non_empty_string(value: Any, path: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")
        return ""
    return value.strip()


def validate_evidence(evidence_path: Path) -> list[str]:
    errors: list[str] = []
    if not evidence_path.exists():
        return [f"WAL-G restore drill evidence not found: {evidence_path}"]

    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"WAL-G restore drill evidence is not valid JSON: {exc}"]

    root = _require_mapping(evidence, "evidence", errors)
    schema_version = _require_non_empty_string(root.get("schema_version"), "schema_version", errors)
    if schema_version and schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    status = _require_non_empty_string(root.get("status"), "status", errors)
    if status and status not in PASS_STATUSES:
        errors.append("status must record a passing restore drill")

    environment = _require_non_empty_string(root.get("environment"), "environment", errors)
    if environment and environment.lower() not in NON_PRODUCTION_ENVIRONMENTS:
        errors.append("environment must be a non-production restore target")

    for field in ("generated_at_utc", "release_candidate_sha"):
        _require_non_empty_string(root.get(field), field, errors)

    backup = _require_mapping(root.get("backup"), "backup", errors)
    restore = _require_mapping(root.get("restore"), "restore", errors)
    validations = _require_mapping(root.get("validations"), "validations", errors)
    approvals = _require_mapping(root.get("approvals"), "approvals", errors)

    backup_method = _require_non_empty_string(backup.get("method"), "backup.method", errors)
    if backup_method and "wal-g backup-push" not in backup_method.lower():
        errors.append("backup.method must include wal-g backup-push")
    artifact_uri = _require_non_empty_string(backup.get("artifact_uri"), "backup.artifact_uri", errors)
    if artifact_uri and not artifact_uri.startswith(("s3://", "gs://", "azure://")):
        errors.append("backup.artifact_uri must reference durable object storage")
    _require_non_empty_string(backup.get("completed_at_utc"), "backup.completed_at_utc", errors)

    restore_method = _require_non_empty_string(restore.get("method"), "restore.method", errors)
    if restore_method and "wal-g backup-fetch" not in restore_method.lower():
        errors.append("restore.method must include wal-g backup-fetch")
    _require_non_empty_string(restore.get("target"), "restore.target", errors)
    _require_non_empty_string(restore.get("completed_at_utc"), "restore.completed_at_utc", errors)
    for numeric_field in ("rto_seconds", "rpo_seconds"):
        value = restore.get(numeric_field)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"restore.{numeric_field} must be a positive integer")

    if validations.get("data_integrity") not in PASS_STATUSES:
        errors.append("validations.data_integrity must pass")
    if validations.get("tenant_checksums_match") is not True:
        errors.append("validations.tenant_checksums_match must be true")
    if validations.get("application_smoke") not in PASS_STATUSES:
        errors.append("validations.application_smoke must pass")
    if validations.get("logs_redacted") is not True:
        errors.append("validations.logs_redacted must be true")

    _require_non_empty_string(approvals.get("sre_owner"), "approvals.sre_owner", errors)
    _require_non_empty_string(approvals.get("approved_at_utc"), "approvals.approved_at_utc", errors)

    return errors


def validate_gate(cronjob_path: Path, evidence_path: Path) -> list[str]:
    if not walg_enabled(cronjob_path):
        return []
    return validate_evidence(evidence_path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Gate WAL-G physical-backup enablement on restore evidence")
    parser.add_argument("--cronjob", type=Path, default=DEFAULT_CRONJOB, help="postgres-backup CronJob manifest")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=DEFAULT_EVIDENCE,
        help="redacted WAL-G restore drill evidence JSON",
    )
    args = parser.parse_args(argv)

    cronjob_path = args.cronjob if args.cronjob.is_absolute() else ROOT / args.cronjob
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence

    try:
        errors = validate_gate(cronjob_path, evidence_path)
    except GateError as exc:
        errors = [str(exc)]

    if errors:
        print("WAL-G physical backup enablement gate failed:")
        print("\n".join(f"  - {error}" for error in errors))
        return 1

    if walg_enabled(cronjob_path):
        print(f"WAL-G physical backup enablement evidence OK: {evidence_path}")
    else:
        print("WAL-G physical backups remain disabled; no restore evidence required yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
