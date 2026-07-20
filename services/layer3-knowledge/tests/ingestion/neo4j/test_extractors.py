import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from src.ingestion.neo4j.extractors import (
    RDFEntityExtractor,
    RDFRelationshipExtractor,
)

VF = Namespace("https://valuefabric.io/ontology/")


@pytest.fixture
def sample_graph():
    g = Graph()
    cap = URIRef("https://valuefabric.io/entity/cap-1")
    g.add((cap, RDF.type, VF.Capability))
    g.add((cap, VF.name, Literal("Real-Time Data Ingestion")))
    g.add((cap, VF.confidence, Literal(0.95)))

    uc = URIRef("https://valuefabric.io/entity/uc-1")
    g.add((uc, RDF.type, VF.UseCase))
    g.add((uc, VF.name, Literal("Touchless AP")))

    g.add((cap, VF.enables, uc))
    return g


def test_extract_entities(sample_graph):
    entities = RDFEntityExtractor.extract(sample_graph)
    assert len(entities["Capability"]) == 1
    assert entities["Capability"][0]["name"] == "Real-Time Data Ingestion"
    assert entities["Capability"][0]["confidence"] == 0.95


def test_extract_relationships_flat(sample_graph):
    relationships = RDFRelationshipExtractor.extract(sample_graph)
    assert isinstance(relationships, list)
    assert relationships[0]["predicate"] == "enables"


def test_extract_relationships_grouped(sample_graph):
    relationships = RDFRelationshipExtractor.extract(
        sample_graph, source_id="s1", extraction_job_id="j1"
    )
    assert isinstance(relationships, dict)
    assert relationships["enables"][0]["source"] == "s1"
