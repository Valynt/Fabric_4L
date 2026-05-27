"""
Value Fabric SaaS Platform - Ontology Schema Definitions
=========================================================

This module defines the formal ontology for the Value Fabric platform,
including core classes, properties, relationships, and inheritance hierarchies.

The ontology is designed to support:
- Schema-guided entity extraction from unstructured text
- Semantic alignment and coreference resolution
- Integration with industry reference models (APQC, BIAN, FIBO)
- RDF/OWL serialization for knowledge graph construction
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field


# =============================================================================
# ONTOLOGY NAMESPACES
# =============================================================================

class OntologyNamespace:
    """Namespace management for RDF/OWL serialization."""
    
    VF = "http://valuefabric.io/ontology/"  # Value Fabric core namespace
    VF_CAP = "http://valuefabric.io/ontology/capability/"
    VF_USE = "http://valuefabric.io/ontology/usecase/"
    VF_PER = "http://valuefabric.io/ontology/persona/"
    VF_VAL = "http://valuefabric.io/ontology/value/"
    VF_PROD = "http://valuefabric.io/ontology/product/"
    VF_ORG = "http://valuefabric.io/ontology/organization/"
    
    # Industry reference model namespaces
    APQC = "http://www.apqc.org/pcf/"
    BIAN = "http://bian.org/servicelandscape/"
    FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
    
    # Standard semantic web namespaces
    RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    RDFS = "http://www.w3.org/2000/01/rdf-schema#"
    OWL = "http://www.w3.org/2002/07/owl#"
    XSD = "http://www.w3.org/2001/XMLSchema#"
    SKOS = "http://www.w3.org/2004/02/skos/core#"


# =============================================================================
# CORE ENTITY TYPES (Ontology Classes)
# =============================================================================

class EntityType(Enum):
    """Core entity types in the Value Fabric ontology."""
    
    # Primary Business Concepts
    CAPABILITY = "Capability"
    USE_CASE = "UseCase"
    PERSONA = "Persona"
    VALUE_DRIVER = "ValueDriver"
    VALUE_METRIC = "ValueMetric"
    
    # Product & Solution Domain
    PRODUCT = "Product"
    FEATURE = "Feature"
    SERVICE = "Service"
    SOLUTION = "Solution"
    TECHNOLOGY = "Technology"
    
    # Organizational Context
    ORGANIZATION = "Organization"
    BUSINESS_UNIT = "BusinessUnit"
    PROCESS = "Process"
    ACTIVITY = "Activity"
    
    # Industry Reference Model Mappings
    APQC_PROCESS = "APQCProcess"
    BIAN_SERVICE_DOMAIN = "BIANServiceDomain"
    FIBO_ENTITY = "FIBOEntity"
    
    # Supporting Concepts
    INDUSTRY = "Industry"
    MARKET_SEGMENT = "MarketSegment"
    GEOGRAPHY = "Geography"
    REGULATION = "Regulation"
    
    # Metadata & Provenance
    DATA_SOURCE = "DataSource"
    EXTRACTION_EVENT = "ExtractionEvent"
    CONFIDENCE_SCORE = "ConfidenceScore"


# =============================================================================
# RELATIONSHIP TYPES (Object Properties)
# =============================================================================

class RelationshipType(Enum):
    """Relationship types with cardinality and domain/range constraints."""
    
    # Capability Relationships
    CAPABILITY_ENABLES_USECASE = "enables"
    CAPABILITY_REQUIRES_CAPABILITY = "requires"
    CAPABILITY_SUBTYPE_OF = "subTypeOf"
    CAPABILITY_IMPLEMENTED_BY = "implementedBy"
    CAPABILITY_MEASURED_BY = "measuredBy"
    
    # Use Case Relationships
    USE_CASE_DELIVERS_VALUE = "delivers"
    USE_CASE_INVOLVES_PERSONA = "involves"
    USE_CASE_REQUIRES_FEATURE = "requiresFeature"
    USE_CASE_PART_OF_PROCESS = "partOf"
    
    # Value Relationships
    VALUE_DRIVER_IMPACTS_METRIC = "impacts"
    VALUE_DRIVER_DRIVEN_BY = "drivenBy"
    VALUE_METRIC_MEASURES = "measures"
    
    # Product Relationships
    FEATURE_IMPLEMENTS_CAPABILITY = "implements"
    PRODUCT_HAS_FEATURE = "hasFeature"
    PRODUCT_ADDRESSES_USECASE = "addresses"
    SERVICE_PROVIDES_CAPABILITY = "provides"
    
    # Persona Relationships
    PERSONA_PERFORMS_USECASE = "performs"
    PERSONA_BENEFITS_FROM = "benefitsFrom"
    PERSONA_BELONGS_TO = "belongsTo"
    
    # Organizational Relationships
    PROCESS_CONTAINS_ACTIVITY = "contains"
    ORGANIZATION_OPERATES_IN = "operatesIn"
    BUSINESS_UNIT_OWNS_PROCESS = "owns"
    
    # Reference Model Mappings
    MAPS_TO_APQC = "mapsToAPQC"
    MAPS_TO_BIAN = "mapsToBIAN"
    MAPS_TO_FIBO = "mapsToFIBO"
    SEMANTICALLY_EQUIVALENT = "semanticallyEquivalent"
    
    # Provenance Relationships
    EXTRACTED_FROM = "extractedFrom"
    VALIDATED_BY = "validatedBy"
    SUPERSEDES = "supersedes"


@dataclass
class RelationshipConstraint:
    """Defines constraints for a relationship type."""
    relationship_type: RelationshipType
    domain: List[EntityType]
    range: List[EntityType]
    cardinality_min: int = 0
    cardinality_max: Optional[int] = None  # None means unlimited
    inverse_property: Optional[RelationshipType] = None
    transitive: bool = False
    symmetric: bool = False


# =============================================================================
# RELATIONSHIP CONSTRAINTS REGISTRY
# =============================================================================

RELATIONSHIP_CONSTRAINTS: Dict[RelationshipType, RelationshipConstraint] = {
    # Capability -> Use Case (enables)
    RelationshipType.CAPABILITY_ENABLES_USECASE: RelationshipConstraint(
        relationship_type=RelationshipType.CAPABILITY_ENABLES_USECASE,
        domain=[EntityType.CAPABILITY],
        range=[EntityType.USE_CASE],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=RelationshipType.USE_CASE_REQUIRES_FEATURE,
        transitive=False,
        symmetric=False
    ),
    
    # Capability hierarchy
    RelationshipType.CAPABILITY_SUBTYPE_OF: RelationshipConstraint(
        relationship_type=RelationshipType.CAPABILITY_SUBTYPE_OF,
        domain=[EntityType.CAPABILITY],
        range=[EntityType.CAPABILITY],
        cardinality_min=0,
        cardinality_max=1,
        inverse_property=None,
        transitive=True,
        symmetric=False
    ),
    
    # Capability dependencies
    RelationshipType.CAPABILITY_REQUIRES_CAPABILITY: RelationshipConstraint(
        relationship_type=RelationshipType.CAPABILITY_REQUIRES_CAPABILITY,
        domain=[EntityType.CAPABILITY],
        range=[EntityType.CAPABILITY],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=None,
        transitive=False,
        symmetric=False
    ),
    
    # Use Case -> Value Driver
    RelationshipType.USE_CASE_DELIVERS_VALUE: RelationshipConstraint(
        relationship_type=RelationshipType.USE_CASE_DELIVERS_VALUE,
        domain=[EntityType.USE_CASE],
        range=[EntityType.VALUE_DRIVER],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=RelationshipType.VALUE_DRIVER_DRIVEN_BY,
        transitive=False,
        symmetric=False
    ),
    
    # Use Case -> Persona
    RelationshipType.USE_CASE_INVOLVES_PERSONA: RelationshipConstraint(
        relationship_type=RelationshipType.USE_CASE_INVOLVES_PERSONA,
        domain=[EntityType.USE_CASE],
        range=[EntityType.PERSONA],
        cardinality_min=1,
        cardinality_max=None,
        inverse_property=RelationshipType.PERSONA_PERFORMS_USECASE,
        transitive=False,
        symmetric=False
    ),
    
    # Feature -> Capability
    RelationshipType.FEATURE_IMPLEMENTS_CAPABILITY: RelationshipConstraint(
        relationship_type=RelationshipType.FEATURE_IMPLEMENTS_CAPABILITY,
        domain=[EntityType.FEATURE],
        range=[EntityType.CAPABILITY],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=RelationshipType.CAPABILITY_IMPLEMENTED_BY,
        transitive=False,
        symmetric=False
    ),
    
    # Reference model mappings
    RelationshipType.MAPS_TO_APQC: RelationshipConstraint(
        relationship_type=RelationshipType.MAPS_TO_APQC,
        domain=[EntityType.PROCESS, EntityType.ACTIVITY, EntityType.CAPABILITY],
        range=[EntityType.APQC_PROCESS],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=None,
        transitive=False,
        symmetric=False
    ),
    
    RelationshipType.MAPS_TO_BIAN: RelationshipConstraint(
        relationship_type=RelationshipType.MAPS_TO_BIAN,
        domain=[EntityType.CAPABILITY, EntityType.SERVICE],
        range=[EntityType.BIAN_SERVICE_DOMAIN],
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=None,
        transitive=False,
        symmetric=False
    ),
    
    # Semantic equivalence for coreference resolution
    RelationshipType.SEMANTICALLY_EQUIVALENT: RelationshipConstraint(
        relationship_type=RelationshipType.SEMANTICALLY_EQUIVALENT,
        domain=list(EntityType),  # Any entity type
        range=list(EntityType),   # Can match any entity type
        cardinality_min=0,
        cardinality_max=None,
        inverse_property=RelationshipType.SEMANTICALLY_EQUIVALENT,
        transitive=True,
        symmetric=True
    ),
}


# =============================================================================
# CLASS HIERARCHY DEFINITIONS
# =============================================================================

@dataclass
class ClassDefinition:
    """Complete definition of an ontology class."""
    entity_type: EntityType
    parent_classes: List[EntityType] = field(default_factory=list)
    description: str = ""
    properties: Dict[str, 'PropertyDefinition'] = field(default_factory=dict)
    allowed_relationships: List[RelationshipType] = field(default_factory=list)
    abstract: bool = False


@dataclass
class PropertyDefinition:
    """Definition of a class property (data property)."""
    name: str
    property_type: str  # XSD datatype
    cardinality_min: int = 0
    cardinality_max: Optional[int] = 1
    description: str = ""
    examples: List[str] = field(default_factory=list)


# =============================================================================
# CORE CLASS DEFINITIONS
# =============================================================================

CLASS_DEFINITIONS: Dict[EntityType, ClassDefinition] = {
    
    # =========================================================================
    # CAPABILITY CLASS
    # =========================================================================
    EntityType.CAPABILITY: ClassDefinition(
        entity_type=EntityType.CAPABILITY,
        parent_classes=[],
        description="A business capability represents what a business does, "
                    "independent of how it does it or who performs it.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Canonical name of the capability",
                examples=["Inventory Management", "Customer Analytics"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Detailed description of what the capability entails"
            ),
            "capability_level": PropertyDefinition(
                name="capabilityLevel",
                property_type="xsd:integer",
                cardinality_min=0,
                cardinality_max=1,
                description="Hierarchy level (1=Strategic, 2=Core, 3=Operational)",
                examples=["1", "2", "3"]
            ),
            "maturity_level": PropertyDefinition(
                name="maturityLevel",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Capability maturity assessment",
                examples=["Basic", "Emerging", "Advanced", "Leading"]
            ),
            "keywords": PropertyDefinition(
                name="keywords",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=None,
                description="Searchable keywords for discovery"
            ),
            "source_mentions": PropertyDefinition(
                name="sourceMentions",
                property_type="xsd:integer",
                cardinality_min=0,
                cardinality_max=1,
                description="Count of source documents mentioning this capability"
            ),
        },
        allowed_relationships=[
            RelationshipType.CAPABILITY_ENABLES_USECASE,
            RelationshipType.CAPABILITY_REQUIRES_CAPABILITY,
            RelationshipType.CAPABILITY_SUBTYPE_OF,
            RelationshipType.CAPABILITY_IMPLEMENTED_BY,
            RelationshipType.CAPABILITY_MEASURED_BY,
            RelationshipType.MAPS_TO_APQC,
            RelationshipType.MAPS_TO_BIAN,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # USE CASE CLASS
    # =========================================================================
    EntityType.USE_CASE: ClassDefinition(
        entity_type=EntityType.USE_CASE,
        parent_classes=[],
        description="A use case describes how a user (persona) interacts with "
                    "a system to achieve a specific goal, enabled by capabilities.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Canonical name of the use case",
                examples=["Real-time Inventory Tracking", "Automated Reorder"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Detailed scenario description"
            ),
            "trigger": PropertyDefinition(
                name="trigger",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Event that initiates the use case"
            ),
            "preconditions": PropertyDefinition(
                name="preconditions",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=None,
                description="Conditions that must be true before execution"
            ),
            "postconditions": PropertyDefinition(
                name="postconditions",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=None,
                description="Expected outcomes after execution"
            ),
            "frequency": PropertyDefinition(
                name="frequency",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Typical execution frequency",
                examples=["Real-time", "Daily", "Weekly", "On-demand"]
            ),
            "business_criticality": PropertyDefinition(
                name="businessCriticality",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Importance to business operations",
                examples=["Critical", "High", "Medium", "Low"]
            ),
        },
        allowed_relationships=[
            RelationshipType.USE_CASE_DELIVERS_VALUE,
            RelationshipType.USE_CASE_INVOLVES_PERSONA,
            RelationshipType.USE_CASE_REQUIRES_FEATURE,
            RelationshipType.USE_CASE_PART_OF_PROCESS,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # PERSONA CLASS
    # =========================================================================
    EntityType.PERSONA: ClassDefinition(
        entity_type=EntityType.PERSONA,
        parent_classes=[],
        description="A persona represents a user archetype with specific "
                    "goals, behaviors, and interaction patterns.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Persona identifier",
                examples=["Supply Chain Manager", "CFO", "Data Analyst"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Persona characteristics and context"
            ),
            "role_type": PropertyDefinition(
                name="roleType",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Functional role category",
                examples=["Executive", "Manager", "Analyst", "Operator"]
            ),
            "department": PropertyDefinition(
                name="department",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Organizational department",
                examples=["Finance", "Operations", "IT", "Sales"]
            ),
            "goals": PropertyDefinition(
                name="goals",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=None,
                description="Primary objectives this persona seeks to achieve"
            ),
            "pain_points": PropertyDefinition(
                name="painPoints",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=None,
                description="Challenges and frustrations"
            ),
            "technical_proficiency": PropertyDefinition(
                name="technicalProficiency",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Level of technical expertise",
                examples=["High", "Medium", "Low"]
            ),
        },
        allowed_relationships=[
            RelationshipType.PERSONA_PERFORMS_USECASE,
            RelationshipType.PERSONA_BENEFITS_FROM,
            RelationshipType.PERSONA_BELONGS_TO,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # VALUE DRIVER CLASS
    # =========================================================================
    EntityType.VALUE_DRIVER: ClassDefinition(
        entity_type=EntityType.VALUE_DRIVER,
        parent_classes=[],
        description="A value driver represents a business outcome or benefit "
                    "that motivates investment in capabilities and solutions.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Value driver name",
                examples=["Cost Reduction", "Revenue Growth", "Risk Mitigation"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Detailed explanation of the value"
            ),
            "value_category": PropertyDefinition(
                name="valueCategory",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Classification of value type",
                examples=["Financial", "Operational", "Strategic", "Compliance"]
            ),
            "time_to_value": PropertyDefinition(
                name="timeToValue",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Expected timeline for value realization",
                examples=["Immediate", "3-6 months", "1-2 years"]
            ),
            "quantifiable": PropertyDefinition(
                name="quantifiable",
                property_type="xsd:boolean",
                cardinality_min=0,
                cardinality_max=1,
                description="Whether value can be quantitatively measured"
            ),
        },
        allowed_relationships=[
            RelationshipType.VALUE_DRIVER_IMPACTS_METRIC,
            RelationshipType.VALUE_DRIVER_DRIVEN_BY,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # VALUE METRIC CLASS
    # =========================================================================
    EntityType.VALUE_METRIC: ClassDefinition(
        entity_type=EntityType.VALUE_METRIC,
        parent_classes=[],
        description="A measurable indicator used to quantify value realization.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Metric name",
                examples=["Inventory Turnover", "Cost per Transaction"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="How the metric is calculated and interpreted"
            ),
            "unit_of_measure": PropertyDefinition(
                name="unitOfMeasure",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Unit for measurement",
                examples=["Percentage", "Dollars", "Hours", "Count"]
            ),
            "calculation_formula": PropertyDefinition(
                name="calculationFormula",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Mathematical formula for calculation"
            ),
            "benchmark_low": PropertyDefinition(
                name="benchmarkLow",
                property_type="xsd:decimal",
                cardinality_min=0,
                cardinality_max=1,
                description="Low performance benchmark"
            ),
            "benchmark_high": PropertyDefinition(
                name="benchmarkHigh",
                property_type="xsd:decimal",
                cardinality_min=0,
                cardinality_max=1,
                description="High performance benchmark"
            ),
        },
        allowed_relationships=[
            RelationshipType.VALUE_METRIC_MEASURES,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # PRODUCT CLASS
    # =========================================================================
    EntityType.PRODUCT: ClassDefinition(
        entity_type=EntityType.PRODUCT,
        parent_classes=[],
        description="A commercial offering that delivers capabilities through "
                    "features and services.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Product name"
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Product description"
            ),
            "product_type": PropertyDefinition(
                name="productType",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Classification of product",
                examples=["Software", "Service", "Platform", "Solution"]
            ),
            "vendor": PropertyDefinition(
                name="vendor",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Product vendor or provider"
            ),
            "version": PropertyDefinition(
                name="version",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Product version"
            ),
            "deployment_model": PropertyDefinition(
                name="deploymentModel",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Deployment approach",
                examples=["Cloud", "On-premise", "Hybrid", "SaaS"]
            ),
        },
        allowed_relationships=[
            RelationshipType.PRODUCT_HAS_FEATURE,
            RelationshipType.PRODUCT_ADDRESSES_USECASE,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # FEATURE CLASS
    # =========================================================================
    EntityType.FEATURE: ClassDefinition(
        entity_type=EntityType.FEATURE,
        parent_classes=[],
        description="A specific functionality or characteristic of a product "
                    "that implements one or more capabilities.",
        properties={
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Feature name",
                examples=["Real-time Dashboard", "API Integration"]
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Feature description"
            ),
            "feature_category": PropertyDefinition(
                name="featureCategory",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Functional category",
                examples=["UI/UX", "Integration", "Analytics", "Automation"]
            ),
            "availability": PropertyDefinition(
                name="availability",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Product tier availability",
                examples=["Basic", "Professional", "Enterprise"]
            ),
        },
        allowed_relationships=[
            RelationshipType.FEATURE_IMPLEMENTS_CAPABILITY,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # APQC PROCESS CLASS (Reference Model)
    # =========================================================================
    EntityType.APQC_PROCESS: ClassDefinition(
        entity_type=EntityType.APQC_PROCESS,
        parent_classes=[],
        description="APQC Process Classification Framework process element.",
        properties={
            "apqc_id": PropertyDefinition(
                name="apqcId",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="APQC PCF identifier",
                examples=["1.1", "3.2.1"]
            ),
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Process name"
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Process description"
            ),
            "hierarchy_level": PropertyDefinition(
                name="hierarchyLevel",
                property_type="xsd:integer",
                cardinality_min=1,
                cardinality_max=1,
                description="PCF hierarchy level (1-5)"
            ),
            "version": PropertyDefinition(
                name="version",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="PCF version"
            ),
        },
        allowed_relationships=[],
        abstract=False
    ),
    
    # =========================================================================
    # BIAN SERVICE DOMAIN CLASS (Reference Model)
    # =========================================================================
    EntityType.BIAN_SERVICE_DOMAIN: ClassDefinition(
        entity_type=EntityType.BIAN_SERVICE_DOMAIN,
        parent_classes=[],
        description="BIAN Service Landscape service domain element.",
        properties={
            "bian_id": PropertyDefinition(
                name="bianId",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="BIAN service domain identifier",
                examples=["SD-01", "SD-42"]
            ),
            "name": PropertyDefinition(
                name="name",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Service domain name"
            ),
            "description": PropertyDefinition(
                name="description",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Service domain description"
            ),
            "business_area": PropertyDefinition(
                name="businessArea",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="BIAN business area classification"
            ),
            "service_domain_type": PropertyDefinition(
                name="serviceDomainType",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Type of service domain"
            ),
        },
        allowed_relationships=[],
        abstract=False
    ),
    
    # =========================================================================
    # DATA SOURCE CLASS (Provenance)
    # =========================================================================
    EntityType.DATA_SOURCE: ClassDefinition(
        entity_type=EntityType.DATA_SOURCE,
        parent_classes=[],
        description="Source document or data origin for extracted entities.",
        properties={
            "source_id": PropertyDefinition(
                name="sourceId",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Unique source identifier"
            ),
            "source_type": PropertyDefinition(
                name="sourceType",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Type of source",
                examples=["Website", "Document", "Database", "API"]
            ),
            "source_url": PropertyDefinition(
                name="sourceUrl",
                property_type="xsd:anyURI",
                cardinality_min=0,
                cardinality_max=1,
                description="Original source URL"
            ),
            "title": PropertyDefinition(
                name="title",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Source title"
            ),
            "ingestion_date": PropertyDefinition(
                name="ingestionDate",
                property_type="xsd:dateTime",
                cardinality_min=1,
                cardinality_max=1,
                description="When source was ingested"
            ),
            "content_hash": PropertyDefinition(
                name="contentHash",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Content fingerprint for deduplication"
            ),
        },
        allowed_relationships=[
            RelationshipType.EXTRACTED_FROM,
        ],
        abstract=False
    ),
    
    # =========================================================================
    # EXTRACTION EVENT CLASS (Provenance)
    # =========================================================================
    EntityType.EXTRACTION_EVENT: ClassDefinition(
        entity_type=EntityType.EXTRACTION_EVENT,
        parent_classes=[],
        description="Record of an extraction operation with metadata.",
        properties={
            "event_id": PropertyDefinition(
                name="eventId",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Unique event identifier"
            ),
            "extraction_timestamp": PropertyDefinition(
                name="extractionTimestamp",
                property_type="xsd:dateTime",
                cardinality_min=1,
                cardinality_max=1,
                description="When extraction occurred"
            ),
            "extraction_method": PropertyDefinition(
                name="extractionMethod",
                property_type="xsd:string",
                cardinality_min=1,
                cardinality_max=1,
                description="Method used",
                examples=["LLM-Guided", "Rule-Based", "Hybrid"]
            ),
            "model_version": PropertyDefinition(
                name="modelVersion",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="LLM model version used"
            ),
            "prompt_version": PropertyDefinition(
                name="promptVersion",
                property_type="xsd:string",
                cardinality_min=0,
                cardinality_max=1,
                description="Prompt template version"
            ),
            "entities_extracted": PropertyDefinition(
                name="entitiesExtracted",
                property_type="xsd:integer",
                cardinality_min=0,
                cardinality_max=1,
                description="Count of entities extracted"
            ),
            "relationships_extracted": PropertyDefinition(
                name="relationshipsExtracted",
                property_type="xsd:integer",
                cardinality_min=0,
                cardinality_max=1,
                description="Count of relationships extracted"
            ),
        },
        allowed_relationships=[
            RelationshipType.VALIDATED_BY,
        ],
        abstract=False
    ),
}


# =============================================================================
# ONTOLOGY SCHEMA ACCESSOR CLASS
# =============================================================================

class OntologySchema:
    """
    Central accessor for the Value Fabric ontology schema.
    Provides methods for schema introspection and validation.
    """
    
    def __init__(self):
        self.class_definitions = CLASS_DEFINITIONS
        self.relationship_constraints = RELATIONSHIP_CONSTRAINTS
        self.namespaces = OntologyNamespace()
    
    def get_class_definition(self, entity_type: EntityType) -> Optional[ClassDefinition]:
        """Retrieve class definition by entity type."""
        return self.class_definitions.get(entity_type)
    
    def get_all_entity_types(self) -> List[EntityType]:
        """Return all defined entity types."""
        return list(self.class_definitions.keys())
    
    def get_relationship_constraint(
        self, 
        relationship_type: RelationshipType
    ) -> Optional[RelationshipConstraint]:
        """Retrieve constraint for a relationship type."""
        return self.relationship_constraints.get(relationship_type)
    
    def get_allowed_relationships(self, entity_type: EntityType) -> List[RelationshipType]:
        """Get all relationships allowed for an entity type."""
        class_def = self.class_definitions.get(entity_type)
        if class_def:
            return class_def.allowed_relationships
        return []
    
    def validate_relationship(
        self,
        source_type: EntityType,
        relationship_type: RelationshipType,
        target_type: EntityType
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a relationship is allowed between entity types.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        constraint = self.relationship_constraints.get(relationship_type)
        if not constraint:
            return False, f"Unknown relationship type: {relationship_type}"
        
        if source_type not in constraint.domain:
            return False, (
                f"Entity type {source_type} not in domain of {relationship_type}. "
                f"Allowed: {constraint.domain}"
            )
        
        if target_type not in constraint.range:
            return False, (
                f"Entity type {target_type} not in range of {relationship_type}. "
                f"Allowed: {constraint.range}"
            )
        
        return True, None
    
    def get_property_definition(
        self, 
        entity_type: EntityType, 
        property_name: str
    ) -> Optional[PropertyDefinition]:
        """Get property definition for a specific entity type."""
        class_def = self.class_definitions.get(entity_type)
        if class_def:
            return class_def.properties.get(property_name)
        return None
    
    def get_inheritance_chain(self, entity_type: EntityType) -> List[EntityType]:
        """Get full inheritance chain for an entity type."""
        chain = []
        current = entity_type
        
        while current:
            class_def = self.class_definitions.get(current)
            if not class_def:
                break
            chain.append(current)
            # Get parent (for now, simple single inheritance)
            if class_def.parent_classes:
                current = class_def.parent_classes[0]
            else:
                break
        
        return chain
    
    def to_owl_class_iri(self, entity_type: EntityType) -> str:
        """Convert entity type to OWL class IRI."""
        return f"{OntologyNamespace.VF}{entity_type.value}"
    
    def to_owl_property_iri(self, relationship_type: RelationshipType) -> str:
        """Convert relationship type to OWL property IRI."""
        return f"{OntologyNamespace.VF}{relationship_type.value}"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_entity_uri(entity_type: EntityType, entity_id: str) -> str:
    """Generate a canonical URI for an entity instance."""
    return f"{OntologyNamespace.VF}{entity_type.value}/{entity_id}"


def create_relationship_uri(
    source_uri: str, 
    relationship_type: RelationshipType, 
    target_uri: str
) -> str:
    """Generate a canonical URI for a relationship instance."""
    rel_hash = hash(f"{source_uri}|{relationship_type.value}|{target_uri}")
    return f"{OntologyNamespace.VF}relationship/{abs(rel_hash)}"


# Global schema instance
ONTOLOGY_SCHEMA = OntologySchema()
