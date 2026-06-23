"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Create composite (tenant_id, name) indexes for efficient tenant-scoped lookups.

This migration script creates composite btree indexes on (tenant_id, name) for
all major entity types to optimize tenant-scoped queries. These indexes improve
performance for queries that filter by both tenant_id and name, which is a common
pattern in multi-tenant applications.

The following indexes are created:
- capability_tenant_name_idx on Capability(tenant_id, name)
- usecase_tenant_name_idx on UseCase(tenant_id, name)
- persona_tenant_name_idx on Persona(tenant_id, name)
- valuedriver_tenant_name_idx on ValueDriver(tenant_id, name)
- product_tenant_name_idx on Product(tenant_id, name)
- organization_tenant_name_idx on Organization(tenant_id, name)
- painsignal_tenant_name_idx on PainSignal(tenant_id, name)
- evidence_tenant_name_idx on Evidence(tenant_id, name)

Usage:
    # Set environment variables
    export NEO4J_URI="bolt://localhost:7687"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="password"
    
    # Run migration
    python -m services.layer3-knowledge.src.migrations.create_composite_tenant_indexes

Or programmatically:
    from create_composite_tenant_indexes import CompositeTenantIndexMigration
    migration = CompositeTenantIndexMigration()
    await migration.run_migration()
"""

import asyncio
import logging
import os

from neo4j import AsyncDriver, AsyncGraphDatabase
from value_fabric.shared.models.typed_dict import TypedDictModel

logger = logging.getLogger(__name__)


class CompositeTenantIndexMigration_createIndexResult(TypedDictModel):
    index_name: str
    status: str
    error: str | None = None


class CompositeTenantIndexMigration_runMigrationResult(TypedDictModel):
    status: str
    indexes_created: int
    indexes_already_exist: int
    indexes_failed: int
    results: list[CompositeTenantIndexMigration_createIndexResult]


class CompositeTenantIndexMigration:
    """Migration to create composite (tenant_id, name) indexes for tenant-scoped lookups."""

    # Index definitions: (label, properties, index_name)
    INDEXES: list[tuple[str, list[str], str]] = [
        ("Capability", ["tenant_id", "name"], "capability_tenant_name_idx"),
        ("UseCase", ["tenant_id", "name"], "usecase_tenant_name_idx"),
        ("Persona", ["tenant_id", "name"], "persona_tenant_name_idx"),
        ("ValueDriver", ["tenant_id", "name"], "valuedriver_tenant_name_idx"),
        ("Product", ["tenant_id", "name"], "product_tenant_name_idx"),
        ("Organization", ["tenant_id", "name"], "organization_tenant_name_idx"),
        ("PainSignal", ["tenant_id", "name"], "painsignal_tenant_name_idx"),
        ("Evidence", ["tenant_id", "name"], "evidence_tenant_name_idx"),
    ]

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize migration with Neo4j connection details.

        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        return self._driver

    async def close(self) -> None:
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def create_index(
        self,
        label: str,
        properties: list[str],
        index_name: str,
    ) -> CompositeTenantIndexMigration_createIndexResult:
        """Create a composite btree index for a label.

        Args:
            label: Node label (e.g., "Capability")
            properties: List of property names (e.g., ["tenant_id", "name"])
            index_name: Name for the index

        Returns:
            Result dict with status and error if any
        """
        driver = await self._get_driver()
        
        # Build Cypher CREATE INDEX statement with dynamic properties
        props_str = ", ".join(f"n.{p}" for p in properties)
        cypher = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON ({props_str})"
        
        async with driver.session() as session:
            try:
                await session.run(cypher)
                logger.info(f"Created index: {index_name}")
                return CompositeTenantIndexMigration_createIndexResult(
                    index_name=index_name,
                    status="created",
                    error=None
                )
            except Exception as e:
                error_msg = repr(e)
                if "already exists" in error_msg or "EquivalentSchemaRule" in error_msg:
                    logger.info(f"Index already exists: {index_name}")
                    return CompositeTenantIndexMigration_createIndexResult(
                        index_name=index_name,
                        status="already_exists",
                        error=None
                    )
                else:
                    logger.error(f"Failed to create index {index_name}: {e}")
                    return CompositeTenantIndexMigration_createIndexResult(
                        index_name=index_name,
                        status="failed",
                        error=type(e).__name__,
                    )

    async def run_migration(self) -> CompositeTenantIndexMigration_runMigrationResult:
        """Run the complete index migration.

        Returns:
            Migration result with statistics
        """
        logger.info("Starting composite tenant index migration...")
        
        results = []
        indexes_created = 0
        indexes_already_exist = 0
        indexes_failed = 0
        
        for label, properties, index_name in self.INDEXES:
            result = await self.create_index(label, properties, index_name)
            results.append(result)
            
            if result["status"] == "created":
                indexes_created += 1
            elif result["status"] == "already_exists":
                indexes_already_exist += 1
            else:
                indexes_failed += 1
        
        logger.info(
            f"Migration complete: {indexes_created} created, "
            f"{indexes_already_exist} already exist, {indexes_failed} failed"
        )
        
        return CompositeTenantIndexMigration_runMigrationResult(
            status="complete",
            indexes_created=indexes_created,
            indexes_already_exist=indexes_already_exist,
            indexes_failed=indexes_failed,
            results=results,
        )


async def main() -> None:
    """CLI entry point for migration."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create composite (tenant_id, name) indexes for tenant-scoped lookups"
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI"
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD", "password"),
        help="Neo4j password"
    )
    
    args = parser.parse_args()
    
    migration = CompositeTenantIndexMigration(
        uri=args.uri,
        user=args.user,
        password=args.password,
    )
    
    try:
        result = await migration.run_migration()
        print("\nMigration result:")
        print(f"  Status: {result['status']}")
        print(f"  Indexes created: {result['indexes_created']}")
        print(f"  Indexes already exist: {result['indexes_already_exist']}")
        print(f"  Indexes failed: {result['indexes_failed']}")
        
        if result['indexes_failed'] > 0:
            print("\nFailed indexes:")
            for r in result['results']:
                if r['status'] == 'failed':
                    print(f"  - {r['index_name']}: {r['error']}")
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())
