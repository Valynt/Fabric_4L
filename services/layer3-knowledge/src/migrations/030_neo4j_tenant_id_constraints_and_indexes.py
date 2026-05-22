"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Phase 1.1 — Add NOT NULL constraints and lookup indexes on tenant_id
for the seven node labels used by the benchmarks, variables, models, and
formula_governance route modules.

Node labels covered:
    :Benchmark
    :BenchmarkPolicy
    :Variable
    :SourceBinding
    :ValueModel
    :Formula
    :FormulaVersion

For each label this migration creates:
1. A NOT NULL existence constraint on tenant_id (prevents nodes without the
   property from being written).
2. A btree index on tenant_id alone for fast tenant-scoped MATCH lookups.

All statements use IF NOT EXISTS so the migration is fully idempotent.

Usage:
    # Dry run (prints Cypher, makes no changes)
    python -m migrations.030_neo4j_tenant_id_constraints_and_indexes --dry-run

    # Execute
    python -m migrations.030_neo4j_tenant_id_constraints_and_indexes

Environment:
    NEO4J_URI       (default: bolt://localhost:7687)
    NEO4J_USER      (default: neo4j)
    NEO4J_PASSWORD  (required)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node labels that require tenant_id enforcement
# ---------------------------------------------------------------------------

_LABELS: list[str] = [
    "Benchmark",
    "BenchmarkPolicy",
    "Variable",
    "SourceBinding",
    "ValueModel",
    "Formula",
    "FormulaVersion",
]


def _constraint_name(label: str) -> str:
    return f"{label.lower()}_tenant_id_not_null"


def _index_name(label: str) -> str:
    return f"{label.lower()}_tenant_id_idx"


def _constraint_cypher(label: str) -> str:
    name = _constraint_name(label)
    return (
        f"CREATE CONSTRAINT {name} IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.tenant_id IS NOT NULL"
    )


def _index_cypher(label: str) -> str:
    name = _index_name(label)
    return (
        f"CREATE INDEX {name} IF NOT EXISTS "
        f"FOR (n:{label}) ON (n.tenant_id)"
    )


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    label: str
    statement_type: str  # "constraint" | "index"
    cypher: str
    status: str  # "created" | "already_exists" | "failed" | "dry_run"
    error: str | None = None


@dataclass
class MigrationResult:
    status: str  # "success" | "partial" | "dry_run" | "failed"
    created: int = 0
    already_exists: int = 0
    failed: int = 0
    steps: list[StepResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------


class TenantIdConstraintMigration:
    """Add NOT NULL constraints and tenant_id indexes for route-level node labels."""

    MIGRATION_ID = "030"
    DESCRIPTION = "tenant_id NOT NULL constraints + indexes for Benchmark/Variable/Model/Formula labels"

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "")

    async def run(self, dry_run: bool = False) -> MigrationResult:
        """Execute (or simulate) the migration."""
        if dry_run:
            return self._dry_run()

        try:
            from neo4j import AsyncGraphDatabase  # type: ignore[import]
        except ImportError:
            logger.error("neo4j driver not installed; cannot run migration")
            return MigrationResult(status="failed")

        result = MigrationResult(status="success")

        async with AsyncGraphDatabase.driver(
            self._uri, auth=(self._user, self._password)
        ) as driver:
            async with driver.session() as session:
                for label in _LABELS:
                    for stmt_type, cypher in [
                        ("constraint", _constraint_cypher(label)),
                        ("index", _index_cypher(label)),
                    ]:
                        step = await self._execute_step(
                            session, label, stmt_type, cypher
                        )
                        result.steps.append(step)
                        if step.status == "created":
                            result.created += 1
                        elif step.status == "already_exists":
                            result.already_exists += 1
                        elif step.status == "failed":
                            result.failed += 1
                            result.status = "partial"

        if result.failed == len(_LABELS) * 2:
            result.status = "failed"

        return result

    async def _execute_step(
        self,
        session: Any,
        label: str,
        stmt_type: str,
        cypher: str,
    ) -> StepResult:
        try:
            await session.run(cypher)
            logger.info("%-12s %-15s — OK", stmt_type, label)
            return StepResult(
                label=label,
                statement_type=stmt_type,
                cypher=cypher,
                status="created",
            )
        except Exception as exc:
            # Use the Neo4j driver's structured error code where available.
            # ClientError.code is stable across driver versions; string matching
            # on the message is not.
            error_code: str = getattr(exc, "code", "") or ""
            is_equivalent = (
                # Neo4j 5.x: EquivalentSchemaRuleAlreadyExists
                "EquivalentSchemaRule" in error_code
                # Neo4j 4.x: ConstraintAlreadyExists / IndexAlreadyExists
                or "AlreadyExists" in error_code
                # Fallback for drivers that don't expose .code (should not happen
                # with neo4j>=5, but kept as a last resort)
                or (not error_code and (
                    "already exists" in str(exc).lower()
                    or "equivalent" in str(exc).lower()
                ))
            )
            if is_equivalent:
                logger.debug("%-12s %-15s — already exists (code=%s)", stmt_type, label, error_code)
                return StepResult(
                    label=label,
                    statement_type=stmt_type,
                    cypher=cypher,
                    status="already_exists",
                )
            logger.error("%-12s %-15s — FAILED (code=%s): %s", stmt_type, label, error_code, exc)
            return StepResult(
                label=label,
                statement_type=stmt_type,
                cypher=cypher,
                status="failed",
                error=f"[{error_code}] {exc}" if error_code else str(exc),
            )

    def _dry_run(self) -> MigrationResult:
        result = MigrationResult(status="dry_run")
        for label in _LABELS:
            for stmt_type, cypher in [
                ("constraint", _constraint_cypher(label)),
                ("index", _index_cypher(label)),
            ]:
                print(f"[DRY RUN] {stmt_type:12s} {label:20s}  {cypher}")
                result.steps.append(
                    StepResult(
                        label=label,
                        statement_type=stmt_type,
                        cypher=cypher,
                        status="dry_run",
                    )
                )
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _main(dry_run: bool) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )
    migration = TenantIdConstraintMigration()
    result = await migration.run(dry_run=dry_run)

    print(
        f"\nMigration {TenantIdConstraintMigration.MIGRATION_ID} — {result.status.upper()}"
    )
    if not dry_run:
        print(f"  created:       {result.created}")
        print(f"  already_exists:{result.already_exists}")
        print(f"  failed:        {result.failed}")

    if result.failed:
        for step in result.steps:
            if step.status == "failed":
                print(f"  FAILED {step.statement_type} on :{step.label}: {step.error}")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=TenantIdConstraintMigration.DESCRIPTION
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Cypher statements without executing them",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(dry_run=args.dry_run)))
