#!/usr/bin/env python3
"""Validate static database readiness governance docs.

The database gate must remain local and non-destructive, so this script checks
that the repository-owned DB compatibility matrix and migration governance docs
cover the service paths, runtime invariants, and CI entrypoints that release
candidate review depends on.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RequiredDoc:
    path: Path
    required_terms: tuple[str, ...]


DOCS = (
    RequiredDoc(
        Path("docs/reference/database-runtime-compatibility-matrix.md"),
        (
            "RuntimeDatabaseAdapter",
            "Allowed production drivers",
            "Shared adapter required",
            "INTENTIONAL_DB_ADAPTER_BYPASS",
            "SET LOCAL app.tenant_id",
            "SELECT 1",
            "services/layer1-ingestion/src/shared/database.py",
            "services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py",
            "services/layer4-agents/src/database.py",
            "services/layer5-ground-truth/src/layer5_ground_truth/database.py",
            "services/layer6-benchmarks/src/database.py",
        ),
    ),
    RequiredDoc(
        Path("docs/reference/migration-reproducibility-invariants.md"),
        (
            "check_migration_entrypoints.py",
            "services/layer1-ingestion/migrations/versions/",
            "services/layer2-extraction/migrations/versions/",
            "services/layer3-knowledge/src/migrations/",
            "services/layer4-agents/migrations/versions/",
            "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/",
            "services/layer6-benchmarks/migrations/versions/",
            "Validate tenant isolation",
        ),
    ),
    RequiredDoc(
        Path("docs/operations/migration-verification-checklist.md"),
        (
            "migration_verification_checklist.sh",
            "Layer 3 audited graph-write migration checklist item",
            "AuditedGraphMutation",
            "check_layer3_audited_relationship_writes.py",
        ),
    ),
)


def main() -> int:
    errors: list[str] = []
    for doc in DOCS:
        full_path = ROOT / doc.path
        if not full_path.is_file():
            errors.append(f"missing required database governance doc: {doc.path}")
            continue
        text = full_path.read_text(encoding="utf-8")
        if not text.strip():
            errors.append(f"required database governance doc is empty: {doc.path}")
            continue
        for term in doc.required_terms:
            if term not in text:
                errors.append(f"{doc.path}: missing required term {term!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Database governance docs validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
