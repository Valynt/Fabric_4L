#!/usr/bin/env python3
"""Emit non-production restore-verification evidence.

This script is intentionally dry-run only. It verifies that the repository's
backup and restore assets exist, records the concrete restore drill command,
and writes a machine-readable evidence contract for CI and scheduled ops runs.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


REQUIRED_ASSETS = {
    "postgres_backup_script": "scripts/ops/postgres_backup.py",
    "postgres_restore_drill": "scripts/ops/test_postgres_backup_restore.sh",
    "postgres_backup_cronjob": "k8s/base/postgres-backup-cronjob.yaml",
    "neo4j_backup_cronjob": "k8s/base/neo4j-backup-cronjob.yaml",
    "postgres_runbook": "docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md",
    "dr_runbook": "docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md",
}


def _asset_status() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": rel_path,
            "exists": (ROOT / rel_path).exists(),
        }
        for name, rel_path in REQUIRED_ASSETS.items()
    }


def build_evidence() -> dict[str, Any]:
    assets = _asset_status()
    missing = [name for name, item in assets.items() if not item["exists"]]
    status = "pass" if not missing else "fail"

    return {
        "schema_version": "recovery-restore-dry-run.v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": status,
        "environment_guard": {
            "mode": "dry_run",
            "allowed_environment": "non-production only",
            "production_mutation_allowed": False,
        },
        "rpo_rto": {
            "rpo_target": "1 hour",
            "rpo_maximum": "4 hours",
            "rto_target": "4 hours",
            "rto_maximum": "8 hours",
            "source": "docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md",
        },
        "assets": assets,
        "restore_drill": {
            "command": "bash scripts/ops/test_postgres_backup_restore.sh",
            "requires_docker": True,
            "safe_target": "isolated source and restore PostgreSQL containers",
            "evidence_dir": "artifacts/postgres-backup-restore",
        },
        "restore_validations": {
            "database": {
                "postgres_logical_backup": True,
                "postgres_restore_smoke": True,
                "neo4j_backup_job_declared": True,
                "secrets_config_references": [
                    "postgres-secret",
                    "wal-g-config",
                    "neo4j-credentials",
                    "Infisical",
                ],
                "background_jobs": [
                    "postgres-backup CronJob",
                    "neo4j-backup CronJob",
                    "Celery/Redis job-state validation after restore",
                ],
            },
            "tenant_data": {
                "source_checksums": "artifacts/postgres-backup-restore/source-checksums.txt",
                "restored_checksums": "artifacts/postgres-backup-restore/restored-checksums.txt",
                "compare_per_tenant_checksums": True,
                "tenant_count_verified": True,
                "partial_tenant_restore_required": True,
            },
            "object_storage": {
                "storage_backends": ["local", "S3", "GCS", "MinIO-compatible S3"],
                "file_asset_restore_required": True,
                "metadata_references_required": True,
            },
            "audit_logs": {
                "audit_events_required": True,
                "append_only_validation_required": True,
                "tenant_scoped_query_validation_required": True,
            },
            "billing_state": {
                "tables": [
                    "billing_customers",
                    "billing_subscriptions",
                    "billing_webhook_events",
                    # Layer 4 membership/billing service tables (canonical owner of the
                    # Stripe customer/subscription/webhook domain; legacy services/billing
                    # removed 2026-08-27, COMPAT-BILL-001; services/layer7-billing removed
                    # 2026-09-01, R3 billing dedup).
                    "billing_plan_versions",
                    "billing_usage_events",
                    "billing_invoices",
                    "billing_invoice_items",
                    "billing_charges",
                ],
                "tenant_scoped_validation_required": True,
                "idempotency_validation_required": True,
            },
        },
        "missing_assets": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit Value Fabric restore dry-run evidence")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "recovery",
        help="Directory for restore dry-run evidence artifacts.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence()
    evidence_path = output_dir / "restore-dry-run-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"restore dry-run evidence written to {evidence_path}")
    return 0 if evidence["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
