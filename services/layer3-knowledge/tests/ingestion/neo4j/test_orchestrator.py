from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from rdflib import Graph

from src.ingestion.neo4j.connection import Neo4jConnectionManager
from src.ingestion.neo4j.embeddings import EmbeddingGenerator
from src.ingestion.neo4j.extractors import RDFEntityExtractor, RDFRelationshipExtractor
from src.ingestion.neo4j.orchestrator import BatchImportOrchestrator
from src.ingestion.neo4j.writers import EntityBatchWriter, RelationshipBatchWriter

TENANT = "12345678-1234-1234-1234-123456789abc"


class _FakeEmbeddingGenerator:
    def attach(self, entity_type, entities):
        return entities


class _FakeSession:
    async def run(self, query, parameters=None):
        return SimpleNamespace(single=AsyncMock(return_value=None))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def session(self, database=None):
        return _FakeSession()


@pytest.mark.asyncio
async def test_load_rdf_graph_rejects_missing_tenant():
    orchestrator = BatchImportOrchestrator(
        connection=Neo4jConnectionManager(driver=_FakeDriver()),
        entity_extractor=RDFEntityExtractor(),
        relationship_extractor=RDFRelationshipExtractor(),
        embedding_generator=_FakeEmbeddingGenerator(),
        entity_writer=EntityBatchWriter(),
        relationship_writer=RelationshipBatchWriter(),
    )
    with pytest.raises(Exception, match="tenant_id is required"):
        await orchestrator.load_rdf_graph(Graph())


@pytest.mark.asyncio
async def test_load_rdf_graph_accumulates_stats():
    created = []

    class _FakeGateway:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created.append(self)

        async def write_nodes_batch(self, label, nodes):
            return {"count": len(nodes)}

        async def write_relationships_batch(self, rel_type, triples):
            return {"count": len(triples)}

    def _gateway_factory(**kwargs):
        return _FakeGateway(**kwargs)

    class _FakeExtractor:
        def extract(self, graph):
            return {"Capability": [{"id": "c1", "name": "Cap"}]}

    class _FakeRelExtractor:
        def extract(self, graph, source_id=None, extraction_job_id=None):
            return {"enables": [{"source_id": "c1", "target_id": "u1", "predicate": "enables"}]}

    orchestrator = BatchImportOrchestrator(
        connection=Neo4jConnectionManager(driver=_FakeDriver()),
        entity_extractor=_FakeExtractor(),
        relationship_extractor=_FakeRelExtractor(),
        embedding_generator=_FakeEmbeddingGenerator(),
        entity_writer=EntityBatchWriter(mutation_gateway=_gateway_factory),
        relationship_writer=RelationshipBatchWriter(mutation_gateway=_gateway_factory),
    )

    stats = await orchestrator.load_rdf_graph(
        Graph(), source_id="s1", extraction_job_id="j1", tenant_id=TENANT
    )

    assert stats["entities_loaded"] == 1
    assert stats["relationships_loaded"] == 1
    assert stats["triples_processed"] == 0
