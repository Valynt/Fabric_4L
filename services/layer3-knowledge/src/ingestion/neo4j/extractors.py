from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from ...schema.constraints import ENTITY_TYPES, RELATIONSHIP_TYPES
from .constants import VF, VF_HTTPS


class RDFEntityExtractor:
    """Pure functions for pulling typed entities out of an RDF graph."""

    @staticmethod
    def extract(graph: Graph) -> dict[str, list[dict[str, Any]]]:
        """Extract entities grouped by type from an RDF graph."""
        entities: dict[str, list[dict[str, Any]]] = {et: [] for et in ENTITY_TYPES}

        for entity_type in ENTITY_TYPES:
            type_uris = (VF[entity_type], VF_HTTPS[entity_type])
            subjects = {
                s for type_uri in type_uris for s in graph.subjects(RDF.type, type_uri)
            }

            for subject in subjects:
                entity_data: dict[str, Any] = {"uri": str(subject)}

                for predicate, obj in graph.predicate_objects(subject):
                    pred_name = RDFEntityExtractor._property_name(predicate)

                    if isinstance(obj, Literal):
                        if obj.datatype:
                            entity_data[pred_name] = RDFEntityExtractor._convert_literal(
                                obj
                            )
                        else:
                            entity_data[pred_name] = str(obj)
                    elif isinstance(obj, URIRef):
                        entity_data[pred_name] = str(obj)

                entity_data["id"] = entity_data.get("id") or str(subject)
                entities[entity_type].append(entity_data)

        return entities

    @staticmethod
    def _property_name(uri: URIRef) -> str:
        """Extract property name from URI."""
        uri_str = str(uri)
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        return uri_str.split("/")[-1]

    @staticmethod
    def _convert_literal(literal: Literal) -> Any:
        """Convert RDF literal to Python value."""
        if literal.datatype:
            datatype = str(literal.datatype)
            if "integer" in datatype or "int" in datatype:
                return int(literal)
            if "float" in datatype or "double" in datatype:
                return float(literal)
            if "boolean" in datatype:
                return bool(literal)
            if "dateTime" in datatype:
                return str(literal)
        return str(literal)


class RDFRelationshipExtractor:
    """Pure functions for pulling relationships out of an RDF graph."""

    @staticmethod
    def extract(
        graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
    ) -> dict[str, list[dict[str, Any]]] | list[dict[str, Any]]:
        """Extract relationships from RDF graph by type with all properties."""
        legacy_flat_result = source_id is None and extraction_job_id is None
        relationships: dict[str, list[dict[str, Any]]] = {
            rel_type: [] for rel_type in RELATIONSHIP_TYPES
        }

        known_predicates = {
            **{VF[rt]: rt for rt in RELATIONSHIP_TYPES},
            **{VF_HTTPS[rt]: rt for rt in RELATIONSHIP_TYPES},
        }

        for statement in graph.subjects(RDF.type, RDF.Statement):
            subject_uri = graph.value(statement, RDF.subject)
            predicate_uri = graph.value(statement, RDF.predicate)
            object_uri = graph.value(statement, RDF.object)

            if not all((subject_uri, predicate_uri, object_uri)):
                continue

            predicate_name = known_predicates.get(predicate_uri)
            if not predicate_name:
                continue

            rel_data: dict[str, Any] = {
                "source_id": RDFRelationshipExtractor._resolve_entity_id(
                    graph, subject_uri
                ),
                "target_id": RDFRelationshipExtractor._resolve_entity_id(
                    graph, object_uri
                ),
                "predicate": predicate_name,
                "confidence": 1.0,
                "source": source_id,
                "extraction_job_id": extraction_job_id,
                "provenance": {},
            }

            for prop, key, coerce in (
                (VF.rawPredicate, "raw_predicate", str),
                (VF.confidence, "confidence", float),
                (VF.impactLevel, "impact_level", str),
                (VF.strength, "strength", float),
                (VF.enablementType, "enablement_type", str),
                (VF.benefitType, "benefit_type", str),
                (VF.driverType, "driver_type", str),
                (VF.contributionWeight, "contribution_weight", float),
                (VF.influenceWeight, "influence_weight", float),
            ):
                value = graph.value(statement, prop)
                if value:
                    rel_data[key] = coerce(value)

            relationships[predicate_name].append(rel_data)

        for subject_uri, predicate_uri, object_uri in graph:
            predicate_name = known_predicates.get(predicate_uri)
            if not predicate_name or not isinstance(object_uri, URIRef):
                continue
            rel_data = {
                "source_id": RDFRelationshipExtractor._resolve_entity_id(
                    graph, subject_uri
                ),
                "target_id": RDFRelationshipExtractor._resolve_entity_id(
                    graph, object_uri
                ),
                "predicate": predicate_name,
                "confidence": 1.0,
                "source": source_id,
                "extraction_job_id": extraction_job_id,
                "provenance": {},
            }
            if rel_data not in relationships[predicate_name]:
                relationships[predicate_name].append(rel_data)

        if legacy_flat_result:
            return [rel for rels in relationships.values() for rel in rels]

        return relationships

    @staticmethod
    def _resolve_entity_id(graph: Graph, uri: URIRef) -> str:
        """Resolve an entity URI to its ID, using explicit VF.id if available."""
        id_literal = graph.value(uri, VF.id)
        if id_literal:
            return str(id_literal)
        return str(uri)
