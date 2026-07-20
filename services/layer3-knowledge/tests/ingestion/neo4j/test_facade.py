from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from rdflib import Graph

from src.ingestion.neo4j.facade import Neo4jLoader

TENANT = "12345678-1234-1234-1234-123456789abc"


class _FakeSession:
    def __init__(self):
        self.calls = []

    async def run(self, query, parameters=None):
        self.calls.append((query, parameters))
        return SimpleNamespace(single=AsyncMock(return_value=None))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def session(self, database=None):
        return _FakeSession()


@pytest.mark.asyncio
async def test_facade_public_api_unchanged():
    loader = Neo4jLoader(
        driver=_FakeDriver(), settings=SimpleNamespace(use_apoc=False)
    )
    assert loader.batch_size == 1000
    assert hasattr(loader, "load_rdf_graph")
    assert hasattr(loader, "load_turtle_string")
    assert hasattr(loader, "delete_by_source")

    with pytest.raises(Exception, match="tenant_id is required"):
        await loader.load_rdf_graph(Graph())


@pytest.mark.asyncio
async def test_facade_private_extractors_still_work():
    from rdflib import Literal, Namespace, URIRef
    from rdflib.namespace import RDF

    VF = Namespace("https://valuefabric.io/ontology/")
    g = Graph()
    cap = URIRef("https://valuefabric.io/entity/cap-1")
    g.add((cap, RDF.type, VF.Capability))
    g.add((cap, VF.name, Literal("Cap")))

    loader = Neo4jLoader(
        driver=_FakeDriver(), settings=SimpleNamespace(use_apoc=False)
    )
    entities = loader._extract_entities_from_rdf(g)
    assert entities["Capability"][0]["name"] == "Cap"
