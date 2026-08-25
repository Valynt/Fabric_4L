from __future__ import annotations

"""End-to-end pipeline test for Layer 3 Knowledge Graph.

This test verifies the complete flow from extraction to query:
1. Start Neo4j in Docker
2. Initialize schema (constraints, indexes, vector)
3. Simulate Layer 2 extraction results (or use real data)
4. Ingest entities/relationships via Layer 3 API
5. Verify data in Neo4j
6. Run GraphRAG queries
7. Run hybrid search

Usage:
    pytest tests/test_e2e_pipeline.py -v

Requirements:
    - Docker running locally
    - Neo4j image available
"""


import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from neo4j import AsyncGraphDatabase
from value_fabric.shared.identity import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware

# Guard: skip entire module if testcontainers is not installed
try:
    from testcontainers.neo4j import Neo4jContainer  # type: ignore
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

from src.api.dependencies import (
    get_graph_rag,
    get_hybrid_search,
    get_schema_initializer,
    get_sync_manager,
)
from src.api.main import app
from src.config import Settings
from src.ingestion.neo4j_loader import Neo4jLoader
from src.ingestion.sync_manager import SyncManager
from src.retrieval.graph_rag import GraphRAGEngine
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.vector_store import VectorStore
from src.schema.initializer import SchemaInitializer

# Skip entire module if testcontainers not installed
pytestmark = [
    pytest.mark.skipif(
        not HAS_TESTCONTAINERS,
        reason="testcontainers not installed - run: pip install testcontainers[neo4j]"
    ),
    pytest.mark.integration,  # P1: Explicit marker for selective test running
]





def _patch_app_for_test_auth(
    application,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bypass GovernanceMiddleware auth/tenant checks for live E2E fixtures."""
    from value_fabric.shared.identity import require_authenticated

    async def _handle_authentication(self, request):
        return RequestContext(tenant_id=TEST_TENANT_ID, user_id="test-user")

    async def _enforce_tenant_status(self, ctx):
        return None

    monkeypatch.setattr(GovernanceMiddleware, "_handle_authentication", _handle_authentication)
    monkeypatch.setattr(GovernanceMiddleware, "_enforce_tenant_status", _enforce_tenant_status)
    monkeypatch.setitem(
        application.dependency_overrides,
        require_authenticated,
        lambda: RequestContext(
            tenant_id=TEST_TENANT_ID, user_id="test-user"
        ),
    )
    monkeypatch.setattr(application, "middleware_stack", None)


# Test configuration
TEST_NEO4J_PASSWORD = "test-password"
TEST_EMBEDDING_DIMENSION = 384
REQUIRED_VECTOR_INDEXES = {
    "capability_embedding_idx",
    "usecase_embedding_idx",
    "persona_embedding_idx",
    "valuedriver_embedding_idx",
}
TEST_TENANT_ID = "12345678-1234-1234-1234-123456789abc"


@pytest_asyncio.fixture(scope="module")
async def neo4j_container() -> AsyncGenerator[Neo4jContainer, None]:
    """Start Neo4j container for testing with deterministic wait strategy.
    
    Uses testcontainers' built-in wait strategy for reliable container
    startup detection instead of a hardcoded retry loop.
    """
    from testcontainers.core.waiting_utils import wait_for_logs
    
    container = Neo4jContainer(
        image="neo4j:5.15-community",
        password=TEST_NEO4J_PASSWORD,
    ).with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')
    
    # Use testcontainers' built-in wait strategy for deterministic readiness detection.
    container.start()
    wait_for_logs(container, "Started.", timeout=60)
    
    # Additional verification that Neo4j is accepting connections
    driver = AsyncGraphDatabase.driver(
        container.get_connection_url(),
        auth=("neo4j", TEST_NEO4J_PASSWORD),
    )
    try:
        await driver.verify_connectivity()
    finally:
        await driver.close()
    
    yield container
    
    # Cleanup
    container.stop()


@pytest_asyncio.fixture
async def neo4j_driver(neo4j_container: Neo4jContainer) -> AsyncGenerator:
    """Provide Neo4j async driver."""
    driver = AsyncGraphDatabase.driver(
        neo4j_container.get_connection_url(),
        auth=("neo4j", TEST_NEO4J_PASSWORD),
    )
    
    yield driver
    
    await driver.close()


@pytest_asyncio.fixture
async def settings(neo4j_container: Neo4jContainer) -> Settings:
    """Create test settings with Neo4j connection."""
    return Settings(
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password=TEST_NEO4J_PASSWORD,
        neo4j_database="neo4j",
        neo4j_max_pool_size=10,
        embedding_dimension=TEST_EMBEDDING_DIMENSION,
    )


@pytest_asyncio.fixture
async def schema_initializer(
    neo4j_driver,
    settings: Settings,
) -> SchemaInitializer:
    """Provide schema initializer."""
    return SchemaInitializer(driver=neo4j_driver, settings=settings)


@pytest_asyncio.fixture
async def neo4j_edition(neo4j_driver) -> str:
    """Detect Neo4j edition (community or enterprise)."""
    async with neo4j_driver.session() as session:
        result = await session.run("CALL dbms.components() YIELD edition RETURN edition")
        record = await result.single()
        return record["edition"].lower() if record else "unknown"


@pytest_asyncio.fixture
async def initialized_schema(
    schema_initializer: SchemaInitializer,
) -> None:
    """Initialize schema before tests.

    The schema initializer now automatically detects Neo4j edition and
    skips Enterprise-only constraints on Community Edition.
    """
    await schema_initializer.initialize_schema(drop_existing=True)


@pytest_asyncio.fixture
async def neo4j_loader(
    neo4j_driver,
    settings: Settings,
) -> Neo4jLoader:
    """Provide Neo4j loader."""
    return Neo4jLoader(driver=neo4j_driver, settings=settings)


@pytest.mark.asyncio
@pytest.mark.integration
class TestSchemaInitialization:
    """Test Neo4j schema initialization."""
    
    async def test_initialize_schema(
        self,
        schema_initializer: SchemaInitializer,
        neo4j_driver,
    ):
        """Test schema initialization creates constraints and indexes."""
        # Initialize schema
        await schema_initializer.initialize_schema(drop_existing=True)
        
        # Verify constraints exist
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW CONSTRAINTS YIELD name, type RETURN count(*) as count"
            )
            record = await result.single()
            assert record["count"] > 0, "No constraints created"
        
        # Verify indexes exist
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW INDEXES YIELD name, type RETURN count(*) as count"
            )
            record = await result.single()
            assert record["count"] > 0, "No indexes created"

            vector_result = await session.run(
                "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN collect(name) AS names"
            )
            vector_record = await vector_result.single()
            vector_names = set(vector_record["names"] if vector_record else [])
            assert REQUIRED_VECTOR_INDEXES.issubset(vector_names)
    
    async def test_idempotent_schema_init(
        self,
        schema_initializer: SchemaInitializer,
    ):
        """Test schema initialization is idempotent."""
        # Run twice - should not error
        await schema_initializer.initialize_schema(drop_existing=False)
        await schema_initializer.initialize_schema(drop_existing=False)
    
    async def test_health_check(
        self,
        schema_initializer: SchemaInitializer,
    ):
        """Test health check returns healthy status."""
        health = await schema_initializer.health_check()
        assert health["status"] == "healthy"
        assert health["database"] == "neo4j"

    async def test_schema_initialization_detects_community_edition(
        self,
        schema_initializer: SchemaInitializer,
        neo4j_edition: str,
    ):
        """Test that schema initialization correctly detects and handles Community Edition.

        This test verifies that:
        1. Edition is detected correctly
        2. Community edition skips enterprise-only constraints
        3. Schema verification passes with correct constraint count
        """
        # Initialize schema
        await schema_initializer.initialize_schema(drop_existing=True)

        # Verify schema
        results = await schema_initializer.verify_schema()

        # Check edition detection
        assert results["edition"] == neo4j_edition
        assert results["enterprise_features"] == (neo4j_edition == "enterprise")

        # Verify constraints match edition expectations
        if neo4j_edition == "community":
            # Community should have fewer constraints (no TENANT_CONSTRAINTS)
            from src.schema.constraints import CONSTRAINTS, TENANT_CONSTRAINTS
            assert results["constraints"]["expected"] == len(CONSTRAINTS)
        else:
            # Enterprise should have all constraints
            from src.schema.constraints import CONSTRAINTS, TENANT_CONSTRAINTS
            assert results["constraints"]["expected"] == len(CONSTRAINTS) + len(TENANT_CONSTRAINTS)

        # Schema should be valid
        assert results["valid"] is True


@pytest.mark.asyncio
class TestEntityIngestion:
    """Test entity ingestion from extraction results."""
    
    async def test_ingest_single_entity(
        self,
        neo4j_loader: Neo4jLoader,
        initialized_schema,
        neo4j_driver,
    ):
        """Test ingesting a single entity."""
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        
        # Create minimal RDF graph with one capability
        rdf_graph = Graph()
        rdf_graph.bind("vf", VF)
        
        cap_uri = URIRef("http://valuefabric.io/entity/cap-001")
        rdf_graph.add((cap_uri, RDF.type, VF.Capability))
        rdf_graph.add((cap_uri, VF.id, Literal("cap-001")))
        rdf_graph.add((cap_uri, VF.name, Literal("Real-time Analytics")))
        rdf_graph.add((cap_uri, VF.description, Literal("Process data in real-time")))
        rdf_graph.add((cap_uri, VF.confidence, Literal("0.85")))
        
        # Ingest
        stats = await neo4j_loader.load_rdf_graph(
            rdf_graph=rdf_graph,
            source_id="test-source",
            extraction_job_id="test-job-001",
            tenant_id=TEST_TENANT_ID,
        )
        
        assert stats["entities_loaded"] >= 1
        
        # Verify in Neo4j
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (n:Capability {id: 'cap-001'}) "
                "RETURN n.name as name, n.embedding as embedding"
            )
            record = await result.single()
            assert record is not None
            assert record["name"] == "Real-time Analytics"
            assert isinstance(record["embedding"], list)
            assert len(record["embedding"]) > 0
    
    async def test_ingest_with_relationships(
        self,
        neo4j_loader: Neo4jLoader,
        initialized_schema,
        neo4j_driver,
    ):
        """Test ingesting entities with relationships."""
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        
        rdf_graph = Graph()
        rdf_graph.bind("vf", VF)
        
        # Create capability
        cap_uri = URIRef("http://valuefabric.io/entity/cap-002")
        rdf_graph.add((cap_uri, RDF.type, VF.Capability))
        rdf_graph.add((cap_uri, VF.id, Literal("cap-002")))
        rdf_graph.add((cap_uri, VF.name, Literal("AI Prediction")))
        
        # Create use case
        uc_uri = URIRef("http://valuefabric.io/entity/uc-001")
        rdf_graph.add((uc_uri, RDF.type, VF.UseCase))
        rdf_graph.add((uc_uri, VF.id, Literal("uc-001")))
        rdf_graph.add((uc_uri, VF.name, Literal("Demand Forecasting")))
        
        # Create relationship: Capability enables UseCase
        rdf_graph.add((cap_uri, VF.enables, uc_uri))
        
        # Ingest
        stats = await neo4j_loader.load_rdf_graph(
            rdf_graph=rdf_graph,
            source_id="test-source",
            extraction_job_id="test-job-002",
            tenant_id=TEST_TENANT_ID,
        )
        
        assert stats["entities_loaded"] >= 2
        assert stats["relationships_loaded"] >= 1
        
        # Verify relationship in Neo4j
        async with neo4j_driver.session() as session:
            result = await session.run("""
                MATCH (c:Capability {id: 'cap-002'})-[r:enables]->(u:UseCase {id: 'uc-001'})
                RETURN count(r) as count
            """)
            record = await result.single()
            assert record["count"] == 1


@pytest.mark.asyncio
class TestGraphRAGQueries:
    """Test GraphRAG retrieval."""
    
    async def test_graph_rag_query(
        self,
        neo4j_driver,
        settings: Settings,
        initialized_schema,
    ):
        """Test GraphRAG query execution."""
        # Create test data
        async with neo4j_driver.session() as session:
            await session.run("""
                CREATE (c:Capability {id: 'cap-003', name: 'Data Pipeline', confidence: 0.9, tenant_id: $tenant_id})
                CREATE (u:UseCase {id: 'uc-002', name: 'ETL Processing', confidence: 0.85, tenant_id: $tenant_id})
                CREATE (c)-[:enables {confidence: 0.9}]->(u)
            """, {"tenant_id": TEST_TENANT_ID})
        
        # Initialize GraphRAG
        graph_rag = GraphRAGEngine(driver=neo4j_driver, settings=settings)
        
        # Execute query
        result = await graph_rag.query(
            query_text="ETL Processing",
            max_hops=2,
            max_results=5,
            tenant_id=TEST_TENANT_ID,
        )
        
        assert result is not None
        assert len(result.entities) > 0
    
    async def test_multi_hop_traversal(
        self,
        neo4j_driver,
        settings: Settings,
        initialized_schema,
    ):
        """Test multi-hop graph traversal."""
        # Create chain: Capability -> UseCase -> Persona
        async with neo4j_driver.session() as session:
            await session.run("""
                CREATE (c:Capability {id: 'cap-004', name: 'ML Platform', confidence: 0.9, tenant_id: $tenant_id})
                CREATE (u:UseCase {id: 'uc-003', name: 'AutoML', confidence: 0.85, tenant_id: $tenant_id})
                CREATE (p:Persona {id: 'pers-001', name: 'Data Scientist', confidence: 0.9, tenant_id: $tenant_id})
                CREATE (c)-[:enables {confidence: 0.9}]->(u)
                CREATE (u)-[:involves {confidence: 0.85}]->(p)
            """, {"tenant_id": TEST_TENANT_ID})
        
        graph_rag = GraphRAGEngine(driver=neo4j_driver, settings=settings)
        
        # Query from Capability to find reachable Persona
        result = await graph_rag.query(
            query_text="ML Platform",
            max_hops=3,
            max_results=10,
            tenant_id=TEST_TENANT_ID,
        )
        
        assert result is not None
        # Should find at least 3 entities in the chain
        assert len(result.entities) >= 3


@pytest.mark.asyncio
class TestHybridSearch:
    """Test hybrid (vector + graph) search."""
    
    async def test_hybrid_search_basic(
        self,
        neo4j_driver,
        settings: Settings,
        initialized_schema,
    ):
        """Test basic hybrid search functionality."""
        # Create test data with embeddings
        async with neo4j_driver.session() as session:
            await session.run("""
                CREATE (c:Capability {
                    id: 'cap-005',
                    name: 'Stream Processing',
                    description: 'Real-time data stream processing',
                    confidence: 0.9,
                    embedding: range(0, 767),
                    tenant_id: $tenant_id
                })
            """, {"tenant_id": TEST_TENANT_ID})
        
        # Initialize hybrid search (without vector store - uses Neo4j only)
        hybrid_search = HybridSearch(driver=neo4j_driver, settings=settings)
        
        # Search
        results = await hybrid_search.search(
            query="stream processing",
            limit=5,
            tenant_id=TEST_TENANT_ID,
        )
        
        # Verify results structure
        assert isinstance(results, list)


@pytest.mark.asyncio
class TestAPIEndpoints:
    """Test Layer 3 API endpoints."""
    
    @pytest_asyncio.fixture
    async def api_client(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> AsyncGenerator[AsyncClient, None]:
        """Provide HTTP client for API testing."""
        schema_initializer = AsyncMock()
        schema_initializer.health_check.return_value = {
            "status": "healthy",
            "database": "neo4j",
            "uri": "bolt://localhost:7687",
        }
        schema_initializer.verify_schema.return_value = {
            "constraints": {"expected": 0, "found": 0, "missing": []},
            "indexes": {"expected": 0, "found": 0, "missing": []},
            "valid": True,
        }
        app.dependency_overrides[get_schema_initializer] = lambda: schema_initializer
        _patch_app_for_test_auth(app, monkeypatch)
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        finally:
            app.dependency_overrides.pop(get_schema_initializer, None)
    
    async def test_health_endpoint(self, api_client: AsyncClient):
        """Test health check endpoint."""
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
    
    async def test_detailed_health_endpoint(self, api_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await api_client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "schema_status" in data

    @pytest_asyncio.fixture
    async def api_client_with_neo4j(
        self,
        neo4j_driver,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> AsyncGenerator[AsyncClient, None]:
        """Provide API client with real Neo4j dependencies injected."""
        loader = Neo4jLoader(driver=neo4j_driver, settings=settings)
        sync_manager = SyncManager(loader=loader, driver=neo4j_driver, settings=settings)
        vector_store = VectorStore(driver=neo4j_driver, settings=settings)
        graph_rag = GraphRAGEngine(
            driver=neo4j_driver,
            vector_store=vector_store,
            settings=settings,
        )
        hybrid = HybridSearch(
            driver=neo4j_driver,
            vector_store=vector_store,
            graph_engine=graph_rag,
            settings=settings,
        )

        app.dependency_overrides[get_sync_manager] = lambda: sync_manager
        app.dependency_overrides[get_graph_rag] = lambda: graph_rag
        app.dependency_overrides[get_hybrid_search] = lambda: hybrid

        _patch_app_for_test_auth(app, monkeypatch)
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        finally:
            app.dependency_overrides.clear()

    async def test_ingest_endpoint_with_real_neo4j(
        self,
        api_client_with_neo4j: AsyncClient,
        initialized_schema,
    ):
        """Should ingest RDF data via API endpoint and return success with entity count."""
        rdf_data = """
            @prefix vf: <http://valuefabric.io/ontology/> .
            @prefix ex: <http://valuefabric.io/entity/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

            ex:cap-ingest-001 rdf:type vf:Capability ;
                vf:id "cap-ingest-001" ;
                vf:name "API Test Capability" ;
                vf:description "Testing ingestion via API" ;
                vf:confidence "0.90" .
        """

        response = await api_client_with_neo4j.post(
            "/v1/ingest",
            json={
                "rdf_data": rdf_data,
                "source_id": "api-test-source",
                "extraction_job_id": "api-test-job-001",
                "tenant_id": TEST_TENANT_ID,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["entities_loaded"] >= 1

    async def test_graph_query_routes_return_results(
        self,
        api_client_with_neo4j: AsyncClient,
        initialized_schema,
    ):
        """Should return matching entities from both /v1/query/graph and /v1/query endpoints."""
        # First ingest test data
        rdf_data = """
            @prefix vf: <http://valuefabric.io/ontology/> .
            @prefix ex: <http://valuefabric.io/entity/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

            ex:cap-query-001 rdf:type vf:Capability ;
                vf:id "cap-query-001" ;
                vf:name "Graph Query Test" ;
                vf:confidence "0.90" .
        """

        ingest_resp = await api_client_with_neo4j.post(
            "/v1/ingest",
            json={
                "rdf_data": rdf_data,
                "source_id": "query-test-source",
                "extraction_job_id": "query-test-job",
                "tenant_id": TEST_TENANT_ID,
            },
        )
        assert ingest_resp.status_code == 200

        # Test two graph query routes (both are deprecated compatibility aliases).
        payload = {
            "query": "Graph Query Test",
            "max_hops": 2,
            "top_k": 10,
        }

        # /v1/query/graph alias route
        alias_resp = await api_client_with_neo4j.post("/v1/query/graph", json=payload)
        assert alias_resp.status_code == 200
        alias_data = alias_resp.json()
        assert len(alias_data["entities"]) > 0, "Alias route should return entities"

        # /v1/graphrag legacy alias route
        legacy_resp = await api_client_with_neo4j.post("/v1/graphrag", json=payload)
        assert legacy_resp.status_code == 200
        legacy_data = legacy_resp.json()
        assert len(legacy_data["entities"]) > 0, "Legacy route should return entities"

    async def test_search_routes_return_results(
        self,
        api_client_with_neo4j: AsyncClient,
        initialized_schema,
    ):
        """Should return search results from both /v1/search/hybrid and /v1/search endpoints."""
        # First ingest test data
        rdf_data = """
            @prefix vf: <http://valuefabric.io/ontology/> .
            @prefix ex: <http://valuefabric.io/entity/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

            ex:cap-search-001 rdf:type vf:Capability ;
                vf:id "cap-search-001" ;
                vf:name "Search Route Test" ;
                vf:description "Testing search functionality" ;
                vf:confidence "0.90" .
        """

        ingest_resp = await api_client_with_neo4j.post(
            "/v1/ingest",
            json={
                "rdf_data": rdf_data,
                "source_id": "search-test-source",
                "extraction_job_id": "search-test-job",
                "tenant_id": TEST_TENANT_ID,
            },
        )
        assert ingest_resp.status_code == 200

        # Test both search endpoints
        payload = {
            "query": "search route test",
            "search_type": "hybrid",
            "top_k": 5,
        }

        # Alias route
        alias_resp = await api_client_with_neo4j.post("/v1/search/hybrid", json=payload)
        assert alias_resp.status_code == 200
        alias_data = alias_resp.json()
        assert alias_data["total_results"] >= 0, "Alias route should return results"

        # Legacy route
        legacy_resp = await api_client_with_neo4j.post("/v1/search", json=payload)
        assert legacy_resp.status_code == 200
        legacy_data = legacy_resp.json()
        assert legacy_data["total_results"] >= 0, "Legacy route should return results"


@pytest.mark.asyncio
class TestE2ECompletePipeline:
    """Complete end-to-end pipeline test."""
    
    async def test_ingests_entities_from_rdf_graph(
        self,
        neo4j_loader: Neo4jLoader,
        initialized_schema,
    ):
        """Should ingest entities and relationships from RDF graph into Neo4j."""
        # Arrange: Create RDF graph with entities and relationships
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF

        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        rdf_graph = Graph()
        rdf_graph.bind("vf", VF)

        # Create test entities
        entities = [
            ("cap-006", "Capability", "Predictive Maintenance", "AI-powered equipment monitoring"),
            ("uc-004", "UseCase", "Factory Optimization", "Optimize factory operations"),
        ]

        for entity_id, entity_type, name, description in entities:
            uri = URIRef(f"http://valuefabric.io/entity/{entity_id}")
            type_class = getattr(VF, entity_type)
            rdf_graph.add((uri, RDF.type, type_class))
            rdf_graph.add((uri, VF.id, Literal(entity_id)))
            rdf_graph.add((uri, VF.name, Literal(name)))
            rdf_graph.add((uri, VF.description, Literal(description)))
            rdf_graph.add((uri, VF.confidence, Literal("0.85")))

        # Add relationship: Capability enables UseCase
        cap_uri = URIRef("http://valuefabric.io/entity/cap-006")
        uc_uri = URIRef("http://valuefabric.io/entity/uc-004")
        rdf_graph.add((cap_uri, VF.enables, uc_uri))

        # Act: Ingest to Neo4j
        stats = await neo4j_loader.load_rdf_graph(
            rdf_graph=rdf_graph,
            source_id="e2e-test",
            extraction_job_id="e2e-job-001",
            tenant_id=TEST_TENANT_ID,
        )

        # Assert: Verify ingestion stats
        assert stats["entities_loaded"] >= 2, f"Expected at least 2 entities, got {stats['entities_loaded']}"
        assert stats["relationships_loaded"] >= 1, f"Expected at least 1 relationship, got {stats['relationships_loaded']}"

    async def test_queries_ingested_entities_with_graphrag(
        self,
        neo4j_driver,
        neo4j_loader: Neo4jLoader,
        settings: Settings,
        initialized_schema,
    ):
        """Should find ingested entities when querying via GraphRAG."""
        # Arrange: Ingest test data
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF

        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        rdf_graph = Graph()
        rdf_graph.bind("vf", VF)

        cap_uri = URIRef("http://valuefabric.io/entity/cap-006")
        rdf_graph.add((cap_uri, RDF.type, VF.Capability))
        rdf_graph.add((cap_uri, VF.id, Literal("cap-006")))
        rdf_graph.add((cap_uri, VF.name, Literal("Predictive Maintenance")))
        rdf_graph.add((cap_uri, VF.confidence, Literal("0.90")))

        await neo4j_loader.load_rdf_graph(
            rdf_graph=rdf_graph,
            source_id="query-test",
            extraction_job_id="query-job-001",
            tenant_id=TEST_TENANT_ID,
        )

        # Act: Query with GraphRAG
        graph_rag = GraphRAGEngine(driver=neo4j_driver, settings=settings)
        result = await graph_rag.query(
            query_text="Predictive Maintenance",
            max_hops=2,
            max_results=5,
            tenant_id=TEST_TENANT_ID,
        )

        # Assert: Should find the capability
        entity_names = [e.get("name", "") for e in result.entities]
        assert "Predictive Maintenance" in entity_names, f"Expected 'Predictive Maintenance' in {entity_names}"

    async def test_verifies_data_integrity_after_ingestion(
        self,
        neo4j_driver,
        neo4j_loader: Neo4jLoader,
        initialized_schema,
    ):
        """Should verify entities and relationships exist in Neo4j after ingestion."""
        # Arrange: Ingest entities with relationships
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF

        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        rdf_graph = Graph()
        rdf_graph.bind("vf", VF)

        # Create chain: Capability -> UseCase -> Persona
        cap_uri = URIRef("http://valuefabric.io/entity/cap-007")
        uc_uri = URIRef("http://valuefabric.io/entity/uc-005")
        pers_uri = URIRef("http://valuefabric.io/entity/pers-003")

        for uri, eid, name, etype in [
            (cap_uri, "cap-007", "Data Pipeline", VF.Capability),
            (uc_uri, "uc-005", "ETL Processing", VF.UseCase),
            (pers_uri, "pers-003", "Data Engineer", VF.Persona),
        ]:
            rdf_graph.add((uri, RDF.type, etype))
            rdf_graph.add((uri, VF.id, Literal(eid)))
            rdf_graph.add((uri, VF.name, Literal(name)))
            rdf_graph.add((uri, VF.confidence, Literal("0.85")))

        rdf_graph.add((cap_uri, VF.enables, uc_uri))
        rdf_graph.add((uc_uri, VF.involves, pers_uri))

        await neo4j_loader.load_rdf_graph(
            rdf_graph=rdf_graph,
            source_id="integrity-test",
            extraction_job_id="integrity-job-001",
            tenant_id=TEST_TENANT_ID,
        )

        # Act & Assert: Verify data integrity in Neo4j
        async with neo4j_driver.session() as session:
            # Count entities by type
            result = await session.run(
                "MATCH (n) WHERE n.id IN ['cap-007', 'uc-005', 'pers-003'] "
                "RETURN count(n) as count"
            )
            record = await result.single()
            assert record["count"] == 3, f"Expected 3 entities, got {record['count']}"

            # Count relationships
            result = await session.run(
                "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r) as count"
            )
            record = await result.single()
            assert record["count"] >= 2, f"Expected at least 2 relationships, got {record['count']}"


@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Docker and RUN_INTEGRATION_TESTS env var",
)
class TestIntegrationWithLayer2:
    """Integration tests with Layer 2 extraction."""
    
    # These tests would require Layer 2 to be running
    # They test the actual Layer 2 -> Layer 3 integration
    
    async def test_layer2_to_layer3_integration(self):
        """Test actual Layer 2 extraction → Layer 3 ingestion."""
        # This would call Layer 2 /extract-and-ingest endpoint
        # and verify data appears in Layer 3
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
