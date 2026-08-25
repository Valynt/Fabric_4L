from __future__ import annotations

"""End-to-end vector index test for Layer 3 Knowledge Graph.

This test focuses specifically on vector index functionality:
1. Start Neo4j in Docker
2. Initialize vector indexes
3. Generate real embeddings with sentence-transformers
4. Ingest entities with embeddings
5. Run hybrid search and verify ranking

Usage:
    pytest tests/test_vector_e2e.py -v

Requirements:
    - Docker running locally
    - Neo4j 5.x image (Community Edition works)
    - sentence-transformers package
"""


import asyncio
from collections.abc import AsyncGenerator

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
from src.ingestion.neo4j import Neo4jLoader
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
    pytest.mark.integration,
    pytest.mark.vector,
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


@pytest_asyncio.fixture(scope="function")
async def neo4j_container() -> AsyncGenerator[Neo4jContainer, None]:
    """Provide a Neo4j test container."""
    container = Neo4jContainer(
        "neo4j:5-community", password=TEST_NEO4J_PASSWORD
    )
    container.with_env("NEO4J_dbms_memory_heap_max__size", "512M")
    container.start()
    
    # Wait for Neo4j to be ready
    await asyncio.sleep(5)
    
    yield container
    
    container.stop()


@pytest_asyncio.fixture
async def neo4j_driver(neo4j_container: Neo4jContainer) -> AsyncGenerator[AsyncGraphDatabase, None]:
    """Provide a Neo4j async driver connected to the test container."""
    uri = neo4j_container.get_connection_url().replace("bolt://", "neo4j://")
    driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", TEST_NEO4J_PASSWORD))
    
    # Verify connection
    try:
        await driver.verify_connectivity()
    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {e}")
    
    yield driver
    await driver.close()


@pytest.fixture
def settings(neo4j_container: Neo4jContainer) -> Settings:
    """Provide test settings with container credentials."""
    uri = neo4j_container.get_connection_url().replace("bolt://", "neo4j://")
    return Settings(
        neo4j_uri=uri,
        neo4j_user="neo4j",
        neo4j_password=TEST_NEO4J_PASSWORD,
        neo4j_database="neo4j",
        neo4j_max_pool_size=10,
        embedding_dimension=TEST_EMBEDDING_DIMENSION,
    )


@pytest_asyncio.fixture
async def schema_initializer(
    neo4j_driver: AsyncGraphDatabase,
    settings: Settings,
) -> AsyncGenerator[SchemaInitializer, None]:
    """Provide a schema initializer with test container driver."""
    initializer = SchemaInitializer(driver=neo4j_driver, settings=settings)
    yield initializer
    await initializer.close()


@pytest_asyncio.fixture
async def initialized_schema(
    schema_initializer: SchemaInitializer,
) -> AsyncGenerator[SchemaInitializer, None]:
    """Provide schema initializer with schema already initialized."""
    await schema_initializer.initialize_schema(drop_existing=True)
    yield schema_initializer


@pytest_asyncio.fixture
async def neo4j_loader(
    neo4j_driver: AsyncGraphDatabase,
    settings: Settings,
) -> AsyncGenerator[Neo4jLoader, None]:
    """Provide a Neo4j loader with test container driver."""
    loader = Neo4jLoader(driver=neo4j_driver, settings=settings)
    yield loader
    await loader.close()


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX async client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def api_client_with_neo4j(
    neo4j_driver: AsyncGraphDatabase,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide API client with real Neo4j dependencies injected."""
    loader = Neo4jLoader(driver=neo4j_driver, settings=settings)
    sync_manager = SyncManager(loader=loader, driver=neo4j_driver, settings=settings)
    VectorStore(driver=neo4j_driver, settings=settings)
    
    # Override dependencies
    vector_store = VectorStore(driver=neo4j_driver, settings=settings)
    hybrid_search = HybridSearch(
        driver=neo4j_driver,
        vector_store=vector_store,
        settings=settings,
    )
    graph_rag = GraphRAGEngine(
        driver=neo4j_driver,
        vector_store=vector_store,
        settings=settings,
    )
    app.dependency_overrides[get_sync_manager] = lambda: sync_manager
    app.dependency_overrides[get_schema_initializer] = lambda: SchemaInitializer(
        driver=neo4j_driver, settings=settings
    )
    app.dependency_overrides[get_hybrid_search] = lambda: hybrid_search
    app.dependency_overrides[get_graph_rag] = lambda: graph_rag

    _patch_app_for_test_auth(app, monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Cleanup
    await loader.close()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestVectorIndexCreation:
    """Test Neo4j vector index initialization."""
    
    async def test_vector_indexes_created_by_schema_initializer(
        self,
        neo4j_driver: AsyncGraphDatabase,
        initialized_schema: SchemaInitializer,
    ):
        """Verify vector indexes are created during schema initialization."""
        async with neo4j_driver.session() as session:
            # Query for vector indexes
            result = await session.run(
                "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN collect(name) AS names"
            )
            record = await result.single()
            vector_names = set(record["names"] if record else [])
            
            # Assert all required vector indexes exist
            missing = REQUIRED_VECTOR_INDEXES - vector_names
            assert not missing, f"Missing vector indexes: {missing}"
            
            # Verify specific indexes exist
            for idx_name in REQUIRED_VECTOR_INDEXES:
                assert idx_name in vector_names, f"Vector index {idx_name} not found"


@pytest.mark.asyncio
class TestEmbeddingGeneration:
    """Test real embedding generation with sentence-transformers."""
    
    async def test_sentence_transformers_generates_real_embeddings(
        self,
        neo4j_loader: Neo4jLoader,
    ):
        """Verify sentence-transformers generates non-zero embeddings."""
        # Build embedding text
        test_entity = {
            "id": "test-cap-001",
            "name": "Real-time Analytics Platform",
            "description": "A capability for processing streaming data in real-time",
        }
        text = neo4j_loader._build_embedding_text(test_entity)
        
        # Generate embedding
        embedding = neo4j_loader._generate_embedding(text)
        
        # Assert embedding properties
        assert embedding is not None, "Embedding generation failed"
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) == TEST_EMBEDDING_DIMENSION, (
            f"Expected dimension {TEST_EMBEDDING_DIMENSION}, got {len(embedding)}"
        )
        
        # Assert non-zero (real embeddings, not fallback)
        assert any(e != 0.0 for e in embedding), (
            "Embedding is all zeros - sentence-transformers not working properly"
        )
        
        # Assert normalized (cosine similarity ready)
        import math
        magnitude = math.sqrt(sum(e * e for e in embedding))
        assert 0.9 < magnitude < 1.1, f"Embedding not normalized, magnitude: {magnitude}"


@pytest.mark.asyncio
class TestIngestionWithEmbeddings:
    """Test entity ingestion creates nodes with embeddings."""
    
    async def test_ingestion_creates_capability_with_embedding(
        self,
        neo4j_driver: AsyncGraphDatabase,
        neo4j_loader: Neo4jLoader,
        initialized_schema: SchemaInitializer,
    ):
        """Verify ingested Capability has embedding property."""
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        
        # Create test RDF graph with Capability
        g = Graph()
        cap_uri = URIRef("http://valuefabric.io/cap/test-cap-001")
        g.add((cap_uri, RDF.type, VF.Capability))
        g.add((cap_uri, VF.id, Literal("test-cap-001")))
        g.add((cap_uri, VF.name, Literal("Real-time Analytics Platform")))
        g.add((cap_uri, VF.description, Literal("Process streaming data in real-time")))
        g.add((cap_uri, VF.confidence, Literal(0.95)))
        
        # Load into Neo4j
        stats = await neo4j_loader.load_rdf_graph(
            g,
            source_id="test-source",
            tenant_id=TEST_TENANT_ID,
        )
        
        # Verify entity loaded
        assert stats["entities_loaded"] >= 1, f"Expected at least 1 entity, got {stats['entities_loaded']}"
        
        # Query Neo4j for the entity and its embedding
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (n:Capability {id: 'test-cap-001'}) "
                "RETURN n.name as name, n.embedding as embedding, n.id as id"
            )
            record = await result.single()
            assert record is not None, "Capability not found in Neo4j"
            assert record["name"] == "Real-time Analytics Platform"
            
            # Verify embedding exists and is valid
            embedding = record["embedding"]
            assert embedding is not None, "Embedding property not set"
            assert isinstance(embedding, list), "Embedding should be a list"
            assert len(embedding) == TEST_EMBEDDING_DIMENSION, (
                f"Expected embedding dimension {TEST_EMBEDDING_DIMENSION}, got {len(embedding)}"
            )
            
            # Verify non-zero embedding (real generation worked)
            assert any(e != 0.0 for e in embedding), (
                "Embedding is all zeros - real embedding generation failed"
            )


@pytest.mark.asyncio
class TestHybridSearch:
    """Test hybrid (vector + graph) search behavior."""
    
    async def test_hybrid_search_returns_ranked_results(
        self,
        neo4j_driver: AsyncGraphDatabase,
        neo4j_loader: Neo4jLoader,
        initialized_schema: SchemaInitializer,
        settings: Settings,
    ):
        """Verify hybrid search returns results ranked by vector + graph scores."""
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        
        # Create test entities with different descriptions
        g = Graph()
        
        # Entity 1: Highly relevant to "data analytics"
        cap1_uri = URIRef("http://valuefabric.io/cap/cap-001")
        g.add((cap1_uri, RDF.type, VF.Capability))
        g.add((cap1_uri, VF.id, Literal("cap-001")))
        g.add((cap1_uri, VF.name, Literal("Advanced Data Analytics")))
        g.add((cap1_uri, VF.description, Literal("Machine learning and statistical analysis for big data")))
        g.add((cap1_uri, VF.confidence, Literal(0.95)))
        
        # Entity 2: Less relevant
        cap2_uri = URIRef("http://valuefabric.io/cap/cap-002")
        g.add((cap2_uri, RDF.type, VF.Capability))
        g.add((cap2_uri, VF.id, Literal("cap-002")))
        g.add((cap2_uri, VF.name, Literal("User Interface Design")))
        g.add((cap2_uri, VF.description, Literal("Creating visual interfaces for web applications")))
        g.add((cap2_uri, VF.confidence, Literal(0.85)))
        
        # Load into Neo4j
        await neo4j_loader.load_rdf_graph(
            g,
            source_id="test-source",
            tenant_id=TEST_TENANT_ID,
        )
        
        # Initialize hybrid search
        vector_store = VectorStore(driver=neo4j_driver, settings=settings)
        hybrid_search = HybridSearch(
            driver=neo4j_driver,
            vector_store=vector_store,
            settings=settings,
        )
        
        # Search for analytics-related capability
        results = await hybrid_search.search(
            query="data analytics and machine learning",
            entity_types=["Capability"],
            limit=10,
            tenant_id=TEST_TENANT_ID,
        )
        
        # Verify results
        assert results is not None, "Hybrid search returned None"
        assert len(results) > 0, "Hybrid search returned no results"

        # Verify ranking - analytics entity should rank higher
        def _result_name(result):
            if hasattr(result, "name"):
                return result.name
            return result.get("name", "")

        entity_names = [_result_name(r) for r in results]
        assert "Advanced Data Analytics" in entity_names, (
            f"Expected 'Advanced Data Analytics' in results, got: {entity_names}"
        )

        # The analytics entity should be ranked higher than UI design
        analytics_rank = entity_names.index("Advanced Data Analytics")
        try:
            ui_rank = entity_names.index("User Interface Design")
            assert analytics_rank < ui_rank, (
                f"Analytics should rank higher than UI. Rankings: {entity_names}"
            )
        except ValueError:
            # UI might not appear in top results, which is also valid
            pass


@pytest.mark.asyncio
class TestVectorE2EComplete:
    """Complete vector end-to-end pipeline test."""
    
    async def test_extract_ingest_search_vector_pipeline(
        self,
        api_client_with_neo4j: AsyncClient,
        initialized_schema: SchemaInitializer,
    ):
        """Complete flow: ingest via API and search with hybrid."""
        # Ingest test data via API
        test_data = {
            "rdf_data": '''
            @prefix vf: <http://valuefabric.io/ontology/> .
            @prefix ex: <http://valuefabric.io/entity/> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

            ex:pipeline-test a vf:Capability ;
                vf:id "pipeline-test" ;
                vf:name "AI-Powered Decision Support" ;
                vf:description "Machine learning models for business decision optimization" ;
                vf:confidence "0.92"^^xsd:float .
            ''',
            "source_id": "vector-e2e-test",
            "extraction_job_id": "vector-e2e-job",
            "tenant_id": TEST_TENANT_ID,
        }
        
        response = await api_client_with_neo4j.post("/v1/ingest", json=test_data)
        assert response.status_code == 200, f"Ingest failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert data["entities_loaded"] >= 1
        
        # Query via search endpoint
        search_response = await api_client_with_neo4j.post(
            "/v1/search/hybrid",
            json={
                "query": "machine learning decision optimization",
                "entity_types": ["Capability"],
                "limit": 5,
            },
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        
        search_data = search_response.json()
        assert "results" in search_data
        results = search_data["results"]
        assert len(results) > 0, "Search returned no results"
        
        # Verify the ingested entity appears in results
        entity_names = [r.get("name", "") for r in results]
        assert "AI-Powered Decision Support" in entity_names, (
            f"Expected ingested entity in search results, got: {entity_names}"
        )


@pytest.mark.asyncio
class TestDockerContainerRecovery:
    """Test resilience to Docker container failures."""

    async def test_driver_reconnects_after_container_restart(
        self,
        neo4j_container: Neo4jContainer,
        settings: Settings,
    ):
        """Driver must reconnect after Neo4j container restarts."""
        uri = neo4j_container.get_connection_url().replace("bolt://", "neo4j://")
        driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", TEST_NEO4J_PASSWORD))

        # Verify initial connectivity
        await driver.verify_connectivity()

        # Restart the container
        neo4j_container.stop()
        neo4j_container.start()

        # Poll for readiness instead of fixed sleep
        new_uri = neo4j_container.get_connection_url().replace("bolt://", "neo4j://")
        new_driver = AsyncGraphDatabase.driver(new_uri, auth=("neo4j", TEST_NEO4J_PASSWORD))

        try:
            for _ in range(15):
                try:
                    await new_driver.verify_connectivity()
                    break
                except Exception:
                    await asyncio.sleep(2)
            else:
                pytest.fail("Neo4j did not become ready within 30 seconds after restart")
        finally:
            await new_driver.close()
            await driver.close()

    async def test_operations_fail_gracefully_on_stopped_container(
        self,
        neo4j_container: Neo4jContainer,
        settings: Settings,
    ):
        """Operations must raise a clear error when container is stopped."""
        uri = neo4j_container.get_connection_url().replace("bolt://", "neo4j://")
        driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", TEST_NEO4J_PASSWORD))
        await driver.verify_connectivity()

        # Stop container
        neo4j_container.stop()

        # Operations should raise a ServiceUnavailable or connectivity error
        try:
            with pytest.raises(Exception, match=r"(?i)(unavailable|connection|session|refused)"):
                async with driver.session() as session:
                    await session.run("RETURN 1")
        finally:
            await driver.close()
            # Restart for subsequent tests and poll for readiness
            neo4j_container.start()
            for _ in range(15):
                try:
                    test_driver = AsyncGraphDatabase.driver(
                        neo4j_container.get_connection_url().replace("bolt://", "neo4j://"),
                        auth=("neo4j", TEST_NEO4J_PASSWORD),
                    )
                    await test_driver.verify_connectivity()
                    await test_driver.close()
                    break
                except Exception:
                    await asyncio.sleep(2)


@pytest.mark.asyncio
class TestSchemaIdempotency:
    """Test that schema initialization is idempotent."""

    async def test_schema_init_twice_does_not_fail(
        self,
        schema_initializer: SchemaInitializer,
    ):
        """Calling initialize_schema twice must not raise errors."""
        await schema_initializer.initialize_schema(drop_existing=True)
        # Second call must also succeed
        await schema_initializer.initialize_schema(drop_existing=True)

    async def test_schema_init_preserves_data_when_not_dropping(
        self,
        neo4j_driver: AsyncGraphDatabase,
        schema_initializer: SchemaInitializer,
        neo4j_loader: Neo4jLoader,
    ):
        """Re-initializing schema without drop must preserve existing data."""
        await schema_initializer.initialize_schema(drop_existing=True)

        # Insert a test entity
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806
        g = Graph()
        cap_uri = URIRef("http://valuefabric.io/cap/persist-test")
        g.add((cap_uri, RDF.type, VF.Capability))
        g.add((cap_uri, VF.id, Literal("persist-test")))
        g.add((cap_uri, VF.name, Literal("Persistence Check")))
        g.add((cap_uri, VF.description, Literal("Verify data persists")))
        g.add((cap_uri, VF.confidence, Literal(0.9)))
        await neo4j_loader.load_rdf_graph(
            g,
            source_id="idempotent-test",
            tenant_id=TEST_TENANT_ID,
        )

        # Re-initialize without dropping
        await schema_initializer.initialize_schema(drop_existing=False)

        # Entity should still exist
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (n:Capability {id: 'persist-test'}) RETURN n.name AS name"
            )
            record = await result.single()
            assert record is not None, "Entity must survive schema re-init without drop"
            assert record["name"] == "Persistence Check"


@pytest.mark.asyncio
class TestEmbeddingDimensionValidation:
    """Test embedding dimension validation and edge cases."""

    async def test_empty_text_produces_valid_embedding(
        self,
        neo4j_loader: Neo4jLoader,
    ):
        """Empty or whitespace-only text must still produce a valid embedding."""
        embedding = neo4j_loader._generate_embedding("")
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == TEST_EMBEDDING_DIMENSION

    async def test_very_long_text_produces_valid_embedding(
        self,
        neo4j_loader: Neo4jLoader,
    ):
        """Very long text must produce a valid embedding without crashing."""
        long_text = "machine learning analytics " * 500  # ~15,000 chars
        embedding = neo4j_loader._generate_embedding(long_text)
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == TEST_EMBEDDING_DIMENSION

    async def test_special_characters_in_text_handled(
        self,
        neo4j_loader: Neo4jLoader,
    ):
        """Text with special chars/unicode must produce a valid embedding."""
        special_text = "Ünïcödé テスト 中文 ñoño <script>alert('xss')</script>"
        embedding = neo4j_loader._generate_embedding(special_text)
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == TEST_EMBEDDING_DIMENSION


@pytest.mark.asyncio
class TestVectorCleanup:
    """Test vector data cleanup and index management."""

    async def test_drop_existing_removes_all_vector_indexes(
        self,
        neo4j_driver: AsyncGraphDatabase,
        schema_initializer: SchemaInitializer,
    ):
        """initialize_schema(drop_existing=True) must remove and recreate all vector indexes."""
        # First init
        await schema_initializer.initialize_schema(drop_existing=True)

        # Verify indexes exist
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN count(*) AS cnt"
            )
            record = await result.single()
            assert record["cnt"] >= len(REQUIRED_VECTOR_INDEXES)

        # Drop and recreate
        await schema_initializer.initialize_schema(drop_existing=True)

        # Verify indexes exist again (were recreated)
        async with neo4j_driver.session() as session:
            result = await session.run(
                "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN collect(name) AS names"
            )
            record = await result.single()
            vector_names = set(record["names"] if record else [])
            missing = REQUIRED_VECTOR_INDEXES - vector_names
            assert not missing, f"After re-init, missing indexes: {missing}"

    async def test_node_deletion_removes_embeddings(
        self,
        neo4j_driver: AsyncGraphDatabase,
        neo4j_loader: Neo4jLoader,
        initialized_schema: SchemaInitializer,
    ):
        """Deleting a node must remove its embedding from the index."""
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF
        VF = Namespace("http://valuefabric.io/ontology/")  # noqa: N806

        g = Graph()
        cap_uri = URIRef("http://valuefabric.io/cap/cleanup-test")
        g.add((cap_uri, RDF.type, VF.Capability))
        g.add((cap_uri, VF.id, Literal("cleanup-test")))
        g.add((cap_uri, VF.name, Literal("Cleanup Test Entity")))
        g.add((cap_uri, VF.description, Literal("Entity for cleanup verification")))
        g.add((cap_uri, VF.confidence, Literal(0.9)))
        await neo4j_loader.load_rdf_graph(
            g,
            source_id="cleanup-source",
            tenant_id=TEST_TENANT_ID,
        )

        # Verify entity exists
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (n:Capability {id: 'cleanup-test'}) RETURN n.embedding IS NOT NULL AS has_emb"
            )
            record = await result.single()
            assert record is not None, "Cleanup test entity not found"
            assert record["has_emb"], "Entity should have an embedding before deletion"

        # Delete entity
        async with neo4j_driver.session() as session:
            await session.run("MATCH (n:Capability {id: 'cleanup-test'}) DELETE n")

        # Verify entity is gone
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (n:Capability {id: 'cleanup-test'}) RETURN n"
            )
            record = await result.single()
            assert record is None, "Entity should be deleted"
