from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Phase 2 Migration: L3 Tenant Property Standardization

This migration performs three operations:

1. RENAME: tenantId (camelCase) → tenant_id (snake_case) on :Formula and :Variable
2. BACKFILL: Add tenant_id = 'default' to nodes that never had a tenant property
3. VERIFY: Report counts and confirm all targeted nodes now have tenant_id

Target labels:
    - :Formula     (rename + backfill nulls)
    - :Variable    (rename + backfill nulls)
    - :ValueModel  (backfill only)
    - :Benchmark   (backfill only)
    - :BenchmarkPolicy (backfill only)
    - :FormulaVersion  (backfill only)
    - :SourceBinding   (backfill only)

Usage:
    # Dry run
    python -m services.layer3-knowledge.src.migrations.028_l3_tenant_standardization --dry-run

    # Execute
    python -m services.layer3-knowledge.src.migrations.028_l3_tenant_standardization

Environment:
    NEO4J_URI       (default: bolt://localhost:7687)
    NEO4J_USER      (default: neo4j)
    NEO4J_PASSWORD  (required)
    DEFAULT_TENANT  (default: default)
"""


import argparse
import asyncio
import logging
import os
import sys
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)

DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT", "default")

# ──────────────────────────────────────────────────────────────────────────────
# Migration steps
# ──────────────────────────────────────────────────────────────────────────────

RENAME_STEPS: list[dict[str, Any]] = [
    {
        "name": "rename_formula_tenantId",
        "description": "Rename tenantId → tenant_id on :Formula nodes",
        "label": "Formula",
        "count_cypher": "MATCH (f:Formula) WHERE f.tenantId IS NOT NULL RETURN count(f) as cnt",
        "migrate_cypher": """
            MATCH (f:Formula)
            WHERE f.tenantId IS NOT NULL
            SET f.tenant_id = f.tenantId
            REMOVE f.tenantId
            RETURN count(f) as cnt
        """,
    },
    {
        "name": "rename_variable_tenantId",
        "description": "Rename tenantId → tenant_id on :Variable nodes",
        "label": "Variable",
        "count_cypher": "MATCH (v:Variable) WHERE v.tenantId IS NOT NULL RETURN count(v) as cnt",
        "migrate_cypher": """
            MATCH (v:Variable)
            WHERE v.tenantId IS NOT NULL
            SET v.tenant_id = v.tenantId
            REMOVE v.tenantId
            RETURN count(v) as cnt
        """,
    },
]

BACKFILL_STEPS: list[dict[str, Any]] = [
    {
        "name": "backfill_formula",
        "label": "Formula",
        "description": "Backfill tenant_id on :Formula nodes missing it",
        "count_cypher": "MATCH (n:Formula) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:Formula)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_variable",
        "label": "Variable",
        "description": "Backfill tenant_id on :Variable nodes missing it",
        "count_cypher": "MATCH (n:Variable) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:Variable)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_valuemodel",
        "label": "ValueModel",
        "description": "Backfill tenant_id on :ValueModel nodes",
        "count_cypher": "MATCH (n:ValueModel) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:ValueModel)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_benchmark",
        "label": "Benchmark",
        "description": "Backfill tenant_id on :Benchmark nodes",
        "count_cypher": "MATCH (n:Benchmark) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:Benchmark)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_benchmarkpolicy",
        "label": "BenchmarkPolicy",
        "description": "Backfill tenant_id on :BenchmarkPolicy nodes",
        "count_cypher": "MATCH (n:BenchmarkPolicy) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:BenchmarkPolicy)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_formulaversion",
        "label": "FormulaVersion",
        "description": "Backfill tenant_id on :FormulaVersion nodes",
        "count_cypher": "MATCH (n:FormulaVersion) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:FormulaVersion)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
    {
        "name": "backfill_sourcebinding",
        "label": "SourceBinding",
        "description": "Backfill tenant_id on :SourceBinding nodes",
        "count_cypher": "MATCH (n:SourceBinding) WHERE n.tenant_id IS NULL RETURN count(n) as cnt",
        "migrate_cypher": """
            MATCH (n:SourceBinding)
            WHERE n.tenant_id IS NULL
            SET n.tenant_id = $tenant_id
            RETURN count(n) as cnt
        """,
    },
]

# Labels to verify after migration
VERIFICATION_LABELS = [
    "Formula",
    "Variable",
    "ValueModel",
    "Benchmark",
    "BenchmarkPolicy",
    "FormulaVersion",
    "SourceBinding",
]


class L3TenantStandardizationMigration:
    """Phase 2 migration: standardize tenant properties across L3 labels."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        default_tenant_id: str = DEFAULT_TENANT_ID,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.default_tenant_id = default_tenant_id
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            if not self.password:
                raise RuntimeError(
                    "Neo4j password required. Set NEO4J_PASSWORD environment variable."
                )
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        return self._driver

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    # ── Inventory ────────────────────────────────────────────────────────────

    async def inventory(self) -> dict[str, Any]:
        """Count nodes per label, split by tenant property status."""
        driver = await self._get_driver()
        results: dict[str, Any] = {"labels": {}}

        async with driver.session() as session:
            for label in VERIFICATION_LABELS:
                # Total nodes
                total_result = await session.run(
                    f"MATCH (n:{label}) RETURN count(n) as total"
                )
                total_record = await total_result.single()
                total = total_record["total"] if total_record else 0

                # Nodes with tenant_id
                has_result = await session.run(
                    f"MATCH (n:{label}) WHERE n.tenant_id IS NOT NULL RETURN count(n) as has_tenant_id"
                )
                has_record = await has_result.single()
                has_tenant_id = has_record["has_tenant_id"] if has_record else 0

                # Nodes with tenantId (old camelCase)
                old_result = await session.run(
                    f"MATCH (n:{label}) WHERE n.tenantId IS NOT NULL RETURN count(n) as has_old_tenantId"
                )
                old_record = await old_result.single()
                has_old_tenant_id = old_record["has_old_tenantId"] if old_record else 0

                results["labels"][label] = {
                    "total": total,
                    "has_tenant_id": has_tenant_id,
                    "has_old_tenantId": has_old_tenant_id,
                    "missing_any": total - has_tenant_id - has_old_tenant_id,
                }

        return results

    # ── Rename ───────────────────────────────────────────────────────────────

    async def run_renames(self, dry_run: bool = False) -> dict[str, Any]:
        """Rename tenantId → tenant_id on :Formula and :Variable."""
        driver = await self._get_driver()
        results: dict[str, Any] = {"dry_run": dry_run, "steps": []}

        for step in RENAME_STEPS:
            if dry_run:
                async with driver.session() as session:
                    result = await session.run(step["count_cypher"])
                    record = await result.single()
                    count = record["cnt"] if record else 0

                results["steps"].append(
                    {
                        "name": step["name"],
                        "description": step["description"],
                        "would_rename": count,
                        "status": "dry_run",
                    }
                )
                logger.info(f"[DRY RUN] {step['description']}: would rename {count} nodes")
            else:
                async with driver.session() as session:
                    result = await session.run(step["migrate_cypher"])
                    record = await result.single()
                    count = record["cnt"] if record else 0

                results["steps"].append(
                    {
                        "name": step["name"],
                        "description": step["description"],
                        "renamed": count,
                        "status": "completed",
                    }
                )
                logger.info(f"{step['description']}: renamed {count} nodes")

        return results

    # ── Backfill ─────────────────────────────────────────────────────────────

    async def run_backfills(self, dry_run: bool = False) -> dict[str, Any]:
        """Backfill tenant_id on nodes that never had it."""
        driver = await self._get_driver()
        results: dict[str, Any] = {"dry_run": dry_run, "steps": []}

        for step in BACKFILL_STEPS:
            if dry_run:
                async with driver.session() as session:
                    result = await session.run(step["count_cypher"])
                    record = await result.single()
                    count = record["cnt"] if record else 0

                results["steps"].append(
                    {
                        "name": step["name"],
                        "label": step["label"],
                        "description": step["description"],
                        "would_backfill": count,
                        "status": "dry_run",
                    }
                )
                logger.info(f"[DRY RUN] {step['description']}: would backfill {count} nodes")
            else:
                async with driver.session() as session:
                    result = await session.run(
                        step["migrate_cypher"], {"tenant_id": self.default_tenant_id}
                    )
                    record = await result.single()
                    count = record["cnt"] if record else 0

                results["steps"].append(
                    {
                        "name": step["name"],
                        "label": step["label"],
                        "description": step["description"],
                        "backfilled": count,
                        "status": "completed",
                    }
                )
                logger.info(f"{step['description']}: backfilled {count} nodes")

        return results

    # ── Verify ───────────────────────────────────────────────────────────────

    async def verify(self) -> dict[str, Any]:
        """Post-migration verification: ensure all nodes have tenant_id."""
        driver = await self._get_driver()
        results: dict[str, Any] = {"labels": {}, "all_passed": True}

        async with driver.session() as session:
            for label in VERIFICATION_LABELS:
                result = await session.run(
                    f"""
                    MATCH (n:{label})
                    RETURN
                        count(n) as total,
                        count(CASE WHEN n.tenant_id IS NOT NULL THEN 1 END) as has_tenant_id,
                        count(CASE WHEN n.tenantId IS NOT NULL THEN 1 END) as has_old_tenantId
                    """
                )
                record = await result.single()
                total = record["total"] if record else 0
                has_tenant_id = record["has_tenant_id"] if record else 0
                has_old = record["has_old_tenantId"] if record else 0

                passed = total == has_tenant_id and has_old == 0
                if not passed:
                    results["all_passed"] = False

                results["labels"][label] = {
                    "total": total,
                    "has_tenant_id": has_tenant_id,
                    "has_old_tenantId": has_old,
                    "passed": passed,
                }

        return results

    # ── Orchestration ────────────────────────────────────────────────────────

    async def run(
        self, dry_run: bool = False, skip_rename: bool = False, skip_backfill: bool = False
    ) -> dict[str, Any]:
        """Run the complete Phase 2 migration."""
        logger.info("=" * 60)
        logger.info("L3 Tenant Standardization Migration (Phase 2)")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info(f"Default tenant_id: {self.default_tenant_id}")
        logger.info("=" * 60)

        # Pre-migration inventory
        logger.info("\n--- Pre-migration inventory ---")
        pre_inventory = await self.inventory()
        for label, counts in pre_inventory["labels"].items():
            logger.info(
                f"  {label}: total={counts['total']}, "
                f"has_tenant_id={counts['has_tenant_id']}, "
                f"has_old_tenantId={counts['has_old_tenantId']}, "
                f"missing={counts['missing_any']}"
            )

        results: dict[str, Any] = {
            "dry_run": dry_run,
            "default_tenant_id": self.default_tenant_id,
            "pre_inventory": pre_inventory,
        }

        # Rename step
        if not skip_rename:
            logger.info("\n--- Rename tenantId → tenant_id ---")
            results["rename"] = await self.run_renames(dry_run=dry_run)

        # Backfill step
        if not skip_backfill:
            logger.info("\n--- Backfill missing tenant_id ---")
            results["backfill"] = await self.run_backfills(dry_run=dry_run)

        # Post-migration verification (only if not dry run)
        if not dry_run:
            logger.info("\n--- Post-migration verification ---")
            results["verification"] = await self.verify()
            for label, v in results["verification"]["labels"].items():
                status = "PASS" if v["passed"] else "FAIL"
                logger.info(
                    f"  {label}: total={v['total']}, "
                    f"has_tenant_id={v['has_tenant_id']}, "
                    f"has_old_tenantId={v['has_old_tenantId']} → {status}"
                )

            if not results["verification"]["all_passed"]:
                logger.error("\n*** VERIFICATION FAILED ***")
                logger.error("Some nodes still missing tenant_id or have old tenantId property.")
                results["status"] = "verification_failed"
            else:
                logger.info("\n*** ALL VERIFICATION CHECKS PASSED ***")
                results["status"] = "complete"
        else:
            results["status"] = "dry_run_complete"

        return results


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2: L3 Tenant Property Standardization Migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--skip-rename",
        action="store_true",
        help="Skip the tenantId → tenant_id rename step",
    )
    parser.add_argument(
        "--skip-backfill",
        action="store_true",
        help="Skip the backfill step",
    )
    parser.add_argument(
        "--default-tenant",
        default=os.getenv("DEFAULT_TENANT", "default"),
        help="Default tenant_id for backfilled nodes (default: default)",
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j bolt URI",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD"),
        help="Neo4j password (or set NEO4J_PASSWORD env var)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    migration = L3TenantStandardizationMigration(
        uri=args.uri,
        user=args.user,
        password=args.password,
        default_tenant_id=args.default_tenant,
    )

    try:
        results = await migration.run(
            dry_run=args.dry_run,
            skip_rename=args.skip_rename,
            skip_backfill=args.skip_backfill,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Status: {results['status']}")
        print(f"Mode: {'dry run' if results['dry_run'] else 'live'}")

        if "rename" in results:
            print("\nRename results:")
            for step in results["rename"]["steps"]:
                if results["dry_run"]:
                    print(f"  {step['name']}: would rename {step.get('would_rename', 0)} nodes")
                else:
                    print(f"  {step['name']}: renamed {step.get('renamed', 0)} nodes")

        if "backfill" in results:
            print("\nBackfill results:")
            for step in results["backfill"]["steps"]:
                if results["dry_run"]:
                    print(f"  {step['name']}: would backfill {step.get('would_backfill', 0)} nodes")
                else:
                    print(f"  {step['name']}: backfilled {step.get('backfilled', 0)} nodes")

        if "verification" in results:
            print("\nVerification:")
            for label, v in results["verification"]["labels"].items():
                status = "PASS" if v["passed"] else "FAIL"
                print(
                    f"  {label}: {v['has_tenant_id']}/{v['total']} have tenant_id, "
                    f"{v['has_old_tenantId']} still have old tenantId → {status}"
                )

        return 0 if results["status"] in ("complete", "dry_run_complete") else 1

    except Exception:
        logger.exception("Migration failed")
        return 1
    finally:
        await migration.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
