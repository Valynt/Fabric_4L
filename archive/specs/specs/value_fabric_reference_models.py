"""
Value Fabric SaaS Platform - Industry Reference Model Integration
=================================================================

This module defines the integration patterns for industry-standard reference models:
- APQC Process Classification Framework (PCF): Cross-industry business process taxonomy
- BIAN (Banking Industry Architecture Network): Financial services service landscape
- FIBO (Financial Industry Business Ontology): Financial instruments and risk ontology

Integration Patterns:
1. Taxonomy Mapping: Map Value Fabric entities to reference model concepts
2. Alignment Procedures: Automated and manual alignment workflows
3. Crosswalk Generation: Create bidirectional mappings
4. Import/Export: Load reference model data and export aligned ontologies
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

# Import from ontology schema module
from value_fabric_ontology_schema import (
    EntityType, OntologyNamespace
)


# =============================================================================
# REFERENCE MODEL ENUMERATIONS
# =============================================================================

class ReferenceModelType(Enum):
    """Supported industry reference models."""
    APQC_PCF = "apqc_pcf"
    BIAN = "bian"
    FIBO = "fibo"


class MappingDirection(Enum):
    """Direction of mapping between models."""
    TO_REFERENCE = "to_reference"      # Value Fabric -> Reference Model
    FROM_REFERENCE = "from_reference"  # Reference Model -> Value Fabric
    BIDIRECTIONAL = "bidirectional"


class MappingStatus(Enum):
    """Status of a mapping entry."""
    AUTO_MAPPED = "auto_mapped"
    MANUALLY_MAPPED = "manually_mapped"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class MappingConfidence(Enum):
    """Confidence level for automated mappings."""
    HIGH = "high"       # > 0.90 similarity
    MEDIUM = "medium"   # 0.75 - 0.90 similarity
    LOW = "low"         # 0.60 - 0.75 similarity
    UNCERTAIN = "uncertain"  # < 0.60 similarity


# =============================================================================
# MAPPING DATA STRUCTURES
# =============================================================================

@dataclass
class ReferenceModelConcept:
    """A concept from an industry reference model."""
    concept_id: str
    model_type: ReferenceModelType
    name: str
    description: str
    parent_id: Optional[str] = None
    hierarchy_level: int = 1
    properties: Dict[str, Any] = field(default_factory=dict)
    external_references: Dict[str, str] = field(default_factory=dict)
    
    def get_full_path(self, concept_map: Dict[str, 'ReferenceModelConcept']) -> str:
        """Get full hierarchical path for this concept."""
        path_parts = [self.name]
        current = self
        while current.parent_id and current.parent_id in concept_map:
            current = concept_map[current.parent_id]
            path_parts.insert(0, current.name)
        return " > ".join(path_parts)


@dataclass
class MappingEntry:
    """Single mapping between Value Fabric and reference model concepts."""
    mapping_id: str
    vf_entity_type: EntityType
    vf_entity_id: Optional[str]  # None for template mappings
    vf_entity_name: str
    
    reference_model: ReferenceModelType
    reference_concept_id: str
    reference_concept_name: str
    reference_hierarchy_path: str
    
    mapping_type: str  # exact, narrow, broad, related
    direction: MappingDirection
    status: MappingStatus
    confidence: MappingConfidence
    confidence_score: float
    
    mapping_method: str  # algorithm, manual, import
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    # Alignment metadata
    alignment_vector: Optional[List[float]] = None
    similarity_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class MappingRule:
    """Rule for automated mapping between models."""
    rule_id: str
    name: str
    source_model: ReferenceModelType
    target_entity_types: List[EntityType]
    match_criteria: Dict[str, Any]
    confidence_threshold: float
    mapping_type: str
    priority: int = 1
    active: bool = True


@dataclass
class CrosswalkReport:
    """Report of mappings between Value Fabric and reference model."""
    report_id: str
    reference_model: ReferenceModelType
    generated_at: datetime
    
    total_vf_entities: int
    total_reference_concepts: int
    
    mapped_count: int
    unmapped_vf_count: int
    unmapped_reference_count: int
    
    mapping_breakdown: Dict[str, int]  # by status, confidence, type
    coverage_percentage: float
    
    mappings: List[MappingEntry]
    unmapped_vf_entities: List[Tuple[EntityType, str]]
    unmapped_reference_concepts: List[str]


# =============================================================================
# APQC PCF INTEGRATION
# =============================================================================

class APQCPCFIntegration:
    """
    Integration with APQC Process Classification Framework (PCF).
    
    PCF provides a cross-industry taxonomy of business processes organized
    into 12 Enterprise Processes, each with hierarchical decomposition:
    - Level 1: Process Category (e.g., "1.0 Develop Vision and Strategy")
    - Level 2: Process Group (e.g., "1.1 Define the Business Concept")
    - Level 3: Process (e.g., "1.1.1 Assess the External Environment")
    - Level 4: Activity
    - Level 5: Task
    
    Mapping Strategy:
    - VF Capability <-> PCF Process (Level 3)
    - VF Process <-> PCF Activity (Level 4)
    - VF Activity <-> PCF Task (Level 5)
    """
    
    PCF_VERSION = "7.4"
    PCF_NAMESPACE = OntologyNamespace.APQC
    
    # PCF Enterprise Processes (Level 1)
    PCF_CATEGORIES = {
        "1.0": "Develop Vision and Strategy",
        "2.0": "Develop and Manage Products and Services",
        "3.0": "Market and Sell Products and Services",
        "4.0": "Deliver Physical Products",
        "5.0": "Deliver Services",
        "6.0": "Manage Customer Service",
        "7.0": "Develop and Manage Human Capital",
        "8.0": "Manage Information Technology",
        "9.0": "Manage Financial Resources",
        "10.0": "Acquire, Construct, and Manage Assets",
        "11.0": "Manage Enterprise Risk, Compliance, and Resilience",
        "12.0": "Manage External Relationships",
        "13.0": "Develop and Manage Business Capabilities",
    }
    
    def __init__(self, concept_store: Any):
        self.concept_store = concept_store
        self.concepts: Dict[str, ReferenceModelConcept] = {}
        self.mappings: Dict[str, MappingEntry] = {}
    
    async def load_pcf_data(self, pcf_export_path: str) -> int:
        """
        Load PCF data from export file.
        
        Args:
            pcf_export_path: Path to PCF JSON/XML export
            
        Returns:
            Number of concepts loaded
        """
        # Parse PCF export format
        with open(pcf_export_path, 'r') as f:
            pcf_data = json.load(f)
        
        loaded_count = 0
        for item in pcf_data.get("processes", []):
            concept = ReferenceModelConcept(
                concept_id=item["id"],
                model_type=ReferenceModelType.APQC_PCF,
                name=item["name"],
                description=item.get("description", ""),
                parent_id=item.get("parentId"),
                hierarchy_level=item.get("level", 1),
                properties={
                    "pcfCode": item.get("code"),
                    "pcfLevel": item.get("level"),
                    "industry": item.get("industry", "cross-industry"),
                    "version": self.PCF_VERSION
                }
            )
            self.concepts[concept.concept_id] = concept
            loaded_count += 1
        
        return loaded_count
    
    async def suggest_mappings(
        self,
        vf_entities: List[Tuple[EntityType, str, str]],  # (type, id, name)
        similarity_threshold: float = 0.75
    ) -> List[MappingEntry]:
        """
        Suggest mappings between VF entities and PCF concepts.
        
        Args:
            vf_entities: List of (entity_type, entity_id, entity_name) tuples
            similarity_threshold: Minimum similarity for suggestion
            
        Returns:
            List of proposed mapping entries
        """
        suggestions = []
        
        for entity_type, entity_id, entity_name in vf_entities:
            # Get embedding for VF entity
            vf_embedding = await self._get_embedding(entity_name)
            
            # Find best matching PCF concepts
            best_matches = []
            for concept in self.concepts.values():
                concept_embedding = await self._get_embedding(concept.name)
                similarity = self._compute_similarity(vf_embedding, concept_embedding)
                
                if similarity >= similarity_threshold:
                    best_matches.append((concept, similarity))
            
            # Sort by similarity
            best_matches.sort(key=lambda x: x[1], reverse=True)
            
            # Create mapping entries for top matches
            for concept, similarity in best_matches[:3]:
                confidence = self._score_to_confidence(similarity)
                
                mapping = MappingEntry(
                    mapping_id=f"map-apqc-{hash(entity_id + concept.concept_id) % 1000000}",
                    vf_entity_type=entity_type,
                    vf_entity_id=entity_id,
                    vf_entity_name=entity_name,
                    reference_model=ReferenceModelType.APQC_PCF,
                    reference_concept_id=concept.concept_id,
                    reference_concept_name=concept.name,
                    reference_hierarchy_path=concept.get_full_path(self.concepts),
                    mapping_type=self._determine_mapping_type(similarity),
                    direction=MappingDirection.BIDIRECTIONAL,
                    status=MappingStatus.PROPOSED,
                    confidence=confidence,
                    confidence_score=similarity,
                    mapping_method="semantic_similarity",
                    similarity_scores={"name_similarity": similarity}
                )
                suggestions.append(mapping)
        
        return suggestions
    
    def get_pcf_hierarchy(self, concept_id: str) -> List[ReferenceModelConcept]:
        """Get full hierarchy path for a PCF concept."""
        hierarchy = []
        current_id = concept_id
        
        while current_id and current_id in self.concepts:
            concept = self.concepts[current_id]
            hierarchy.insert(0, concept)
            current_id = concept.parent_id
        
        return hierarchy
    
    def get_capabilities_for_process(self, pcf_process_id: str) -> List[str]:
        """Get VF capabilities mapped to a PCF process."""
        capability_ids = []
        for mapping in self.mappings.values():
            if (mapping.reference_concept_id == pcf_process_id and
                mapping.vf_entity_type == EntityType.CAPABILITY and
                mapping.status in [MappingStatus.AUTO_MAPPED, MappingStatus.MANUALLY_MAPPED]):
                capability_ids.append(mapping.vf_entity_id)
        return capability_ids
    
    def _determine_mapping_type(self, similarity: float) -> str:
        """Determine mapping type based on similarity score."""
        if similarity > 0.95:
            return "exact"
        elif similarity > 0.85:
            return "narrow"
        elif similarity > 0.75:
            return "broad"
        else:
            return "related"
    
    def _score_to_confidence(self, score: float) -> MappingConfidence:
        """Convert similarity score to confidence level."""
        if score > 0.90:
            return MappingConfidence.HIGH
        elif score > 0.75:
            return MappingConfidence.MEDIUM
        elif score > 0.60:
            return MappingConfidence.LOW
        else:
            return MappingConfidence.UNCERTAIN
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get vector embedding for text."""
        # Placeholder - would call embedding service
        return [0.0] * 768
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity."""
        import math
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# =============================================================================
# BIAN INTEGRATION
# =============================================================================

class BIANIntegration:
    """
    Integration with BIAN (Banking Industry Architecture Network) Service Landscape.
    
    BIAN provides:
    - Service Domains: Business capabilities for banking (200+ domains)
    - Business Object Models: Standardized data definitions
    - Service Operations: Standardized service interfaces
    
    Mapping Strategy:
    - VF Capability <-> BIAN Service Domain
    - VF Service <-> BIAN Service Operation
    - VF Business Unit <-> BIAN Functional Area
    """
    
    BIAN_VERSION = "12.0"
    BIAN_NAMESPACE = OntologyNamespace.BIAN
    
    # BIAN Business Areas (Functional Groupings)
    BIAN_BUSINESS_AREAS = {
        "BA1": "Sales and Service",
        "BA2": "Product and Service Development",
        "BA3": "Operations and Execution",
        "BA4": "Risk and Compliance",
        "BA5": "Resource Management",
        "BA6": "Business Development",
        "BA7": "Information Management",
        "BA8": "Infrastructure",
    }
    
    def __init__(self, concept_store: Any):
        self.concept_store = concept_store
        self.service_domains: Dict[str, ReferenceModelConcept] = {}
        self.business_objects: Dict[str, ReferenceModelConcept] = {}
        self.mappings: Dict[str, MappingEntry] = {}
    
    async def load_bian_data(self, bian_export_path: str) -> Dict[str, int]:
        """
        Load BIAN Service Landscape data.
        
        Args:
            bian_export_path: Path to BIAN export
            
        Returns:
            Counts of loaded concepts by type
        """
        with open(bian_export_path, 'r') as f:
            bian_data = json.load(f)
        
        counts = {"service_domains": 0, "business_objects": 0}
        
        # Load Service Domains
        for sd in bian_data.get("serviceDomains", []):
            concept = ReferenceModelConcept(
                concept_id=sd["id"],
                model_type=ReferenceModelType.BIAN,
                name=sd["name"],
                description=sd.get("description", ""),
                properties={
                    "bianId": sd.get("bianId"),
                    "businessArea": sd.get("businessArea"),
                    "serviceDomainType": sd.get("type"),
                    "version": self.BIAN_VERSION
                },
                external_references={
                    "businessObjects": sd.get("businessObjects", []),
                    "serviceOperations": sd.get("serviceOperations", [])
                }
            )
            self.service_domains[concept.concept_id] = concept
            counts["service_domains"] += 1
        
        # Load Business Objects
        for bo in bian_data.get("businessObjects", []):
            concept = ReferenceModelConcept(
                concept_id=bo["id"],
                model_type=ReferenceModelType.BIAN,
                name=bo["name"],
                description=bo.get("description", ""),
                properties={
                    "objectType": bo.get("type"),
                    "version": self.BIAN_VERSION
                }
            )
            self.business_objects[concept.concept_id] = concept
            counts["business_objects"] += 1
        
        return counts
    
    async def suggest_capability_mappings(
        self,
        vf_capabilities: List[Tuple[str, str, str]],  # (id, name, description)
        similarity_threshold: float = 0.70
    ) -> List[MappingEntry]:
        """
        Suggest mappings between VF capabilities and BIAN Service Domains.
        
        Args:
            vf_capabilities: List of (id, name, description) tuples
            similarity_threshold: Minimum similarity for suggestion
            
        Returns:
            List of proposed mapping entries
        """
        suggestions = []
        
        for cap_id, cap_name, cap_desc in vf_capabilities:
            # Combine name and description for embedding
            combined_text = f"{cap_name}. {cap_desc}"
            vf_embedding = await self._get_embedding(combined_text)
            
            best_matches = []
            for domain in self.service_domains.values():
                domain_text = f"{domain.name}. {domain.description}"
                domain_embedding = await self._get_embedding(domain_text)
                similarity = self._compute_similarity(vf_embedding, domain_embedding)
                
                if similarity >= similarity_threshold:
                    best_matches.append((domain, similarity))
            
            best_matches.sort(key=lambda x: x[1], reverse=True)
            
            for domain, similarity in best_matches[:3]:
                mapping = MappingEntry(
                    mapping_id=f"map-bian-{hash(cap_id + domain.concept_id) % 1000000}",
                    vf_entity_type=EntityType.CAPABILITY,
                    vf_entity_id=cap_id,
                    vf_entity_name=cap_name,
                    reference_model=ReferenceModelType.BIAN,
                    reference_concept_id=domain.concept_id,
                    reference_concept_name=domain.name,
                    reference_hierarchy_path=domain.properties.get("businessArea", ""),
                    mapping_type=self._determine_mapping_type(similarity),
                    direction=MappingDirection.BIDIRECTIONAL,
                    status=MappingStatus.PROPOSED,
                    confidence=self._score_to_confidence(similarity),
                    confidence_score=similarity,
                    mapping_method="semantic_similarity_with_description"
                )
                suggestions.append(mapping)
        
        return suggestions
    
    def get_service_domain_details(self, domain_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a BIAN Service Domain."""
        domain = self.service_domains.get(domain_id)
        if not domain:
            return None
        
        return {
            "id": domain.concept_id,
            "name": domain.name,
            "description": domain.description,
            "businessArea": domain.properties.get("businessArea"),
            "serviceDomainType": domain.properties.get("serviceDomainType"),
            "businessObjects": domain.external_references.get("businessObjects", []),
            "serviceOperations": domain.external_references.get("serviceOperations", [])
        }
    
    def get_domains_by_business_area(self, business_area: str) -> List[ReferenceModelConcept]:
        """Get all service domains in a business area."""
        return [
            d for d in self.service_domains.values()
            if d.properties.get("businessArea") == business_area
        ]
    
    def _determine_mapping_type(self, similarity: float) -> str:
        if similarity > 0.95:
            return "exact"
        elif similarity > 0.85:
            return "narrow"
        elif similarity > 0.70:
            return "broad"
        else:
            return "related"
    
    def _score_to_confidence(self, score: float) -> MappingConfidence:
        if score > 0.90:
            return MappingConfidence.HIGH
        elif score > 0.75:
            return MappingConfidence.MEDIUM
        elif score > 0.60:
            return MappingConfidence.LOW
        else:
            return MappingConfidence.UNCERTAIN
    
    async def _get_embedding(self, text: str) -> List[float]:
        return [0.0] * 768
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        import math
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# =============================================================================
# FIBO INTEGRATION
# =============================================================================

class FIBOIntegration:
    """
    Integration with FIBO (Financial Industry Business Ontology).
    
    FIBO provides formal ontologies for:
    - Financial instruments (securities, derivatives, loans)
    - Business entities and legal structures
    - Risk parameters and indicators
    - Market data and indices
    - Regulatory concepts
    
    Mapping Strategy:
    - VF Product <-> FIBO Financial Instrument
    - VF Organization <-> FIBO Business Entity
    - VF Value Metric <-> FIBO Risk Parameter
    """
    
    FIBO_VERSION = "2023-Q4"
    FIBO_NAMESPACE = OntologyNamespace.FIBO
    
    # FIBO Top-level Modules
    FIBO_MODULES = {
        "FBC": "Financial Business and Commerce",
        "FND": "Foundations",
        "IND": "Indicators",
        "LOAN": "Loans",
        "MD": "Market Data",
        "SEC": "Securities",
        "DER": "Derivatives",
        "BP": "Business Processes",
        "CAE": "Corporate Actions and Events",
        "CI": "Currency Amounts and Indices",
        "EXT": "Extended Concepts"
    }
    
    def __init__(self, ontology_client: Any):
        self.ontology_client = ontology_client
        self.classes: Dict[str, ReferenceModelConcept] = {}
        self.properties: Dict[str, ReferenceModelConcept] = {}
        self.individuals: Dict[str, ReferenceModelConcept] = {}
    
    async def load_fibo_ontology(self, fibo_sparql_endpoint: str) -> Dict[str, int]:
        """
        Load FIBO ontology from SPARQL endpoint or RDF dump.
        
        Args:
            fibo_sparql_endpoint: SPARQL endpoint URL or path to RDF files
            
        Returns:
            Counts of loaded concepts by type
        """
        # Query FIBO for classes, properties, and individuals
        # This is a simplified representation
        
        counts = {"classes": 0, "properties": 0, "individuals": 0}
        
        # In production, execute SPARQL queries:
        # SELECT ?class ?label ?comment WHERE { ?class a owl:Class ... }
        
        return counts
    
    async def suggest_product_mappings(
        self,
        vf_products: List[Tuple[str, str, str, List[str]]],  # (id, name, desc, categories)
        similarity_threshold: float = 0.65
    ) -> List[MappingEntry]:
        """
        Suggest mappings between VF Products and FIBO Financial Instruments.
        
        Args:
            vf_products: List of (id, name, description, categories) tuples
            similarity_threshold: Minimum similarity for suggestion
            
        Returns:
            List of proposed mapping entries
        """
        suggestions = []
        
        # Filter FIBO classes to financial instruments
        instrument_classes = [
            c for c in self.classes.values()
            if any(module in c.properties.get("module", "") 
                   for module in ["SEC", "DER", "LOAN"])
        ]
        
        for prod_id, prod_name, prod_desc, categories in vf_products:
            combined_text = f"{prod_name}. {prod_desc}. Categories: {', '.join(categories)}"
            vf_embedding = await self._get_embedding(combined_text)
            
            best_matches = []
            for fibo_class in instrument_classes:
                class_text = f"{fibo_class.name}. {fibo_class.description}"
                class_embedding = await self._get_embedding(class_text)
                similarity = self._compute_similarity(vf_embedding, class_embedding)
                
                if similarity >= similarity_threshold:
                    best_matches.append((fibo_class, similarity))
            
            best_matches.sort(key=lambda x: x[1], reverse=True)
            
            for fibo_class, similarity in best_matches[:3]:
                mapping = MappingEntry(
                    mapping_id=f"map-fibo-{hash(prod_id + fibo_class.concept_id) % 1000000}",
                    vf_entity_type=EntityType.PRODUCT,
                    vf_entity_id=prod_id,
                    vf_entity_name=prod_name,
                    reference_model=ReferenceModelType.FIBO,
                    reference_concept_id=fibo_class.concept_id,
                    reference_concept_name=fibo_class.name,
                    reference_hierarchy_path=fibo_class.properties.get("module", ""),
                    mapping_type=self._determine_mapping_type(similarity),
                    direction=MappingDirection.BIDIRECTIONAL,
                    status=MappingStatus.PROPOSED,
                    confidence=self._score_to_confidence(similarity),
                    confidence_score=similarity,
                    mapping_method="fibo_semantic_matching"
                )
                suggestions.append(mapping)
        
        return suggestions
    
    def get_fibo_class_hierarchy(self, class_id: str) -> List[str]:
        """Get superclass hierarchy for a FIBO class."""
        # In production, query FIBO ontology for rdfs:subClassOf relationships
        return []
    
    def get_related_properties(self, class_id: str) -> List[str]:
        """Get properties applicable to a FIBO class."""
        # In production, query for domain/range relationships
        return []
    
    def _determine_mapping_type(self, similarity: float) -> str:
        if similarity > 0.90:
            return "exact"
        elif similarity > 0.75:
            return "narrow"
        elif similarity > 0.65:
            return "broad"
        else:
            return "related"
    
    def _score_to_confidence(self, score: float) -> MappingConfidence:
        if score > 0.90:
            return MappingConfidence.HIGH
        elif score > 0.75:
            return MappingConfidence.MEDIUM
        elif score > 0.60:
            return MappingConfidence.LOW
        else:
            return MappingConfidence.UNCERTAIN
    
    async def _get_embedding(self, text: str) -> List[float]:
        return [0.0] * 768
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        import math
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# =============================================================================
# MAPPING MANAGER
# =============================================================================

class ReferenceModelMappingManager:
    """
    Central manager for all reference model mappings.
    Coordinates mapping operations across APQC, BIAN, and FIBO.
    """
    
    def __init__(
        self,
        apqc_integration: APQCPCFIntegration,
        bian_integration: BIANIntegration,
        fibo_integration: FIBOIntegration,
        mapping_store: Any
    ):
        self.apqc = apqc_integration
        self.bian = bian_integration
        self.fibo = fibo_integration
        self.mapping_store = mapping_store
        
        self.integrations: Dict[ReferenceModelType, Any] = {
            ReferenceModelType.APQC_PCF: apqc_integration,
            ReferenceModelType.BIAN: bian_integration,
            ReferenceModelType.FIBO: fibo_integration
        }
    
    async def generate_crosswalk_report(
        self,
        reference_model: ReferenceModelType,
        vf_entity_filter: Optional[List[EntityType]] = None
    ) -> CrosswalkReport:
        """
        Generate a crosswalk report showing coverage between VF and reference model.
        
        Args:
            reference_model: Which reference model to report on
            vf_entity_filter: Optional filter for VF entity types
            
        Returns:
            CrosswalkReport with mapping statistics
        """
        # Get all mappings for the reference model
        all_mappings = await self._get_mappings_for_model(reference_model)
        
        # Apply entity type filter
        if vf_entity_filter:
            all_mappings = [
                m for m in all_mappings 
                if m.vf_entity_type in vf_entity_filter
            ]
        
        # Calculate statistics
        total_mapped = len([m for m in all_mappings if m.status in [
            MappingStatus.AUTO_MAPPED, MappingStatus.MANUALLY_MAPPED
        ]])
        
        status_breakdown = {}
        for status in MappingStatus:
            status_breakdown[status.value] = len([
                m for m in all_mappings if m.status == status
            ])
        
        confidence_breakdown = {}
        for conf in MappingConfidence:
            confidence_breakdown[conf.value] = len([
                m for m in all_mappings if m.confidence == conf
            ])
        
        # Get unmapped entities
        self.integrations[reference_model]
        unmapped_vf = await self._get_unmapped_vf_entities(reference_model, vf_entity_filter)
        unmapped_ref = await self._get_unmapped_reference_concepts(reference_model)
        
        # Calculate coverage
        total_vf = total_mapped + len(unmapped_vf)
        coverage = (total_mapped / total_vf * 100) if total_vf > 0 else 0.0
        
        return CrosswalkReport(
            report_id=f"report-{reference_model.value}-{datetime.utcnow().strftime('%Y%m%d')}",
            reference_model=reference_model,
            generated_at=datetime.utcnow(),
            total_vf_entities=total_vf,
            total_reference_concepts=len(await self._get_reference_concepts(reference_model)),
            mapped_count=total_mapped,
            unmapped_vf_count=len(unmapped_vf),
            unmapped_reference_count=len(unmapped_ref),
            mapping_breakdown={**status_breakdown, **confidence_breakdown},
            coverage_percentage=coverage,
            mappings=all_mappings,
            unmapped_vf_entities=unmapped_vf,
            unmapped_reference_concepts=unmapped_ref
        )
    
    async def approve_mapping(self, mapping_id: str, approved_by: str) -> bool:
        """Approve a proposed mapping."""
        mapping = await self._get_mapping(mapping_id)
        if not mapping:
            return False
        
        mapping.status = MappingStatus.MANUALLY_MAPPED
        mapping.reviewed_by = approved_by
        mapping.reviewed_at = datetime.utcnow()
        
        await self._save_mapping(mapping)
        return True
    
    async def reject_mapping(self, mapping_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a proposed mapping."""
        mapping = await self._get_mapping(mapping_id)
        if not mapping:
            return False
        
        mapping.status = MappingStatus.REJECTED
        mapping.reviewed_by = rejected_by
        mapping.reviewed_at = datetime.utcnow()
        mapping.notes = reason
        
        await self._save_mapping(mapping)
        return True
    
    async def create_manual_mapping(
        self,
        vf_entity_type: EntityType,
        vf_entity_id: str,
        reference_model: ReferenceModelType,
        reference_concept_id: str,
        created_by: str,
        mapping_type: str = "exact"
    ) -> MappingEntry:
        """Create a manual mapping between VF entity and reference concept."""
        # Get reference concept details
        self.integrations[reference_model]
        concept = await self._get_reference_concept(reference_model, reference_concept_id)
        
        vf_entity = await self._get_vf_entity(vf_entity_type, vf_entity_id)
        
        mapping = MappingEntry(
            mapping_id=f"map-manual-{hash(vf_entity_id + reference_concept_id) % 1000000}",
            vf_entity_type=vf_entity_type,
            vf_entity_id=vf_entity_id,
            vf_entity_name=vf_entity["name"],
            reference_model=reference_model,
            reference_concept_id=reference_concept_id,
            reference_concept_name=concept.name if concept else "",
            reference_hierarchy_path=concept.get_full_path({}) if concept else "",
            mapping_type=mapping_type,
            direction=MappingDirection.BIDIRECTIONAL,
            status=MappingStatus.MANUALLY_MAPPED,
            confidence=MappingConfidence.HIGH,
            confidence_score=1.0,
            mapping_method="manual",
            created_by=created_by
        )
        
        await self._save_mapping(mapping)
        return mapping
    
    # Placeholder methods for data access
    async def _get_mappings_for_model(self, model: ReferenceModelType) -> List[MappingEntry]:
        return []
    
    async def _get_mapping(self, mapping_id: str) -> Optional[MappingEntry]:
        return None
    
    async def _save_mapping(self, mapping: MappingEntry) -> None:
        pass
    
    async def _get_unmapped_vf_entities(
        self, 
        model: ReferenceModelType,
        entity_filter: Optional[List[EntityType]]
    ) -> List[Tuple[EntityType, str]]:
        return []
    
    async def _get_unmapped_reference_concepts(self, model: ReferenceModelType) -> List[str]:
        return []
    
    async def _get_reference_concepts(self, model: ReferenceModelType) -> List[str]:
        return []
    
    async def _get_reference_concept(
        self, 
        model: ReferenceModelType, 
        concept_id: str
    ) -> Optional[ReferenceModelConcept]:
        return None
    
    async def _get_vf_entity(self, entity_type: EntityType, entity_id: str) -> Dict[str, Any]:
        return {"name": ""}
