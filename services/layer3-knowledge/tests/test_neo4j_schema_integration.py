from __future__ import annotations

"""Integration tests for Neo4j schema layer (between unit and e2e).

These tests verify real Neo4j behavior with actual schema constraints,
without requiring full Layer 2 → Layer 3 workflow orchestration.

Requirements:
    - Docker running locally
    - testcontainers[neo4j] installed

Run with:
    pytest tests/test_neo4j_schema_integration.py -v -m integration
"""


import pytest
import pytest_asyncio

# Guard: skip entire module if testcontainers is not installed
try:
    from testcontainers.neo4j import Neo4jContainer
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

from neo4j import AsyncGraphDatabase

from src.config import Settings
from src.schema.initializer import SchemaInitializer

pytestmark = [
    pytest.mark.skipif(
        not HAS_TESTCONTAINERS,
        reason="testcontainers not installed - run: pip install testcontainers[neo4j]"
    ),
    pytest.mark.integration,
]


TEST_NEO4J_PASSWORD = "test-password"


async def _wait_for_neo4j_ready(container: Neo4jContainer, timeout_seconds: float = 60.0) -> None:
    """Wait for Neo4j to be ready using driver-native retry with timeout.

    Uses asyncio.wait_for to enforce a hard deadline while allowing
    the driver's verify_connectivity to handle transient failures.
    """
    import asyncio

    async def _check_connectivity() -> None:
        driver = AsyncGraphDatabase.driver(
            container.get_connection_url(),
            auth=("neo4j", TEST_NEO4J_PASSWORD),
        )
        try:
            await driver.verify_connectivity()
        finally:
            await driver.close()

    start_time = asyncio.get_event_loop().time()
    last_error = None

    while asyncio.get_event_loop().time() - start_time < timeout_seconds:
        try:
            await asyncio.wait_for(_check_connectivity(), timeout=5.0)
            return  # Success - Neo4j is ready
        except Exception as e:
            last_error = e
            # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, then cap at 1.0s
            elapsed = asyncio.get_event_loop().time() - start_time
            backoff = min(0.1 * (2 ** int(elapsed / 2)), 1.0)
            await asyncio.sleep(backoff)

    raise RuntimeError(f"Neo4j failed to start within {timeout_seconds}s: {last_error}")


@pytest_asyncio.fixture(scope="module")
async def neo4j_container():
    """Start Neo4j container for integration tests."""
    container = Neo4jContainer(
        image="neo4j:5.15-community",
        password=TEST_NEO4J_PASSWORD,
    )

    container.start()

    try:
        await _wait_for_neo4j_ready(container, timeout_seconds=60.0)
        yield container
    finally:
        container.stop()


@pytest_asyncio.fixture
async def neo4j_driver(neo4j_container):
    """Provide Neo4j async driver."""
    driver = AsyncGraphDatabase.driver(
        neo4j_container.get_connection_url(),
        auth=("neo4j", TEST_NEO4J_PASSWORD),
    )

    yield driver

    await driver.close()


@pytest_asyncio.fixture
async def settings(neo4j_container):
    """Create test settings with Neo4j connection."""
    return Settings(
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password=TEST_NEO4J_PASSWORD,
        neo4j_database="neo4j",
        neo4j_max_pool_size=10,
        embedding_dimension=384,
    )


@pytest_asyncio.fixture
async def schema_initializer(neo4j_driver, settings):
    """Provide schema initializer."""
    return SchemaInitializer(driver=neo4j_driver, settings=settings)


@pytest.mark.asyncio
@pytest.mark.integration
class TestNeo4jConstraints:
    """Test Neo4j constraint creation and enforcement."""

    async def test_composite_unique_constraint_prevents_duplicates(
        self, neo4j_driver, schema_initializer
    ):
        """Composite (id, tenant_id) constraint should prevent same id in same tenant."""
        # Initialize schema
        await schema_initializer.initialize_schema(drop_existing=True)

        # Insert first entity
        async with neo4j_driver.session() as session:
            await session.run(
                "CREATE (c:Capability {id: 'cap-001', tenant_id: 'tenant-a', name: 'First'})"
            )

        # Attempt duplicate in same tenant - should fail
        with pytest.raises(Exception) as exc_info:
            async with neo4j_driver.session() as session:
                await session.run(
                    "CREATE (c:Capability {id: 'cap-001', tenant_id: 'tenant-a', name: 'Duplicate'})"
                )

        assert "constraint" in str(exc_info.value).lower() or "already exists" in str(exc_info.value).lower()

    async def test_same_id_different_tenants_allowed(
        self, neo4j_driver, schema_initializer
    ):
        """Same id should be allowed in different tenants (multi-tenancy)."""
        await schema_initializer.initialize_schema(drop_existing=True)

        async with neo4j_driver.session() as session:
            # Both should succeed - different tenants
            await session.run(
                "CREATE (c1:Capability {id: 'cap-shared', tenant_id: 'tenant-a', name: 'A'})"
            )
            await session.run(
                "CREATE (c2:Capability {id: 'cap-shared', tenant_id: 'tenant-b', name: 'B'})"
            )

            # Verify both exist
            result = await session.run(
                "MATCH (c:Capability {id: 'cap-shared'}) RETURN count(c) as count"
            )
            record = await result.single()
            assert record["count"] == 2

    async def test_all_constraints_are_community_compatible(
        self, neo4j_driver, schema_initializer
    ):
        """All constraints must work on Neo4j Community Edition."""
        await schema_initializer.initialize_schema(drop_existing=True)

        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW CONSTRAINTS YIELD name, type RETURN collect({name: name, type: type}) as constraints"
            )
            record = await result.single()
            constraints = record["constraints"]

            # All should be uniqueness constraints (Community compatible)
            for c in constraints:
                assert c["type"] == "UNIQUENESS", f"Constraint {c['name']} is {c['type']} - may require Enterprise"


@pytest.mark.asyncio
@pytest.mark.integration
class TestNeo4jIndexPerformance:
    """Test index creation and query performance."""

    async def test_tenant_id_index_exists(self, neo4j_driver, schema_initializer):
        """Tenant isolation index should exist for filtering."""
        await schema_initializer.initialize_schema(drop_existing=True)

        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW INDEXES YIELD name, properties WHERE 'tenant_id' IN properties "
                "RETURN collect(name) as tenant_indexes"
            )
            record = await result.single()
            tenant_indexes = record["tenant_indexes"]

            # Should have at least one index on tenant_id
            assert len(tenant_indexes) > 0, "No indexes found on tenant_id"

    async def test_vector_indexes_created(self, neo4j_driver, schema_initializer):
        """Vector indexes should exist for similarity search."""
        await schema_initializer.initialize_schema(drop_existing=True)

        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' "
                "RETURN collect(name) as vector_indexes"
            )
            record = await result.single()
            vector_indexes = set(record["vector_indexes"] if record else [])

            expected = {
                "capability_embedding_idx",
                "usecase_embedding_idx",
                "persona_embedding_idx",
                "valuedriver_embedding_idx",
            }
            assert expected.issubset(vector_indexes), f"Missing vector indexes: {expected - vector_indexes}"


@pytest.mark.asyncio
@pytest.mark.integration
class TestNeo4jFailureModes:
    """Test failure handling and recovery scenarios."""

    async def test_schema_init_idempotent(self, neo4j_driver, schema_initializer):
        """Schema initialization should be idempotent (safe to retry)."""
        # First initialization
        await schema_initializer.initialize_schema(drop_existing=True)

        # Second initialization should not error
        await schema_initializer.initialize_schema(drop_existing=False)

        # Verify constraints still exist
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW CONSTRAINTS YIELD name RETURN count(*) as count"
            )
            record = await result.single()
            assert record["count"] > 0

    async def test_corrupted_constraint_recreated_after_drop(
        self, neo4j_driver, schema_initializer
    ):
        """If constraints are corrupted/dropped, re-init should restore them."""
        # Initialize first
        await schema_initializer.initialize_schema(drop_existing=True)

        # Simulate corruption - drop a constraint
        async with neo4j_driver.session() as session:
            await session.run("DROP CONSTRAINT capability_id_tenant IF EXISTS")

        # Re-initialize should restore
        await schema_initializer.initialize_schema(drop_existing=False)

        # Verify restored
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW CONSTRAINTS YIELD name WHERE name = 'capability_id_tenant' "
                "RETURN count(*) as count"
            )
            record = await result.single()
            assert record["count"] == 1


def test_get_tenant_constraints_community_returns_empty() -> None:
    """P2 Regression: Verify Community Edition gets no tenant constraints."""
    from schema.constraints import get_tenant_constraints

    constraints = get_tenant_constraints("community")
    assert constraints == []


def test_get_tenant_constraints_enterprise_returns_all() -> None:
    """P2 Regression: Verify Enterprise Edition gets all tenant constraints."""
    from schema.constraints import TENANT_CONSTRAINTS, get_tenant_constraints

    constraints = get_tenant_constraints("enterprise")
    assert len(constraints) == len(TENANT_CONSTRAINTS)
    assert all(c.constraint_type == "exists" for c in constraints)

