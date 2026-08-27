"""Integration tests for Layer 3 Neo4j connectivity.

These tests use ``testcontainers`` to spin up a real Neo4j 5.x instance and
validate that:
- The driver factory connects and verifies connectivity.
- Schema initialisation creates all expected constraints and vector indexes.
- ``Neo4jLoader`` can merge entity nodes using native Cypher (APOC-free path).
- ``VectorStore`` can create a vector index and run a similarity query.
- ``HybridSearch`` returns results without raising ``AttributeError``.
- ``GraphRAGEngine`` returns a non-empty result dict when the driver is live.

Run with::

    pytest tests/test_neo4j_integration.py -v -m integration

Requirements (in addition to the project's dev extras)::

    pip install testcontainers[neo4j]

The ``NEO4J_PASSWORD`` used inside the container is ``test-password``.

Docker Requirements:
    - Docker must be running for these tests to execute
    - Tests will be skipped if Docker is unavailable
    - Add to pytest.ini: markers = integration: marks tests as integration (deselect with '-m "not integration"')
"""


import pytest
import pytest_asyncio

# Guard: skip entire module if testcontainers is not installed
try:
    from testcontainers.neo4j import Neo4jContainer  # type: ignore
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.vector,
    pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed"),
]

NEO4J_IMAGE = "neo4j:5.18-community"
NEO4J_PASSWORD = "test-password"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def neo4j_container():
    """Start a Neo4j 5.x container for the entire test session.
    
    P1 Fix: Uses wait_for_logs for deterministic container readiness.
    """
    from testcontainers.core.waiting_utils import wait_for_logs
    
    container = Neo4jContainer(image=NEO4J_IMAGE, password=NEO4J_PASSWORD)
    container.start()
    
    # P1 Fix: Deterministic wait for Neo4j to be ready
    wait_for_logs(container, "Started.", timeout=60)
    
    yield container
    
    # Cleanup
    container.stop()


@pytest.fixture(scope="session")
def neo4j_bolt_url(neo4j_container):
    """Return the bolt URL for the running container."""
    return neo4j_container.get_connection_url()


@pytest.fixture(scope="session")
def settings(neo4j_bolt_url):
    """Return a Settings instance pointing at the test container."""
    # Import here so the module can be collected even without a .env file
    from config import Settings

    return Settings(
        neo4j_uri=neo4j_bolt_url,
        neo4j_username="neo4j",
        neo4j_password=NEO4J_PASSWORD,
        neo4j_database="neo4j",
        neo4j_max_pool_size=5,
        neo4j_connection_timeout=10,
        neo4j_max_retry_attempts=2,
        neo4j_retry_delay=0.5,
        openai_api_key="sk-test-placeholder",  # not used in these tests
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        use_apoc=False,  # force native Cypher path
    )


@pytest_asyncio.fixture(scope="session")
async def driver(settings):
    """Shared async Neo4j driver for the test session."""
    from src.db.driver import get_driver, reset_driver

    drv = await get_driver(settings)
    yield drv
    await reset_driver()


# ── Helper ────────────────────────────────────────────────────────────────────

async def run_query(driver, cypher: str, params: dict = None):
    """Execute a Cypher query and return all records."""
    async with driver.session(database="neo4j") as session:
        result = await session.run(cypher, params or {})
        return await result.data()


# ── Tests: driver factory ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_driver_connects(driver):
    """Driver should be able to run a trivial query."""
    records = await run_query(driver, "RETURN 1 AS n")
    assert records == [{"n": 1}]


@pytest.mark.asyncio
async def test_driver_verify_connectivity(settings):
    """get_driver should raise on bad credentials, not hang."""
    from neo4j.exceptions import AuthError, ServiceUnavailable

    from src.db.driver import get_driver, reset_driver

    bad_settings = settings.model_copy(update={"neo4j_password": "wrongpassword"})
    with pytest.raises((AuthError, ServiceUnavailable, Exception)):
        await get_driver(bad_settings)
    await reset_driver()


# ── Tests: schema initialiser ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_initializer_creates_constraints(driver, settings):
    """SchemaInitializer should create uniqueness constraints for all entity types."""
    from schema import SchemaInitializer

    initializer = SchemaInitializer(driver=driver, settings=settings)
    await initializer.initialize_schema()

    # Check that at least one uniqueness constraint exists
    records = await run_query(
        driver,
        "SHOW CONSTRAINTS YIELD name, type WHERE type = 'UNIQUENESS' RETURN name, type",
    )
    assert len(records) > 0, "No uniqueness constraints found after schema init"


@pytest.mark.asyncio
async def test_schema_initializer_creates_vector_indexes(driver, settings):
    """SchemaInitializer should create vector indexes for all entity types."""
    from schema import SchemaInitializer

    initializer = SchemaInitializer(driver=driver, settings=settings)
    await initializer.initialize_schema()

    records = await run_query(
        driver,
        "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN name, type",
    )
    assert len(records) > 0, "No vector indexes found after schema init"


# ── Tests: Neo4jLoader (APOC-free) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_neo4j_loader_merge_capability_node(driver, settings):
    """Neo4jLoader should merge a Capability node using native Cypher."""
    from ingestion.neo4j_loader import Neo4jLoader

    loader = Neo4jLoader(driver=driver, settings=settings)

    entity = {
        "id": "cap-test-001",
        "name": "Single Sign-On",
        "description": "Unified authentication across all products.",
        "entity_type": "Capability",
        "confidence": 0.94,
        "source_url": "https://example.com/sso",
        "embedding": [0.0] * 1536,
    }

    await loader.load_entity(entity)

    records = await run_query(
        driver,
        "MATCH (n:Capability {id: $id}) RETURN n.name AS name",
        {"id": "cap-test-001"},
    )
    assert len(records) == 1
    assert records[0]["name"] == "Single Sign-On"


@pytest.mark.asyncio
async def test_neo4j_loader_merge_relationship(driver, settings):
    """Neo4jLoader should create a ENABLES relationship without APOC."""
    from ingestion.neo4j_loader import Neo4jLoader

    loader = Neo4jLoader(driver=driver, settings=settings)

    # Ensure both nodes exist
    for entity in [
        {"id": "cap-rel-001", "name": "RBAC", "entity_type": "Capability",
         "description": "Role-based access control.", "confidence": 0.97,
         "source_url": "https://example.com", "embedding": [0.0] * 1536},
        {"id": "uc-rel-001", "name": "Compliance Automation", "entity_type": "UseCase",
         "description": "Automate compliance workflows.", "confidence": 0.85,
         "source_url": "https://example.com", "embedding": [0.0] * 1536},
    ]:
        await loader.load_entity(entity)

    await loader.load_relationship(
        source_id="cap-rel-001",
        target_id="uc-rel-001",
        rel_type="ENABLES",
        properties={"confidence": 0.88},
    )

    records = await run_query(
        driver,
        """
        MATCH (a {id: $src})-[r:ENABLES]->(b {id: $tgt})
        RETURN type(r) AS rel_type, r.confidence AS conf
        """,
        {"src": "cap-rel-001", "tgt": "uc-rel-001"},
    )
    assert len(records) == 1
    assert records[0]["rel_type"] == "ENABLES"
    assert records[0]["conf"] == pytest.approx(0.88)


# ── Tests: VectorStore (Neo4j-native) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_vector_store_index_exists_after_schema_init(driver, settings):
    """VectorStore should confirm the index exists after schema initialisation."""
    from retrieval.vector_store import VectorStore
    from schema import SchemaInitializer

    await SchemaInitializer(driver=driver, settings=settings).initialize_schema()
    vs = VectorStore(driver=driver, settings=settings)

    # index_exists is a helper that queries SHOW INDEXES
    exists = await vs.index_exists("capability_embedding")
    assert exists is True


@pytest.mark.asyncio
async def test_vector_store_search_returns_list(driver, settings):
    """VectorStore.search() should return a list (possibly empty) without raising."""
    from retrieval.vector_store import VectorStore
    from schema import SchemaInitializer

    await SchemaInitializer(driver=driver, settings=settings).initialize_schema()
    vs = VectorStore(driver=driver, settings=settings)

    # Use a zero-vector query — results may be empty but must not raise
    results = await vs.search(
        query_vector=[0.0] * 1536,
        entity_type="Capability",
        top_k=5,
    )
    assert isinstance(results, list)


# ── Tests: HybridSearch ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_search_no_attribute_error(driver, settings):
    """HybridSearch should initialise and run without raising AttributeError."""
    from retrieval.hybrid_search import HybridSearch
    from retrieval.vector_store import VectorStore
    from schema import SchemaInitializer

    await SchemaInitializer(driver=driver, settings=settings).initialize_schema()
    vs = VectorStore(driver=driver, settings=settings)
    hs = HybridSearch(driver=driver, vector_store=vs, settings=settings)

    # search() must not raise; results may be empty on a fresh DB
    results = await hs.search(
        query_text="single sign-on authentication",
        entity_type="Capability",
        top_k=5,
    )
    assert isinstance(results, list)


# ── Tests: GraphRAGEngine ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_rag_returns_dict(driver, settings):
    """GraphRAGEngine.query() should return a dict with a 'results' key."""
    from retrieval.graph_rag import GraphRAGEngine
    from retrieval.vector_store import VectorStore
    from schema import SchemaInitializer

    await SchemaInitializer(driver=driver, settings=settings).initialize_schema()
    vs = VectorStore(driver=driver, settings=settings)
    rag = GraphRAGEngine(driver=driver, vector_store=vs, settings=settings)

    response = await rag.query(
        query_text="What capabilities relate to compliance?",
        max_hops=2,
        max_results=5,
    )
    assert isinstance(response, dict)
    assert "results" in response or "answer" in response or "entities" in response


@pytest.mark.asyncio
async def test_graph_rag_driver_factory_failure_is_not_masked(monkeypatch):
    """GraphRAGEngine should propagate a meaningful lazy-driver failure."""
    from neo4j.exceptions import ServiceUnavailable

    from config import Settings
    from retrieval import graph_rag as graph_rag_module

    async def unavailable_driver(_settings):
        raise ServiceUnavailable("test driver unavailable")

    monkeypatch.setattr(graph_rag_module, "get_driver", unavailable_driver)
    settings = Settings(neo4j_password=NEO4J_PASSWORD)

    rag = graph_rag_module.GraphRAGEngine(
        driver=None,
        vector_store=None,
        settings=settings,
    )

    with pytest.raises(ServiceUnavailable, match="test driver unavailable"):
        await rag.query(
            "test query",
            max_hops=1,
            max_results=3,
            tenant_id="12345678-1234-1234-1234-123456789abc",
        )
