"""Tests for RDF ingestion pipeline."""

from types import SimpleNamespace

import pytest
from rdflib import RDF, Graph, Literal, Namespace, URIRef

from src.ingestion import Neo4jLoader, RDFLoadError
from src.ingestion.neo4j import (
    TenantValidationError,
    validate_ingestion_tenant_id,
)


TEST_TENANT_ID = "12345678-1234-1234-1234-123456789abc"
TEST_SETTINGS = SimpleNamespace(
    neo4j_database="neo4j",
    use_apoc=False,
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
)


class _FakeResult:
    def __init__(self, loaded: int):
        self._loaded = loaded

    async def single(self):
        return {"loaded": self._loaded}


class _FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query, params):
        self.calls.append((query, params))
        if "nodes" in params:
            return _FakeResult(len(params["nodes"]))
        if "triples" in params:
            return _FakeResult(len(params["triples"]))
        return _FakeResult(0)


class _FakeSessionContext:
    def __init__(self, session: _FakeSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def __init__(self, session: _FakeSession):
        self._session = session

    def session(self, database=None):
        return _FakeSessionContext(self._session)


class _FakeEmbeddingModel:
    def encode(self, text, normalize_embeddings=True):
        return SimpleNamespace(tolist=lambda: [0.1, 0.2])


@pytest.fixture
def sample_rdf_graph():
    """Create a sample RDF graph for testing."""
    g = Graph()
    VF = Namespace("https://valuefabric.io/ontology/")  # noqa: N806

    # Add sample capability
    cap = URIRef("https://valuefabric.io/entity/cap-1")
    g.add((cap, RDF.type, VF.Capability))
    g.add((cap, VF.name, Literal("Real-Time Data Ingestion")))
    g.add((cap, VF.description, Literal("Stream data with low latency")))
    g.add((cap, VF.confidence, Literal(0.95)))

    # Add sample use case
    uc = URIRef("https://valuefabric.io/entity/uc-1")
    g.add((uc, RDF.type, VF.UseCase))
    g.add((uc, VF.name, Literal("Touchless Accounts Payable")))
    g.add((uc, VF.description, Literal("Automated AP processing")))

    # Add relationship
    g.add((cap, VF.enables, uc))

    return g


@pytest.mark.asyncio
async def test_extract_entities_from_rdf(sample_rdf_graph):
    """Test entity extraction from RDF graph."""
    loader = Neo4jLoader(settings=TEST_SETTINGS)

    entities = loader._extract_entities_from_rdf(sample_rdf_graph)

    assert "Capability" in entities
    assert "UseCase" in entities
    assert len(entities["Capability"]) == 1
    assert len(entities["UseCase"]) == 1

    cap = entities["Capability"][0]
    assert cap["name"] == "Real-Time Data Ingestion"
    assert cap["confidence"] == 0.95


@pytest.mark.asyncio
async def test_extract_relationships_from_rdf(sample_rdf_graph):
    """Test relationship extraction from RDF graph."""
    loader = Neo4jLoader(settings=TEST_SETTINGS)

    relationships = loader._extract_relationships_from_rdf(sample_rdf_graph)

    assert len(relationships) == 1
    assert relationships[0]["predicate"] == "enables"
    assert "cap-1" in relationships[0]["source_id"]
    assert "uc-1" in relationships[0]["target_id"]


@pytest.mark.asyncio
async def test_load_turtle_string():
    """Test loading Turtle-formatted RDF."""
    turtle_data = '''
    @prefix vf: <https://valuefabric.io/ontology/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    <https://valuefabric.io/entity/cap-1> a vf:Capability ;
        vf:name "Test Capability" ;
        vf:confidence "0.9"^^xsd:float .
    '''

    Neo4jLoader(settings=TEST_SETTINGS)

    # This would require a real Neo4j instance
    # For unit tests, we just verify parsing works
    try:
        from rdflib import Graph
        g = Graph()
        g.parse(data=turtle_data, format="turtle")
        assert len(g) > 0
    except Exception as e:
        pytest.fail(f"Turtle parsing failed: {e}")


def test_validate_ingestion_tenant_id_rejects_missing_or_empty():
    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        validate_ingestion_tenant_id(None)

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        validate_ingestion_tenant_id("   ")


def test_validate_ingestion_tenant_id_rejects_malformed():
    with pytest.raises(TenantValidationError, match="Invalid tenant_id format"):
        validate_ingestion_tenant_id("system")

    with pytest.raises(TenantValidationError, match="Invalid tenant_id format"):
        validate_ingestion_tenant_id("not-a-uuid")


@pytest.mark.asyncio
async def test_load_rdf_graph_rejects_missing_tenant_id(sample_rdf_graph):
    loader = Neo4jLoader(settings=TEST_SETTINGS)

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await loader.load_rdf_graph(sample_rdf_graph, source_id="source-1", extraction_job_id="job-1")


@pytest.mark.asyncio
async def test_load_turtle_string_rejects_invalid_tenant_id():
    loader = Neo4jLoader(settings=TEST_SETTINGS)
    turtle_data = """
    @prefix vf: <https://valuefabric.io/ontology/> .
    <https://valuefabric.io/entity/cap-1> a vf:Capability ;
        vf:name "Test Capability" .
    """

    with pytest.raises(RDFLoadError, match="Invalid tenant_id format"):
        await loader.load_turtle_string(
            turtle_data,
            source_id="source-1",
            extraction_job_id="job-1",
            tenant_id="system",
        )


@pytest.mark.asyncio
async def test_batch_loaders_reject_missing_tenant_id():
    loader = Neo4jLoader(settings=TEST_SETTINGS)
    session = _FakeSession()

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await loader._load_entities_batch(
            session,
            "Capability",
            [{"id": "cap-1", "name": "Capability One"}],
            "source-1",
            "job-1",
            None,
        )

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await loader._load_relationships_batch(
            session,
            {"enables": [{"source_id": "cap-1", "target_id": "uc-1", "predicate": "enables"}]},
            "source-1",
            "job-1",
            None,
        )


@pytest.mark.asyncio
async def test_load_rdf_graph_persists_valid_tenant_on_entities_and_relationships(sample_rdf_graph):
    session = _FakeSession()
    loader = Neo4jLoader(driver=_FakeDriver(session), settings=TEST_SETTINGS)
    loader._orchestrator.embedding_generator._model = _FakeEmbeddingModel()

    stats = await loader.load_rdf_graph(
        sample_rdf_graph,
        source_id="source-1",
        extraction_job_id="job-1",
        tenant_id=TEST_TENANT_ID,
    )

    assert stats["entities_loaded"] >= 2
    assert stats["relationships_loaded"] >= 1
    assert len(session.calls) >= 3

    entity_calls = [params for _, params in session.calls if "nodes" in params]
    relationship_calls = [params for _, params in session.calls if "triples" in params]

    assert entity_calls
    assert relationship_calls
    assert all(
        node["properties"]["tenant_id"] == TEST_TENANT_ID
        for call in entity_calls
        for node in call["nodes"]
    )
    assert all(call["tenant_id"] == TEST_TENANT_ID for call in entity_calls)
    assert all(call["tenant_id"] == TEST_TENANT_ID for call in relationship_calls)
