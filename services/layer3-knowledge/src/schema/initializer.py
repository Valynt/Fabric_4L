"""Schema initializer for Neo4j Knowledge Graph."""

import logging
from typing import TYPE_CHECKING, Any

from neo4j import AsyncDriver
from neo4j.exceptions import (
    ClientError,
    ConfigurationError,
    DatabaseError,
    ServiceUnavailable,
    TransientError,
)
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config import Settings, get_settings
from ..db.driver import get_driver
from ..schema.constraints import (
    CONSTRAINTS,
    INDEXES,
    TENANT_CONSTRAINTS,
    Constraint,
    Index,
)


class SchemaInitializer_health_checkResult(TypedDictModel):
    database: Any
    error: str | None = None
    status: str
    uri: Any

if TYPE_CHECKING:
    from neo4j import AsyncSession

logger = logging.getLogger(__name__)

# Error message patterns for resilient matching
_ERROR_ALREADY_EXISTS = "already exists"
_ERROR_CONSTRAINT_EXISTS = "constraint already exists"
_ERROR_INDEX_EXISTS = "index already exists"


class SchemaInitializer:
    """Initialize and manage Neo4j schema for Value Fabric."""

    def __init__(
        self, driver: AsyncDriver | None = None, settings: Settings | None = None
    ):
        """Initialize schema manager.

        Args:
            driver: Neo4j async driver. If None, creates new connection.
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None
        self._edition: str | None = None

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver via the shared singleton factory."""
        if self._driver is None:
            self._driver = await get_driver(self.settings)
        return self._driver

    async def close(self) -> None:
        """Close Neo4j driver if owned."""
        if self._owned_driver and self._driver:
            await self._driver.close()
            self._driver = None

    def _get_edition(self, edition: str | None = None) -> str:
        """Get effective edition with fallback chain.

        Args:
            edition: Optional edition override. Falls back to cached edition,
                     then defaults to "community".

        Returns:
            Effective edition string
        """
        return edition or self._edition or "community"

    async def _detect_edition(self, session: "AsyncSession") -> str:
        """Detect Neo4j edition (community or enterprise).

        Args:
            session: Neo4j async session

        Returns:
            Edition string: "community", "enterprise", or "unknown"
        """
        try:
            result = await session.run("CALL dbms.components() YIELD edition RETURN edition")
            record = await result.single()
            edition = record["edition"].lower() if record else "unknown"
            return edition
        except (ClientError, DatabaseError) as e:
            logger.warning(
                "Failed to detect Neo4j edition, assuming community",
                extra={"error_code": "NEO4J_EDITION_DETECTION_ERROR", "error": sanitize_log_error(e), "error_type": type(e).__name__},
            )
            return "community"

    def _is_enterprise(self, edition: str | None = None) -> bool:
        """Check if running on Neo4j Enterprise Edition.

        Args:
            edition: Edition string. If None, uses cached edition from detection.

        Returns:
            True if Enterprise Edition, False otherwise
        """
        return self._get_edition(edition) == "enterprise"

    def _get_constraints_for_edition(self, edition: str | None = None) -> list[Constraint]:
        """Get constraints appropriate for the Neo4j edition.

        Args:
            edition: Edition string. If None, uses cached edition.

        Returns:
            List of constraints to create for this edition
        """
        if self._is_enterprise(edition):
            # Enterprise gets all constraints including property existence
            return CONSTRAINTS + TENANT_CONSTRAINTS
        # Community only gets basic unique constraints
        return CONSTRAINTS

    async def initialize_schema(self, drop_existing: bool = False) -> None:
        """Initialize all schema elements.

        Args:
            drop_existing: If True, drops existing constraints/indexes first.
        """
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Detect edition first
            self._edition = await self._detect_edition(session)
            is_enterprise = self._is_enterprise(self._edition)

            if is_enterprise:
                logger.info("Neo4j Enterprise Edition detected - will create all constraints")
            else:
                logger.info(f"Neo4j {self._edition.capitalize()} Edition detected - skipping Enterprise-only constraints")

            if drop_existing:
                await self._drop_all_constraints_and_indexes(session)

            # Create constraints first (required for data integrity)
            await self._create_constraints(session)

            # Create indexes (can be done in parallel with constraints)
            await self._create_indexes(session)

            logger.info("Schema initialization complete")

    async def _execute_schema_statement(
        self,
        session: "AsyncSession",
        name: str,
        cypher: str,
        item_type: str,
    ) -> None:
        """Execute a single schema statement with resilient error handling.

        Args:
            session: Neo4j async session
            name: Name of the constraint/index for logging
            cypher: Cypher statement to execute
            item_type: "constraint" or "index" for context-aware logging

        Raises:
            Various Neo4j exceptions on non-recoverable errors
        """
        try:
            await session.run(cypher)
            logger.info(f"Created {item_type}: {name}")
        except ClientError as e:
            error_msg = str(e).lower()
            if _ERROR_ALREADY_EXISTS in error_msg or _ERROR_CONSTRAINT_EXISTS in error_msg or _ERROR_INDEX_EXISTS in error_msg:
                logger.info(f"{item_type.capitalize()} {name} already exists")
                return
            logger.error(
                f"Client error creating {item_type} {name}",
                extra={"name": name, "item_type": item_type, "error_code": "NEO4J_CLIENT_ERROR", "error": sanitize_log_error(e)},
                exc_info=True,
            )
            raise
        except (ConfigurationError, DatabaseError) as e:
            logger.error(
                f"Database error creating {item_type} {name}",
                extra={"name": name, "item_type": item_type, "error_code": "NEO4J_DATABASE_ERROR", "error": sanitize_log_error(e)},
                exc_info=True,
            )
            raise
        except (TransientError, ServiceUnavailable) as e:
            logger.warning(
                f"Transient error creating {item_type} {name}, retry may be needed",
                extra={"name": name, "item_type": item_type, "error_code": "NEO4J_TRANSIENT_ERROR", "error": sanitize_log_error(e)},
            )
            raise

    async def _create_constraints(self, session: "AsyncSession") -> None:
        """Create all schema constraints appropriate for the Neo4j edition.

        Args:
            session: Neo4j async session
        """
        constraints = self._get_constraints_for_edition(self._edition)

        for constraint in constraints:
            await self._execute_schema_statement(
                session, constraint.name, constraint.cypher, "constraint"
            )

        # Log skipped enterprise constraints
        if not self._is_enterprise() and TENANT_CONSTRAINTS:
            skipped_names = [c.name for c in TENANT_CONSTRAINTS]
            logger.info(
                "Skipped Enterprise-only constraints",
                extra={"skipped_count": len(TENANT_CONSTRAINTS), "skipped_names": skipped_names},
            )

    def _build_index_cypher(self, index: Index) -> str:
        """Build Cypher for creating an index.

        Args:
            index: Index definition

        Returns:
            Cypher statement for creating the index
        """
        if index.index_type == "vector":
            return self._build_vector_index_cypher(
                index_name=index.name,
                entity_type=index.entity_type,
                property_name=index.properties[0],
            )
        return index.cypher

    async def _create_indexes(self, session: "AsyncSession") -> None:
        """Create all schema indexes.

        Args:
            session: Neo4j async session
        """
        for index in INDEXES:
            query = self._build_index_cypher(index)
            await self._execute_schema_statement(
                session, index.name, query, "index"
            )

    def _build_vector_index_cypher(
        self,
        index_name: str,
        entity_type: str,
        property_name: str,
    ) -> str:
        """Build vector index Cypher using configured embedding dimension."""
        embedding_dimension = getattr(self.settings, "embedding_dimension", 384)
        return (
            f"CREATE VECTOR INDEX {index_name} "
            "IF NOT EXISTS "
            f"FOR (n:{entity_type}) "
            f"ON (n.{property_name}) "
            "OPTIONS {indexConfig: {"
            f"`vector.dimensions`: {embedding_dimension}, "
            "`vector.similarity_function`: 'cosine'"
            "}}"
        )

    async def _drop_all_constraints_and_indexes(self, session) -> None:
        """Drop all existing constraints and indexes."""
        # Detect edition if not already cached
        if self._edition is None:
            self._edition = await self._detect_edition(session)

        # Get all constraints for this edition (including enterprise if applicable)
        constraints_to_drop = self._get_constraints_for_edition(self._edition)

        # Drop constraints
        for constraint in constraints_to_drop:
            try:
                await session.run(constraint.drop_cypher)
                logger.info(f"Dropped constraint: {constraint.name}")
            except ClientError as e:
                if "does not exist" in str(e):
                    logger.debug(
                        f"Constraint {constraint.name} does not exist, skipping"
                    )
                else:
                    logger.warning(
                        f"Client error dropping constraint {constraint.name}: {e}"
                    )
            except (ConfigurationError, DatabaseError) as e:
                logger.warning(
                    f"Database error dropping constraint {constraint.name}: {e}"
                )
            except (TransientError, ServiceUnavailable) as e:
                logger.warning(
                    f"Transient error dropping constraint {constraint.name}, retry may be needed: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"Unexpected error dropping constraint {constraint.name}: {e}"
                )

        # Drop indexes
        for index in INDEXES:
            try:
                await session.run(index.drop_cypher)
                logger.info(f"Dropped index: {index.name}")
            except ClientError as e:
                if "does not exist" in str(e):
                    logger.debug(f"Index {index.name} does not exist, skipping")
                else:
                    logger.warning(f"Client error dropping index {index.name}: {e}")
            except (ConfigurationError, DatabaseError) as e:
                logger.warning(f"Database error dropping index {index.name}: {e}")
            except (TransientError, ServiceUnavailable) as e:
                logger.warning(
                    f"Transient error dropping index {index.name}, retry may be needed: {e}"
                )
            except Exception as e:
                logger.warning(f"Unexpected error dropping index {index.name}: {e}")

    async def verify_schema(self) -> dict:
        """Verify that all schema elements exist.

        Returns:
            Dictionary with verification results.
        """
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Detect edition if not already cached
            if self._edition is None:
                self._edition = await self._detect_edition(session)

            expected_constraints = self._get_constraints_for_edition(self._edition)

            results = {
                "constraints": {"expected": len(expected_constraints), "found": 0, "missing": []},
                "indexes": {"expected": len(INDEXES), "found": 0, "missing": []},
                "edition": self._edition,
                "enterprise_features": self._is_enterprise(),
            }

            # Check constraints
            constraint_records = await session.run("SHOW CONSTRAINTS YIELD name")
            existing_constraints = [
                record["name"] async for record in constraint_records
            ]

            for constraint in expected_constraints:
                if constraint.name in existing_constraints:
                    results["constraints"]["found"] += 1
                else:
                    results["constraints"]["missing"].append(constraint.name)

            # Check indexes
            index_records = await session.run("SHOW INDEXES YIELD name")
            existing_indexes = [record["name"] async for record in index_records]

            for index in INDEXES:
                if index.name in existing_indexes:
                    results["indexes"]["found"] += 1
                else:
                    results["indexes"]["missing"].append(index.name)

        results["valid"] = (
            results["constraints"]["found"] == results["constraints"]["expected"]
            and results["indexes"]["found"] == results["indexes"]["expected"]
        )

        return results

    async def get_statistics(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with node and relationship counts by type.
        """
        driver = await self._get_driver()
        stats = {
            "nodes": {},
            "relationships": {},
            "total_nodes": 0,
            "total_relationships": 0,
        }

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Count nodes by label
            node_result = await session.run(
                "MATCH (n) RETURN labels(n) as labels, count(*) as count"
            )
            async for record in node_result:
                labels = record["labels"]
                count = record["count"]
                label_str = ":".join(labels) if labels else "NoLabel"
                stats["nodes"][label_str] = count
                stats["total_nodes"] += count

            # Count relationships by type
            rel_result = await session.run(
                "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
            )
            async for record in rel_result:
                rel_type = record["type"]
                count = record["count"]
                stats["relationships"][rel_type] = count
                stats["total_relationships"] += count

        return stats

    async def health_check(self) -> dict:
        """Check Neo4j connectivity and basic functionality.

        Returns:
            Health status dictionary.
        """
        try:
            driver = await self._get_driver()
            async with driver.session(database=self.settings.neo4j_database) as session:
                result = await session.run("RETURN 1 as check")
                record = await result.single()
                if record and record["check"] == 1:
                    return SchemaInitializer_health_checkResult.model_validate({
                        "status": "healthy",
                        "database": self.settings.neo4j_database,
                        "uri": self.settings.neo4j_uri,
                    })


                return SchemaInitializer_health_checkResult.model_validate({
                    "status": "unhealthy",
                    "error": "Query returned unexpected result",
                })


        except (ServiceUnavailable, TransientError) as e:
            return SchemaInitializer_health_checkResult.model_validate({"status": "unhealthy", "error": f"Neo4j service unavailable: {e}"})
        except ConfigurationError as e:
            return SchemaInitializer_health_checkResult.model_validate({"status": "unhealthy", "error": f"Neo4j configuration error: {e}"})
        except DatabaseError as e:
            return SchemaInitializer_health_checkResult.model_validate({"status": "unhealthy", "error": f"Neo4j database error: {e}"})
        except ClientError as e:
            return SchemaInitializer_health_checkResult.model_validate({"status": "unhealthy", "error": f"Neo4j client error: {e}"})
        except Exception as e:
            return SchemaInitializer_health_checkResult.model_validate({"status": "unhealthy", "error": f"Unexpected error: {e}"})
