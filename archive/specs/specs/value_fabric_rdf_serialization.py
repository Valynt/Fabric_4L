"""
Value Fabric SaaS Platform - RDF/OWL Serialization
==================================================

This module defines the serialization of validated entities and relationships
into formal graph structures using RDF and OWL standards.

Serialization Components:
1. RDF Triple Generation: Subject-Predicate-Object triples
2. OWL Constraint Definitions: Logical constraints, inverse properties, transitivity
3. Namespace Management: Prefix declarations and IRI resolution
4. Graph Construction: Building complete knowledge graphs
5. Import/Export: Turtle, RDF/XML, JSON-LD formats
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

# Import from ontology schema module
from value_fabric_ontology_schema import (
    EntityType, RelationshipType, PropertyDefinition,
    OntologySchema, ONTOLOGY_SCHEMA,
    OntologyNamespace, create_entity_uri, create_relationship_uri
)

from value_fabric_extraction_pipeline import (
    ExtractedEntity, ExtractedRelationship, ExtractionResult
)


# =============================================================================
# RDF/OWL DATA STRUCTURES
# =============================================================================

class RDFTermType(Enum):
    """Types of RDF terms."""
    URI = "uri"
    LITERAL = "literal"
    BLANK_NODE = "blank_node"


@dataclass
class RDFTerm:
    """A term in an RDF triple."""
    term_type: RDFTermType
    value: str
    datatype: Optional[str] = None  # For literals
    language: Optional[str] = None  # For language-tagged literals
    
    def to_ntriples(self) -> str:
        """Serialize to N-Triples format."""
        if self.term_type == RDFTermType.URI:
            return f"<{self.value}>"
        elif self.term_type == RDFTermType.BLANK_NODE:
            return f"_:{self.value}"
        else:  # LITERAL
            if self.datatype:
                return f'"{self.escape_literal(self.value)}"^^<{self.datatype}>'
            elif self.language:
                return f'"{self.escape_literal(self.value)}"@{self.language}'
            else:
                return f'"{self.escape_literal(self.value)}"'
    
    def to_turtle(self, namespace_manager: 'NamespaceManager') -> str:
        """Serialize to Turtle format with prefix compression."""
        if self.term_type == RDFTermType.URI:
            return namespace_manager.compress_uri(self.value)
        elif self.term_type == RDFTermType.BLANK_NODE:
            return f"_:{self.value}"
        else:  # LITERAL
            if self.datatype:
                compressed_dt = namespace_manager.compress_uri(self.datatype)
                return f'"{self.escape_literal(self.value)}"^^{compressed_dt}'
            elif self.language:
                return f'"{self.escape_literal(self.value)}"@{self.language}'
            else:
                return f'"{self.escape_literal(self.value)}"'
    
    @staticmethod
    def escape_literal(value: str) -> str:
        """Escape special characters in literal values."""
        escapes = {
            '\\': '\\\\',
            '"': '\\"',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t'
        }
        for old, new in escapes.items():
            value = value.replace(old, new)
        return value


@dataclass
class RDFTriple:
    """A single RDF triple (Subject-Predicate-Object)."""
    subject: RDFTerm
    predicate: RDFTerm
    object: RDFTerm
    graph: Optional[str] = None  # Named graph (optional)
    
    def to_ntriples(self) -> str:
        """Serialize to N-Triples format."""
        return f"{self.subject.to_ntriples()} {self.predicate.to_ntriples()} {self.object.to_ntriples()} ."
    
    def to_turtle(self, namespace_manager: 'NamespaceManager') -> str:
        """Serialize to Turtle format."""
        subj = self.subject.to_turtle(namespace_manager)
        pred = self.predicate.to_turtle(namespace_manager)
        obj = self.object.to_turtle(namespace_manager)
        return f"{subj} {pred} {obj} ."


@dataclass
class OWLConstraint:
    """OWL constraint definition."""
    constraint_type: str  # cardinality, restriction, disjoint, etc.
    target_class: str
    property: Optional[str] = None
    value: Any = None
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None


# =============================================================================
# NAMESPACE MANAGEMENT
# =============================================================================

class NamespaceManager:
    """
    Manages RDF namespace prefixes and IRI resolution.
    Provides prefix compression for readable Turtle output.
    """
    
    DEFAULT_PREFIXES = {
        "rdf": OntologyNamespace.RDF,
        "rdfs": OntologyNamespace.RDFS,
        "owl": OntologyNamespace.OWL,
        "xsd": OntologyNamespace.XSD,
        "skos": OntologyNamespace.SKOS,
        "vf": OntologyNamespace.VF,
        "vf-cap": OntologyNamespace.VF_CAP,
        "vf-use": OntologyNamespace.VF_USE,
        "vf-per": OntologyNamespace.VF_PER,
        "vf-val": OntologyNamespace.VF_VAL,
        "apqc": OntologyNamespace.APQC,
        "bian": OntologyNamespace.BIAN,
        "fibo": OntologyNamespace.FIBO,
    }
    
    def __init__(self, custom_prefixes: Optional[Dict[str, str]] = None):
        self.prefixes = {**self.DEFAULT_PREFIXES}
        if custom_prefixes:
            self.prefixes.update(custom_prefixes)
        
        # Build reverse mapping for compression
        self._build_reverse_map()
    
    def _build_reverse_map(self) -> None:
        """Build reverse mapping for URI compression."""
        self.uri_to_prefix: Dict[str, str] = {}
        for prefix, uri in sorted(self.prefixes.items(), key=lambda x: -len(x[1])):
            self.uri_to_prefix[uri] = prefix
    
    def add_prefix(self, prefix: str, uri: str) -> None:
        """Add a new namespace prefix."""
        self.prefixes[prefix] = uri
        self._build_reverse_map()
    
    def expand_uri(self, prefixed: str) -> str:
        """Expand a prefixed name to full URI."""
        if ':' not in prefixed:
            return prefixed
        
        prefix, local = prefixed.split(':', 1)
        if prefix in self.prefixes:
            return self.prefixes[prefix] + local
        return prefixed
    
    def compress_uri(self, uri: str) -> str:
        """Compress a URI to prefixed form if possible."""
        for prefix_uri, prefix in self.uri_to_prefix.items():
            if uri.startswith(prefix_uri):
                local = uri[len(prefix_uri):]
                return f"{prefix}:{local}"
        return f"<{uri}>"
    
    def get_prefix_declarations(self) -> str:
        """Get Turtle-style prefix declarations."""
        lines = []
        for prefix, uri in sorted(self.prefixes.items()):
            lines.append(f"@prefix {prefix}: <{uri}> .")
        return "\n".join(lines)


# =============================================================================
# RDF TRIPLE GENERATOR
# =============================================================================

class RDFTripleGenerator:
    """
    Generates RDF triples from extracted entities and relationships.
    Produces standard RDF with OWL annotations.
    """
    
    def __init__(
        self,
        schema: OntologySchema,
        namespace_manager: Optional[NamespaceManager] = None
    ):
        self.schema = schema
        self.ns = namespace_manager or NamespaceManager()
    
    def generate_entity_triples(self, entity: ExtractedEntity) -> List[RDFTriple]:
        """
        Generate RDF triples for a single entity.
        
        Args:
            entity: Extracted entity
            
        Returns:
            List of RDF triples
        """
        triples = []
        entity_uri = create_entity_uri(entity.entity_type, entity.entity_id)
        
        # Type declaration
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
            object=RDFTerm(RDFTermType.URI, self.schema.to_owl_class_iri(entity.entity_type))
        ))
        
        # Also declare as OWL NamedIndividual
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
            object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "NamedIndividual")
        ))
        
        # Label (canonical name)
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "label"),
            object=RDFTerm(RDFTermType.LITERAL, entity.canonical_name)
        ))
        
        # SKOS prefLabel
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.SKOS + "prefLabel"),
            object=RDFTerm(RDFTermType.LITERAL, entity.canonical_name)
        ))
        
        # Alternative names (SKOS altLabel)
        for alt_name in entity.alternative_names:
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, entity_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.SKOS + "altLabel"),
                object=RDFTerm(RDFTermType.LITERAL, alt_name)
            ))
        
        # Properties
        class_def = self.schema.get_class_definition(entity.entity_type)
        if class_def:
            for prop_name, prop_value in entity.properties.items():
                if prop_name in class_def.properties:
                    prop_def = class_def.properties[prop_name]
                    triples.extend(self._generate_property_triples(
                        entity_uri, prop_name, prop_value, prop_def
                    ))
        
        # Confidence score as provenance
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "confidenceScore"),
            object=RDFTerm(
                RDFTermType.LITERAL, 
                str(entity.confidence_score),
                OntologyNamespace.XSD + "decimal"
            )
        ))
        
        # Extraction source
        if entity.extraction_source:
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, entity_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "extractedFrom"),
                object=RDFTerm(RDFTermType.URI, 
                              f"{OntologyNamespace.VF}source/{entity.extraction_source}")
            ))
        
        return triples
    
    def _generate_property_triples(
        self,
        entity_uri: str,
        prop_name: str,
        prop_value: Any,
        prop_def: PropertyDefinition
    ) -> List[RDFTriple]:
        """Generate triples for a single property."""
        triples = []
        
        # Convert property name to URI
        property_uri = f"{OntologyNamespace.VF}{prop_def.name}"
        
        # Handle different property types
        if prop_def.property_type == "xsd:string":
            obj_term = RDFTerm(RDFTermType.LITERAL, str(prop_value.value))
        elif prop_def.property_type == "xsd:integer":
            obj_term = RDFTerm(
                RDFTermType.LITERAL, 
                str(int(prop_value.value)),
                OntologyNamespace.XSD + "integer"
            )
        elif prop_def.property_type == "xsd:decimal":
            obj_term = RDFTerm(
                RDFTermType.LITERAL,
                str(float(prop_value.value)),
                OntologyNamespace.XSD + "decimal"
            )
        elif prop_def.property_type == "xsd:boolean":
            obj_term = RDFTerm(
                RDFTermType.LITERAL,
                str(bool(prop_value.value)).lower(),
                OntologyNamespace.XSD + "boolean"
            )
        elif prop_def.property_type == "xsd:dateTime":
            obj_term = RDFTerm(
                RDFTermType.LITERAL,
                str(prop_value.value),
                OntologyNamespace.XSD + "dateTime"
            )
        elif prop_def.property_type == "xsd:anyURI":
            obj_term = RDFTerm(RDFTermType.URI, str(prop_value.value))
        else:
            # Default to string
            obj_term = RDFTerm(RDFTermType.LITERAL, str(prop_value.value))
        
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, entity_uri),
            predicate=RDFTerm(RDFTermType.URI, property_uri),
            object=obj_term
        ))
        
        # Add confidence annotation if available
        if hasattr(prop_value, 'confidence') and prop_value.confidence < 1.0:
            # Use reification for confidence annotation
            statement_id = f"stmt-{hash(entity_uri + prop_name) % 1000000}"
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, f"{OntologyNamespace.VF}{statement_id}"),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
                object=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "Statement")
            ))
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, f"{OntologyNamespace.VF}{statement_id}"),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "subject"),
                object=RDFTerm(RDFTermType.URI, entity_uri)
            ))
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, f"{OntologyNamespace.VF}{statement_id}"),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "predicate"),
                object=RDFTerm(RDFTermType.URI, property_uri)
            ))
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, f"{OntologyNamespace.VF}{statement_id}"),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "object"),
                object=obj_term
            ))
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, f"{OntologyNamespace.VF}{statement_id}"),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "confidence"),
                object=RDFTerm(
                    RDFTermType.LITERAL,
                    str(prop_value.confidence),
                    OntologyNamespace.XSD + "decimal"
                )
            ))
        
        return triples
    
    def generate_relationship_triples(
        self, 
        relationship: ExtractedRelationship
    ) -> List[RDFTriple]:
        """
        Generate RDF triples for a relationship.
        
        Args:
            relationship: Extracted relationship
            
        Returns:
            List of RDF triples
        """
        triples = []
        
        source_uri = create_entity_uri(
            EntityType.CAPABILITY,  # Placeholder - would look up actual type
            relationship.source_entity_id
        )
        target_uri = create_entity_uri(
            EntityType.CAPABILITY,  # Placeholder
            relationship.target_entity_id
        )
        
        property_uri = self.schema.to_owl_property_iri(relationship.relationship_type)
        
        # Main relationship triple
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, source_uri),
            predicate=RDFTerm(RDFTermType.URI, property_uri),
            object=RDFTerm(RDFTermType.URI, target_uri)
        ))
        
        # Add inverse property if defined
        constraint = self.schema.get_relationship_constraint(relationship.relationship_type)
        if constraint and constraint.inverse_property:
            inverse_uri = self.schema.to_owl_property_iri(constraint.inverse_property)
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, target_uri),
                predicate=RDFTerm(RDFTermType.URI, inverse_uri),
                object=RDFTerm(RDFTermType.URI, source_uri)
            ))
        
        # Confidence annotation
        rel_uri = create_relationship_uri(source_uri, relationship.relationship_type, target_uri)
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, rel_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
            object=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "Relationship")
        ))
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, rel_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "confidenceScore"),
            object=RDFTerm(
                RDFTermType.LITERAL,
                str(relationship.confidence_score),
                OntologyNamespace.XSD + "decimal"
            )
        ))
        
        # Evidence text
        if relationship.evidence_text:
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, rel_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "evidenceText"),
                object=RDFTerm(RDFTermType.LITERAL, relationship.evidence_text)
            ))
        
        return triples
    
    def generate_extraction_result_triples(
        self,
        result: ExtractionResult
    ) -> List[RDFTriple]:
        """Generate triples for a complete extraction result."""
        triples = []
        
        # Entity triples
        for entity in result.entities:
            triples.extend(self.generate_entity_triples(entity))
        
        # Relationship triples
        for relationship in result.relationships:
            triples.extend(self.generate_relationship_triples(relationship))
        
        return triples


# =============================================================================
# OWL CONSTRAINT GENERATOR
# =============================================================================

class OWLConstraintGenerator:
    """
    Generates OWL constraints for the Value Fabric ontology.
    Defines logical properties like inverse, transitive, cardinality.
    """
    
    def __init__(
        self,
        schema: OntologySchema,
        namespace_manager: Optional[NamespaceManager] = None
    ):
        self.schema = schema
        self.ns = namespace_manager or NamespaceManager()
    
    def generate_ontology_header(self) -> List[RDFTriple]:
        """Generate OWL ontology header triples."""
        triples = []
        ontology_uri = OntologyNamespace.VF
        
        # Ontology declaration
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, ontology_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
            object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "Ontology")
        ))
        
        # Ontology metadata
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, ontology_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "label"),
            object=RDFTerm(RDFTermType.LITERAL, "Value Fabric Ontology")
        ))
        
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, ontology_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "comment"),
            object=RDFTerm(RDFTermType.LITERAL, 
                          "Ontology for the Value Fabric SaaS platform")
        ))
        
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, ontology_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "versionInfo"),
            object=RDFTerm(RDFTermType.LITERAL, "1.0.0")
        ))
        
        # Import reference models
        triples.append(RDFTriple(
            subject=RDFTerm(RDFTermType.URI, ontology_uri),
            predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "imports"),
            object=RDFTerm(RDFTermType.URI, OntologyNamespace.SKOS)
        ))
        
        return triples
    
    def generate_class_definitions(self) -> List[RDFTriple]:
        """Generate OWL class definitions for all entity types."""
        triples = []
        
        for entity_type in self.schema.get_all_entity_types():
            class_uri = self.schema.to_owl_class_iri(entity_type)
            class_def = self.schema.get_class_definition(entity_type)
            
            if not class_def:
                continue
            
            # Class declaration
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, class_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
                object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "Class")
            ))
            
            # Label
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, class_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "label"),
                object=RDFTerm(RDFTermType.LITERAL, entity_type.value)
            ))
            
            # Comment/Description
            if class_def.description:
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, class_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "comment"),
                    object=RDFTerm(RDFTermType.LITERAL, class_def.description)
                ))
            
            # Parent classes (subclassOf)
            for parent in class_def.parent_classes:
                parent_uri = self.schema.to_owl_class_iri(parent)
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, class_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "subClassOf"),
                    object=RDFTerm(RDFTermType.URI, parent_uri)
                ))
            
            # If no parent, subclass of vf:Entity
            if not class_def.parent_classes:
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, class_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "subClassOf"),
                    object=RDFTerm(RDFTermType.URI, OntologyNamespace.VF + "Entity")
                ))
        
        return triples
    
    def generate_property_definitions(self) -> List[RDFTriple]:
        """Generate OWL object and data property definitions."""
        triples = []
        
        # Object properties (relationships)
        for rel_type in RelationshipType:
            constraint = self.schema.get_relationship_constraint(rel_type)
            if not constraint:
                continue
            
            prop_uri = self.schema.to_owl_property_iri(rel_type)
            
            # Property declaration
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, prop_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
                object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "ObjectProperty")
            ))
            
            # Label
            triples.append(RDFTriple(
                subject=RDFTerm(RDFTermType.URI, prop_uri),
                predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "label"),
                object=RDFTerm(RDFTermType.LITERAL, rel_type.value)
            ))
            
            # Domain
            for domain_class in constraint.domain:
                domain_uri = self.schema.to_owl_class_iri(domain_class)
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, prop_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "domain"),
                    object=RDFTerm(RDFTermType.URI, domain_uri)
                ))
            
            # Range
            for range_class in constraint.range:
                range_uri = self.schema.to_owl_class_iri(range_class)
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, prop_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDFS + "range"),
                    object=RDFTerm(RDFTermType.URI, range_uri)
                ))
            
            # Inverse property
            if constraint.inverse_property:
                inverse_uri = self.schema.to_owl_property_iri(constraint.inverse_property)
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, prop_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "inverseOf"),
                    object=RDFTerm(RDFTermType.URI, inverse_uri)
                ))
            
            # Transitive
            if constraint.transitive:
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, prop_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
                    object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "TransitiveProperty")
                ))
            
            # Symmetric
            if constraint.symmetric:
                triples.append(RDFTriple(
                    subject=RDFTerm(RDFTermType.URI, prop_uri),
                    predicate=RDFTerm(RDFTermType.URI, OntologyNamespace.RDF + "type"),
                    object=RDFTerm(RDFTermType.URI, OntologyNamespace.OWL + "SymmetricProperty")
                ))
        
        return triples
    
    def generate_cardinality_restrictions(self) -> List[RDFTriple]:
        """Generate OWL cardinality restrictions."""
        triples = []
        
        # This would generate restrictions like:
        # vf:UseCase rdfs:subClassOf [
        #   a owl:Restriction;
        #   owl:onProperty vf:involvesPersona;
        #   owl:minCardinality 1
        # ]
        
        # For now, placeholder - would iterate through constraints
        # and generate appropriate restrictions
        
        return triples
    
    def generate_complete_ontology(self) -> List[RDFTriple]:
        """Generate complete OWL ontology definition."""
        triples = []
        
        triples.extend(self.generate_ontology_header())
        triples.extend(self.generate_class_definitions())
        triples.extend(self.generate_property_definitions())
        triples.extend(self.generate_cardinality_restrictions())
        
        return triples


# =============================================================================
# SERIALIZATION FORMATS
# =============================================================================

class TurtleSerializer:
    """Serializes RDF triples to Turtle format."""
    
    def __init__(self, namespace_manager: NamespaceManager):
        self.ns = namespace_manager
    
    def serialize(self, triples: List[RDFTriple]) -> str:
        """Serialize triples to Turtle format."""
        lines = []
        
        # Prefix declarations
        lines.append(self.ns.get_prefix_declarations())
        lines.append("")
        
        # Group triples by subject for readability
        grouped = self._group_by_subject(triples)
        
        for subject, predicate_objects in grouped.items():
            lines.append(f"{subject}")
            pred_obj_lines = []
            for pred, obj in predicate_objects:
                pred_obj_lines.append(f"  {pred} {obj}")
            lines.append(" ;\n".join(pred_obj_lines) + " .")
            lines.append("")
        
        return "\n".join(lines)
    
    def _group_by_subject(self, triples: List[RDFTriple]) -> Dict[str, List[Tuple[str, str]]]:
        """Group triples by subject for Turtle shorthand syntax."""
        grouped: Dict[str, List[Tuple[str, str]]] = {}
        
        for triple in triples:
            subj = triple.subject.to_turtle(self.ns)
            pred = triple.predicate.to_turtle(self.ns)
            obj = triple.object.to_turtle(self.ns)
            
            if subj not in grouped:
                grouped[subj] = []
            grouped[subj].append((pred, obj))
        
        return grouped


class JSONLDSerializer:
    """Serializes RDF triples to JSON-LD format."""
    
    def __init__(self, namespace_manager: NamespaceManager):
        self.ns = namespace_manager
    
    def serialize(self, triples: List[RDFTriple], context: Optional[Dict] = None) -> str:
        """Serialize triples to JSON-LD format."""
        # Build JSON-LD context
        jsonld_context = context or self._build_context()
        
        # Group triples by subject
        subjects: Dict[str, Dict] = {}
        
        for triple in triples:
            subj_uri = triple.subject.value
            pred_uri = triple.predicate.value
            
            if subj_uri not in subjects:
                subjects[subj_uri] = {"@id": subj_uri}
            
            # Get compacted predicate
            pred_compact = self.ns.compress_uri(pred_uri).strip("<>")
            
            # Handle object
            if triple.object.term_type == RDFTermType.URI:
                obj_value = {"@id": triple.object.value}
            else:
                obj_value = {"@value": triple.object.value}
                if triple.object.datatype:
                    obj_value["@type"] = self.ns.compress_uri(triple.object.datatype).strip("<>")
                if triple.object.language:
                    obj_value["@language"] = triple.object.language
            
            # Add to subject
            if pred_compact not in subjects[subj_uri]:
                subjects[subj_uri][pred_compact] = []
            subjects[subj_uri][pred_compact].append(obj_value)
        
        # Convert single-value lists back to single values
        for subj_data in subjects.values():
            for pred, values in subj_data.items():
                if pred != "@id" and len(values) == 1:
                    subj_data[pred] = values[0]
        
        # Build final document
        doc = {
            "@context": jsonld_context,
            "@graph": list(subjects.values())
        }
        
        return json.dumps(doc, indent=2)
    
    def _build_context(self) -> Dict[str, Any]:
        """Build JSON-LD context from namespace prefixes."""
        context = {}
        
        for prefix, uri in self.ns.prefixes.items():
            context[prefix] = uri
        
        # Add type coercion for common properties
        context["label"] = {"@id": "rdfs:label"}
        context["comment"] = {"@id": "rdfs:comment"}
        context["subClassOf"] = {"@id": "rdfs:subClassOf", "@type": "@id"}
        context["domain"] = {"@id": "rdfs:domain", "@type": "@id"}
        context["range"] = {"@id": "rdfs:range", "@type": "@id"}
        
        return context


class NTriplesSerializer:
    """Serializes RDF triples to N-Triples format."""
    
    def serialize(self, triples: List[RDFTriple]) -> str:
        """Serialize triples to N-Triples format."""
        return "\n".join(triple.to_ntriples() for triple in triples)


# =============================================================================
# KNOWLEDGE GRAPH BUILDER
# =============================================================================

class KnowledgeGraphBuilder:
    """
    Builds complete knowledge graphs from extraction results.
    Combines schema definitions with instance data.
    """
    
    def __init__(
        self,
        schema: OntologySchema,
        namespace_manager: Optional[NamespaceManager] = None
    ):
        self.schema = schema
        self.ns = namespace_manager or NamespaceManager()
        self.triple_generator = RDFTripleGenerator(schema, self.ns)
        self.constraint_generator = OWLConstraintGenerator(schema, self.ns)
    
    def build_complete_graph(
        self,
        extraction_results: List[ExtractionResult],
        include_schema: bool = True
    ) -> List[RDFTriple]:
        """
        Build complete knowledge graph from extraction results.
        
        Args:
            extraction_results: List of extraction results
            include_schema: Whether to include OWL schema definitions
            
        Returns:
            Complete list of RDF triples
        """
        triples = []
        
        # Add schema definitions
        if include_schema:
            triples.extend(self.constraint_generator.generate_complete_ontology())
        
        # Add instance data
        for result in extraction_results:
            triples.extend(
                self.triple_generator.generate_extraction_result_triples(result)
            )
        
        return triples
    
    def export_to_format(
        self,
        triples: List[RDFTriple],
        format_type: str
    ) -> str:
        """
        Export triples to specified format.
        
        Args:
            triples: RDF triples to export
            format_type: One of 'turtle', 'jsonld', 'ntriples'
            
        Returns:
            Serialized string in specified format
        """
        if format_type == "turtle":
            serializer = TurtleSerializer(self.ns)
        elif format_type == "jsonld":
            serializer = JSONLDSerializer(self.ns)
        elif format_type == "ntriples":
            serializer = NTriplesSerializer()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return serializer.serialize(triples)
    
    def export_named_graphs(
        self,
        extraction_results: List[ExtractionResult],
        graph_organization: str = "by_source"
    ) -> Dict[str, List[RDFTriple]]:
        """
        Export triples organized into named graphs.
        
        Args:
            extraction_results: List of extraction results
            graph_organization: How to organize graphs ('by_source', 'by_type', 'single')
            
        Returns:
            Dictionary mapping graph names to triple lists
        """
        graphs: Dict[str, List[RDFTriple]] = {}
        
        if graph_organization == "single":
            all_triples = []
            for result in extraction_results:
                all_triples.extend(
                    self.triple_generator.generate_extraction_result_triples(result)
                )
            graphs["default"] = all_triples
        
        elif graph_organization == "by_source":
            for result in extraction_results:
                graph_name = f"{OntologyNamespace.VF}graph/source/{result.source_id}"
                triples = self.triple_generator.generate_extraction_result_triples(result)
                graphs[graph_name] = triples
        
        elif graph_organization == "by_type":
            for result in extraction_results:
                for entity in result.entities:
                    graph_name = f"{OntologyNamespace.VF}graph/type/{entity.entity_type.value}"
                    if graph_name not in graphs:
                        graphs[graph_name] = []
                    graphs[graph_name].extend(
                        self.triple_generator.generate_entity_triples(entity)
                    )
        
        return graphs


# =============================================================================
# SPARQL QUERY GENERATOR
# =============================================================================

class SPARQLQueryGenerator:
    """
    Generates SPARQL queries for common operations on the knowledge graph.
    """
    
    def __init__(self, namespace_manager: NamespaceManager):
        self.ns = namespace_manager
    
    def generate_prefixes(self) -> str:
        """Generate SPARQL PREFIX declarations."""
        lines = []
        for prefix, uri in sorted(self.ns.prefixes.items()):
            lines.append(f"PREFIX {prefix}: <{uri}>")
        return "\n".join(lines)
    
    def query_entity_by_type(self, entity_type: EntityType, limit: int = 100) -> str:
        """Generate query to find entities of a specific type."""
        class_uri = self.ns.compress_uri(
            ONTOLOGY_SCHEMA.to_owl_class_iri(entity_type)
        ).strip("<>")
        
        return f"""{self.generate_prefixes()}

SELECT ?entity ?name ?description
WHERE {{
  ?entity a {class_uri} ;
          rdfs:label ?name .
  OPTIONAL {{ ?entity vf:description ?description }}
}}
LIMIT {limit}
"""
    
    def query_relationships_for_entity(self, entity_uri: str) -> str:
        """Generate query to find all relationships for an entity."""
        return f"""{self.generate_prefixes()}

SELECT ?predicate ?target ?targetName ?confidence
WHERE {{
  <{entity_uri}> ?predicate ?target .
  ?target rdfs:label ?targetName .
  OPTIONAL {{ 
    ?rel vf:source <{entity_uri}> ;
         vf:target ?target ;
         vf:confidenceScore ?confidence 
  }}
}}
"""
    
    def query_capability_value_chain(self, capability_uri: str) -> str:
        """Generate query to trace capability to value delivery."""
        return f"""{self.generate_prefixes()}

SELECT ?useCase ?persona ?valueDriver ?metric
WHERE {{
  <{capability_uri}> vf:enables ?useCase .
  ?useCase vf:involves ?persona ;
           vf:delivers ?valueDriver .
  OPTIONAL {{ ?valueDriver vf:measuredBy ?metric }}
}}
"""
    
    def query_reference_model_coverage(self, model_type: str) -> str:
        """Generate query to analyze reference model coverage."""
        rel_property = f"vf:mapsTo{model_type.upper()}"
        
        return f"""{self.generate_prefixes()}

SELECT ?entityType (COUNT(?entity) AS ?mappedCount)
WHERE {{
  ?entity {rel_property} ?referenceConcept .
  ?entity a ?entityType .
}}
GROUP BY ?entityType
"""
