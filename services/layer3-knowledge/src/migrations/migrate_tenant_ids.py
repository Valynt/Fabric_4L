"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Data migration script for adding tenant_id to existing Neo4j nodes.

This script migrates existing Neo4j graph data to include tenant_id for
multi-tenant isolation. It uses batched updates via APOC periodic iterate
to avoid locking the graph during migration.

Usage:
    # Set environment variables
    export NEO4J_URI="bolt://localhost:7687"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="password"
    export DEFAULT_TENANT_ID="system"
    
    # Run migration
    cd services/layer3-knowledge
    python -m src.migrations.migrate_tenant_ids

Or programmatically:
    from migrate_tenant_ids import TenantIdMigration
    migration = TenantIdMigration()
    await migration.run_migration(default_tenant_id="system")
"""

import asyncio
import logging
import os
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from value_fabric.shared.models.typed_dict import TypedDictModel


class TenantIdMigration_migrate_nativeResult(TypedDictModel):
    batches: Any
    errors: Any
    method: str
    total_updated: Any

class TenantIdMigration_create_constraintsResult(TypedDictModel):
    constraints: Any | None = None
    error: str
    status: str

class TenantIdMigration_migrate_with_apocResult(TypedDictModel):
    batches: Any
    error: str | None = None
    errors: Any
    method: str
    total_updated: Any
    update_stats: Any

class TenantIdMigration_run_migrationResult(TypedDictModel):
    default_tenant_id: Any | None = None
    message: str
    nodes_to_migrate: Any | None = None
    status: str
    total_updated: int

logger = logging.getLogger(__name__)


class TenantIdMigration:
    """Migrate existing Neo4j nodes to include tenant_id."""

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        """Initialize migration with Neo4j connection details.
        
        Args:
            uri: Neo4j bolt URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    async def close(self) -> None:
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def count_nodes_without_tenant(self) -> int:
        """Count nodes missing tenant_id."""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run("""
                MATCH (n)
                WHERE n.tenant_id IS NULL
                RETURN count(n) as count
            """)
            record = await result.single()
            return record["count"] if record else 0

    async def normalize_legacy_tenant_property_names(self) -> dict[str, int]:
        """Rename legacy `tenantId` property to canonical `tenant_id`.

        Returns:
            Mapping of label -> nodes normalized.
        """
        driver = await self._get_driver()
        labels = ["Formula", "Variable"]
        normalized: dict[str, int] = {}

        async with driver.session() as session:
            for label in labels:
                result = await session.run(
                    f"""
                    MATCH (n:{label})
                    WHERE n.tenant_id IS NULL AND n.tenantId IS NOT NULL
                    SET n.tenant_id = n.tenantId
                    REMOVE n.tenantId
                    RETURN count(n) as updated
                    """
                )
                record = await result.single()
                normalized[label] = int(record["updated"]) if record else 0

        return normalized

    async def backfill_tenant_for_expansion_labels(self, default_tenant_id: str) -> dict[str, int]:
        """Backfill `tenant_id` for labels identified in tenant-isolation expansion audit."""
        driver = await self._get_driver()
        labels = [
            "Formula",
            "Benchmark",
            "ValueModel",
            "BenchmarkPolicy",
            "FormulaVersion",
            "SourceBinding",
        ]
        updated_by_label: dict[str, int] = {}

        async with driver.session() as session:
            for label in labels:
                result = await session.run(
                    f"""
                    MATCH (n:{label})
                    WHERE n.tenant_id IS NULL
                    SET n.tenant_id = $tenant_id
                    RETURN count(n) as updated
                    """,
                    {"tenant_id": default_tenant_id},
                )
                record = await result.single()
                updated_by_label[label] = int(record["updated"]) if record else 0

        return updated_by_label

    async def check_apoc_available(self) -> bool:
        """Check if APOC plugin is available for batched migration."""
        driver = await self._get_driver()
        async with driver.session() as session:
            try:
                result = await session.run("RETURN apoc.version() as version")
                record = await result.single()
                return record is not None and record.get("version") is not None
            except Exception as e:
                logger.warning(f"APOC not available: {e}")
                return False

    async def migrate_with_apoc(
        self, 
        default_tenant_id: str = "system",
        batch_size: int = 1000,
        parallel: bool = True
    ) -> dict[str, Any]:
        """Migrate using APOC periodic iterate (efficient for large graphs).
        
        Args:
            default_tenant_id: Tenant ID to assign to existing nodes
            batch_size: Number of nodes per batch
            parallel: Whether to run batches in parallel
            
        Returns:
            Migration statistics
        """
        driver = await self._get_driver()
        
        # APOC periodic iterate for batched updates
        cypher = """
        CALL apoc.periodic.iterate(
            'MATCH (n) WHERE n.tenant_id IS NULL RETURN n',
            'SET n.tenant_id = $tenant_id',
            {
                batchSize: $batch_size,
                parallel: $parallel,
                params: {tenant_id: $tenant_id}
            }
        ) YIELD batches, total, errorMessages, updateStatistics
        RETURN batches, total, errorMessages, updateStatistics
        """
        
        async with driver.session() as session:
            result = await session.run(
                cypher,
                {
                    "tenant_id": default_tenant_id,
                    "batch_size": batch_size,
                    "parallel": parallel
                }
            )
            record = await result.single()
            
            if record:
                return TenantIdMigration_migrate_with_apocResult.model_validate({
                    "method": "apoc.periodic.iterate",
                    "batches": record["batches"],
                    "total_updated": record["total"],
                    "errors": record["errorMessages"],
                    "update_stats": record["updateStatistics"],
                })


            return TenantIdMigration_migrate_with_apocResult.model_validate({"method": "apoc.periodic.iterate", "error": "No result returned"})

    async def migrate_native(
        self,
        default_tenant_id: str = "system",
        batch_size: int = 1000
    ) -> dict[str, Any]:
        """Migrate using native Cypher (works without APOC).
        
        Args:
            default_tenant_id: Tenant ID to assign to existing nodes
            batch_size: Number of nodes per batch
            
        Returns:
            Migration statistics
        """
        driver = await self._get_driver()
        total_updated = 0
        batches = 0
        errors = []
        
        async with driver.session() as session:
            while True:
                # Update a batch of nodes
                result = await session.run("""
                    MATCH (n)
                    WHERE n.tenant_id IS NULL
                    WITH n LIMIT $batch_size
                    SET n.tenant_id = $tenant_id
                    RETURN count(n) as updated
                """, {"batch_size": batch_size, "tenant_id": default_tenant_id})
                
                record = await result.single()
                updated = record["updated"] if record else 0
                
                if updated == 0:
                    break
                    
                total_updated += updated
                batches += 1
                
                logger.info(f"Batch {batches}: Updated {updated} nodes with tenant_id={default_tenant_id}")
                
                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)
        
        return TenantIdMigration_migrate_nativeResult.model_validate({
            "method": "native_cypher",
            "batches": batches,
            "total_updated": total_updated,
            "errors": errors if errors else None,
        })


    async def run_migration(
        self,
        default_tenant_id: str = "system",
        batch_size: int = 1000,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Run the complete tenant_id migration.
        
        Args:
            default_tenant_id: Tenant ID to assign to existing nodes
            batch_size: Number of nodes per batch
            dry_run: If True, only count nodes without making changes
            
        Returns:
            Migration statistics
        """
        logger.info("Starting tenant_id migration...")
        alias_updates = await self.normalize_legacy_tenant_property_names()
        logger.info(f"Legacy tenant property normalization complete: {alias_updates}")
        expansion_updates = await self.backfill_tenant_for_expansion_labels(default_tenant_id)
        logger.info(f"Expansion label backfill complete: {expansion_updates}")
        
        # Count nodes needing migration
        count = await self.count_nodes_without_tenant()
        logger.info(f"Found {count} nodes without tenant_id")
        
        if dry_run:
            return TenantIdMigration_run_migrationResult.model_validate({
                "status": "dry_run",
                "nodes_to_migrate": count,
                "default_tenant_id": default_tenant_id,
            })


        
        if count == 0:
            logger.info("No migration needed - all nodes have tenant_id")
            return TenantIdMigration_run_migrationResult.model_validate({"status": "complete", "total_updated": 0, "message": "No migration needed"})
        
        # Check for APOC availability
        has_apoc = await self.check_apoc_available()
        
        if has_apoc:
            logger.info("Using APOC periodic iterate for batched migration")
            result = await self.migrate_with_apoc(default_tenant_id, batch_size)
        else:
            logger.info("Using native Cypher for batched migration")
            result = await self.migrate_native(default_tenant_id, batch_size)
        
        # Verify migration
        remaining = await self.count_nodes_without_tenant()
        result["nodes_remaining"] = remaining
        result["status"] = "complete" if remaining == 0 else "partial"
        
        logger.info(f"Migration complete: {result}")
        return result

    async def create_constraints(self) -> dict[str, Any]:
        """Create tenant_id constraints after migration.
        
        This should be run after all nodes have tenant_id set.
        """
        driver = await self._get_driver()
        results = []
        
        # Check remaining nodes without tenant_id
        remaining = await self.count_nodes_without_tenant()
        if remaining > 0:
            return TenantIdMigration_create_constraintsResult.model_validate({
                "error": f"Cannot create constraints: {remaining} nodes still missing tenant_id",
                "status": "failed"
            })


        
        # Create composite unique constraints for each entity type
        from schema.constraints import CONSTRAINTS
        
        async with driver.session() as session:
            for constraint in CONSTRAINTS:
                if "tenant" in constraint.name:
                    try:
                        await session.run(constraint.cypher)
                        results.append({
                            "constraint": constraint.name,
                            "status": "created"
                        })
                        logger.info(f"Created constraint: {constraint.name}")
                    except Exception as e:
                        if "already exists" in repr(e):
                            results.append({
                                "constraint": constraint.name,
                                "status": "already_exists"
                            })
                        else:
                            results.append({
                                "constraint": constraint.name,
                                "status": "failed",
                                "error": type(e).__name__,
                            })
        
        return TenantIdMigration_create_constraintsResult.model_validate({
            "status": "complete",
            "constraints": results
        })


async def main():
    """CLI entry point for migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Neo4j nodes to include tenant_id")
    parser.add_argument(
        "--default-tenant",
        default=os.getenv("DEFAULT_TENANT_ID", "system"),
        help="Default tenant ID for existing nodes (default: system)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of nodes per batch (default: 1000)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count nodes without making changes"
    )
    parser.add_argument(
        "--create-constraints",
        action="store_true",
        help="Create constraints after migration"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    migration = TenantIdMigration()
    
    try:
        if args.create_constraints:
            # Only create constraints
            result = await migration.create_constraints()
            print(f"\nConstraint creation result: {result}")
        else:
            # Run migration
            result = await migration.run_migration(
                default_tenant_id=args.default_tenant,
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
            print(f"\nMigration result: {result}")
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())
