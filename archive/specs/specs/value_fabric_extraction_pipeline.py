"""
Value Fabric SaaS Platform - Extraction Pipeline Logic
======================================================

This module defines the schema-guided extraction pipeline that transforms
unstructured text into structured, ontology-conforming entities and relationships.

Pipeline Stages:
1. Prompt Generation - Convert ontology schema to LLM instructions
2. LLM Extraction - Generate structured output using Pydantic validation
3. Semantic Alignment - Map extracted strings to formal ontology
4. Coreference Resolution - Identify and merge duplicate entities
5. Entailment Validation - Verify logical consistency
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

# Import from ontology schema module
from value_fabric_ontology_schema import (
    EntityType, RelationshipType, ClassDefinition, OntologySchema
)


# =============================================================================
# PYDANTIC SCHEMAS FOR LLM OUTPUT VALIDATION
# =============================================================================

# Note: These are Python representations of Pydantic models
# In production, these would be actual Pydantic BaseModel classes

@dataclass
class ExtractedProperty:
    """Single property value extracted from text."""
    name: str
    value: Any
    confidence: float = 1.0
    source_text: Optional[str] = None
    source_span: Optional[Tuple[int, int]] = None


@dataclass
class ExtractedEntity:
    """Entity extracted from unstructured text."""
    entity_id: str
    entity_type: EntityType
    canonical_name: str
    properties: Dict[str, ExtractedProperty] = field(default_factory=dict)
    confidence_score: float = 1.0
    extraction_source: Optional[str] = None
    source_spans: List[Tuple[int, int]] = field(default_factory=list)
    alternative_names: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entityId": self.entity_id,
            "entityType": self.entity_type.value,
            "canonicalName": self.canonical_name,
            "properties": {
                k: {"value": v.value, "confidence": v.confidence}
                for k, v in self.properties.items()
            },
            "confidenceScore": self.confidence_score,
            "alternativeNames": self.alternative_names
        }


@dataclass
class ExtractedRelationship:
    """Relationship extracted between two entities."""
    relationship_id: str
    relationship_type: RelationshipType
    source_entity_id: str
    target_entity_id: str
    confidence_score: float = 1.0
    evidence_text: Optional[str] = None
    extraction_source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "relationshipId": self.relationship_id,
            "relationshipType": self.relationship_type.value,
            "sourceEntityId": self.source_entity_id,
            "targetEntityId": self.target_entity_id,
            "confidenceScore": self.confidence_score,
            "evidenceText": self.evidence_text
        }


@dataclass
class ExtractionResult:
    """Complete result from an extraction operation."""
    extraction_id: str
    source_id: str
    entities: List[ExtractedEntity] = field(default_factory=list)
    relationships: List[ExtractedRelationship] = field(default_factory=list)
    extraction_timestamp: datetime = field(default_factory=datetime.utcnow)
    model_version: str = ""
    prompt_version: str = ""
    processing_time_ms: int = 0
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "extractionId": self.extraction_id,
            "sourceId": self.source_id,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "extractionTimestamp": self.extraction_timestamp.isoformat(),
            "modelVersion": self.model_version,
            "promptVersion": self.prompt_version,
            "processingTimeMs": self.processing_time_ms,
            "validationErrors": self.validation_errors
        }


# =============================================================================
# PROMPT GENERATION MODULE
# =============================================================================

class PromptTemplate:
    """Template for generating LLM extraction prompts."""
    
    def __init__(self, schema: OntologySchema):
        self.schema = schema
    
    def generate_entity_extraction_prompt(
        self,
        entity_types: List[EntityType],
        context_text: str,
        extraction_guidance: Optional[str] = None
    ) -> str:
        """
        Generate a structured prompt for entity extraction.
        
        Args:
            entity_types: Types of entities to extract
            context_text: Source text for extraction
            extraction_guidance: Optional domain-specific guidance
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # System instruction
        prompt_parts.append(
            "You are an expert knowledge extraction system. Your task is to "
            "extract entities from the provided text and output them as "
            "structured JSON conforming to the specified schema."
        )
        
        # Schema definition section
        prompt_parts.append("\n=== EXTRACTION SCHEMA ===\n")
        for entity_type in entity_types:
            class_def = self.schema.get_class_definition(entity_type)
            if class_def:
                prompt_parts.append(self._format_class_schema(class_def))
        
        # Output format specification
        prompt_parts.append("\n=== OUTPUT FORMAT ===\n")
        prompt_parts.append(
            "Output a JSON object with the following structure:\n"
            "{\n"
            '  "entities": [\n'
            '    {\n'
            '      "entityId": "unique-id",\n'
            '      "entityType": "EntityTypeName",\n'
            '      "canonicalName": "Primary name",\n'
            '      "properties": {\n'
            '        "propertyName": {"value": "...", "confidence": 0.95}\n'
            '      },\n'
            '      "alternativeNames": ["alias1", "alias2"],\n'
            '      "confidenceScore": 0.95\n'
            '    }\n'
            '  ]\n'
            "}\n"
        )
        
        # Extraction rules
        prompt_parts.append("\n=== EXTRACTION RULES ===\n")
        prompt_parts.append(
            "1. Use canonical naming - prefer standard industry terminology\n"
            "2. Avoid duplication - if the same concept appears multiple times, "
            "create ONE entity with multiple source spans\n"
            "3. Confidence scores should reflect certainty (0.0-1.0)\n"
            "4. Include alternative names/aliases found in the text\n"
            "5. Only extract entities that clearly match the defined types\n"
            "6. Properties marked as required MUST be included\n"
        )
        
        # Domain guidance
        if extraction_guidance:
            prompt_parts.append(f"\n=== DOMAIN GUIDANCE ===\n{extraction_guidance}\n")
        
        # Source text
        prompt_parts.append(f"\n=== SOURCE TEXT ===\n{context_text}\n")
        
        return "\n".join(prompt_parts)
    
    def generate_relationship_extraction_prompt(
        self,
        entities: List[ExtractedEntity],
        context_text: str,
        allowed_relationships: Optional[List[RelationshipType]] = None
    ) -> str:
        """
        Generate a prompt for relationship extraction between known entities.
        
        Args:
            entities: Previously extracted entities
            context_text: Source text
            allowed_relationships: Optional filter for relationship types
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        prompt_parts.append(
            "You are an expert knowledge extraction system. Your task is to "
            "identify relationships between the provided entities based on the "
            "source text. Only create relationships that are EXPLICITLY supported "
            "by the text - do NOT infer connections based on proximity alone."
        )
        
        # Available entities
        prompt_parts.append("\n=== AVAILABLE ENTITIES ===\n")
        for entity in entities:
            prompt_parts.append(
                f"ID: {entity.entity_id}\n"
                f"Type: {entity.entity_type.value}\n"
                f"Name: {entity.canonical_name}\n"
                "---"
            )
        
        # Relationship schema
        prompt_parts.append("\n=== ALLOWED RELATIONSHIP TYPES ===\n")
        relationships = allowed_relationships or list(RelationshipType)
        for rel_type in relationships:
            constraint = self.schema.get_relationship_constraint(rel_type)
            if constraint:
                prompt_parts.append(
                    f"{rel_type.value}: "
                    f"{constraint.domain[0].value} -> {constraint.range[0].value}\n"
                    f"  Description: {self._get_relationship_description(rel_type)}"
                )
        
        # Output format
        prompt_parts.append("\n=== OUTPUT FORMAT ===\n")
        prompt_parts.append(
            "{\n"
            '  "relationships": [\n'
            '    {\n'
            '      "relationshipId": "unique-id",\n'
            '      "relationshipType": "relationshipName",\n'
            '      "sourceEntityId": "entity-id",\n'
            '      "targetEntityId": "entity-id",\n'
            '      "confidenceScore": 0.95,\n'
            '      "evidenceText": "Text supporting this relationship"\n'
            '    }\n'
            '  ]\n'
            "}\n"
        )
        
        # Validation rules
        prompt_parts.append("\n=== VALIDATION RULES ===\n")
        prompt_parts.append(
            "1. Only use relationship types from the allowed list\n"
            "2. Source and target must match the domain/range constraints\n"
            "3. Include evidence text that explicitly supports the relationship\n"
            "4. Confidence should reflect strength of evidence\n"
            "5. Do NOT create relationships based on semantic proximity alone\n"
            "6. The relationship must be CAUSAL or FUNCTIONAL, not coincidental\n"
        )
        
        # Source text
        prompt_parts.append(f"\n=== SOURCE TEXT ===\n{context_text}\n")
        
        return "\n".join(prompt_parts)
    
    def _format_class_schema(self, class_def: ClassDefinition) -> str:
        """Format a class definition for prompt inclusion."""
        lines = [f"\nENTITY TYPE: {class_def.entity_type.value}"]
        lines.append(f"Description: {class_def.description}")
        lines.append("\nProperties:")
        
        for prop_name, prop_def in class_def.properties.items():
            required = "(REQUIRED)" if prop_def.cardinality_min > 0 else "(optional)"
            lines.append(
                f"  - {prop_name} {required}\n"
                f"    Type: {prop_def.property_type}\n"
                f"    Description: {prop_def.description}"
            )
            if prop_def.examples:
                lines.append(f"    Examples: {', '.join(prop_def.examples)}")
        
        return "\n".join(lines)
    
    def _get_relationship_description(self, rel_type: RelationshipType) -> str:
        """Get human-readable description for relationship type."""
        descriptions = {
            RelationshipType.CAPABILITY_ENABLES_USECASE: 
                "A capability makes a use case possible",
            RelationshipType.CAPABILITY_REQUIRES_CAPABILITY:
                "A capability depends on another capability",
            RelationshipType.CAPABILITY_SUBTYPE_OF:
                "A capability is a specialized subtype of another",
            RelationshipType.USE_CASE_DELIVERS_VALUE:
                "A use case produces a value outcome",
            RelationshipType.USE_CASE_INVOLVES_PERSONA:
                "A use case involves a specific user persona",
            RelationshipType.FEATURE_IMPLEMENTS_CAPABILITY:
                "A feature provides a capability",
            RelationshipType.SEMANTICALLY_EQUIVALENT:
                "Two entities represent the same concept",
        }
        return descriptions.get(rel_type, "No description available")


# =============================================================================
# SEMANTIC ALIGNMENT MODULE
# =============================================================================

@dataclass
class AlignmentCandidate:
    """Candidate for semantic alignment."""
    candidate_id: str
    canonical_form: str
    entity_type: EntityType
    vector_embedding: List[float]
    source_ontology: str
    confidence: float = 0.0


@dataclass
class AlignmentResult:
    """Result of semantic alignment."""
    extracted_entity_id: str
    aligned_entity_id: Optional[str]
    alignment_score: float
    alignment_method: str
    is_new_entity: bool
    suggested_canonical_name: Optional[str] = None


class SemanticAligner:
    """
    Aligns extracted entities against the formal ontology using
    vector-based similarity and fuzzy matching.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        vector_store_client: Optional[Any] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.vector_store = vector_store_client
        self.alignment_cache: Dict[str, AlignmentResult] = {}
    
    async def align_entity(
        self,
        extracted_entity: ExtractedEntity,
        candidate_pool: List[AlignmentCandidate]
    ) -> AlignmentResult:
        """
        Align an extracted entity against candidate entities.
        
        Args:
            extracted_entity: Entity from extraction
            candidate_pool: Existing entities to match against
            
        Returns:
            Alignment result with match or new entity decision
        """
        # Check cache
        cache_key = self._compute_cache_key(extracted_entity)
        if cache_key in self.alignment_cache:
            return self.alignment_cache[cache_key]
        
        # Get embedding for extracted entity
        extracted_embedding = await self._get_embedding(
            extracted_entity.canonical_name,
            extracted_entity.entity_type
        )
        
        # Filter candidates by entity type
        type_candidates = [
            c for c in candidate_pool 
            if c.entity_type == extracted_entity.entity_type
        ]
        
        if not type_candidates:
            # No candidates of same type - create new entity
            result = AlignmentResult(
                extracted_entity_id=extracted_entity.entity_id,
                aligned_entity_id=None,
                alignment_score=0.0,
                alignment_method="no_candidates",
                is_new_entity=True,
                suggested_canonical_name=extracted_entity.canonical_name
            )
            self.alignment_cache[cache_key] = result
            return result
        
        # Compute similarities
        best_match = None
        best_score = 0.0
        
        for candidate in type_candidates:
            similarity = self._compute_similarity(
                extracted_embedding,
                candidate.vector_embedding
            )
            
            # Boost score for exact name matches
            if self._normalize_name(extracted_entity.canonical_name) == \
               self._normalize_name(candidate.canonical_form):
                similarity = max(similarity, 0.95)
            
            if similarity > best_score:
                best_score = similarity
                best_match = candidate
        
        # Determine alignment result
        if best_score >= self.similarity_threshold:
            result = AlignmentResult(
                extracted_entity_id=extracted_entity.entity_id,
                aligned_entity_id=best_match.candidate_id,
                alignment_score=best_score,
                alignment_method="vector_similarity",
                is_new_entity=False,
                suggested_canonical_name=best_match.canonical_form
            )
        else:
            result = AlignmentResult(
                extracted_entity_id=extracted_entity.entity_id,
                aligned_entity_id=None,
                alignment_score=best_score,
                alignment_method="below_threshold",
                is_new_entity=True,
                suggested_canonical_name=extracted_entity.canonical_name
            )
        
        self.alignment_cache[cache_key] = result
        return result
    
    async def align_batch(
        self,
        extracted_entities: List[ExtractedEntity],
        candidate_pool: List[AlignmentCandidate]
    ) -> List[AlignmentResult]:
        """Align multiple entities efficiently."""
        results = []
        for entity in extracted_entities:
            result = await self.align_entity(entity, candidate_pool)
            results.append(result)
        return results
    
    async def _get_embedding(
        self, 
        text: str, 
        entity_type: EntityType
    ) -> List[float]:
        """Get vector embedding for text."""
        # In production, this would call an embedding service
        # Placeholder implementation
        if self.vector_store:
            return await self.vector_store.get_embedding(text)
        # Return dummy embedding for development
        return [0.0] * 768
    
    def _compute_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between embeddings."""
        import math
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for comparison."""
        return name.lower().strip().replace("-", " ").replace("_", " ")
    
    def _compute_cache_key(self, entity: ExtractedEntity) -> str:
        """Compute cache key for alignment result."""
        key_data = f"{entity.entity_type.value}:{entity.canonical_name}"
        return hashlib.md5(key_data.encode()).hexdigest()


# =============================================================================
# COREFERENCE RESOLUTION MODULE
# =============================================================================

@dataclass
class CoreferenceCluster:
    """Cluster of coreferent entities."""
    cluster_id: str
    canonical_entity_id: str
    canonical_name: str
    entity_type: EntityType
    member_entity_ids: List[str]
    confidence: float
    resolution_method: str


@dataclass
class CoreferenceRule:
    """Rule for identifying coreferences."""
    name: str
    entity_types: List[EntityType]
    match_criteria: Dict[str, Any]
    confidence_boost: float


class CoreferenceResolver:
    """
    Identifies and resolves coreferences between extracted entities.
    Handles cases like "inventory tracking" vs "automated stock management".
    """
    
    def __init__(self, schema: OntologySchema):
        self.schema = schema
        self.resolution_rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[CoreferenceRule]:
        """Initialize coreference resolution rules."""
        return [
            CoreferenceRule(
                name="exact_name_match",
                entity_types=list(EntityType),
                match_criteria={"name_similarity": "exact"},
                confidence_boost=1.0
            ),
            CoreferenceRule(
                name="normalized_name_match",
                entity_types=list(EntityType),
                match_criteria={"name_similarity": "normalized"},
                confidence_boost=0.95
            ),
            CoreferenceRule(
                name="shared_alternative_name",
                entity_types=list(EntityType),
                match_criteria={"alternative_name_overlap": True},
                confidence_boost=0.90
            ),
            CoreferenceRule(
                name="capability_hierarchy",
                entity_types=[EntityType.CAPABILITY],
                match_criteria={"parent_child_overlap": True},
                confidence_boost=0.85
            ),
        ]
    
    def resolve_coreferences(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[CoreferenceCluster]:
        """
        Identify coreference clusters among extracted entities.
        
        Args:
            entities: All extracted entities
            relationships: All extracted relationships
            
        Returns:
            List of coreference clusters
        """
        clusters = []
        processed_ids = set()
        
        # Group entities by type
        entities_by_type: Dict[EntityType, List[ExtractedEntity]] = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        # Process each type group
        for entity_type, type_entities in entities_by_type.items():
            for i, entity1 in enumerate(type_entities):
                if entity1.entity_id in processed_ids:
                    continue
                
                cluster_members = [entity1]
                
                for entity2 in type_entities[i+1:]:
                    if entity2.entity_id in processed_ids:
                        continue
                    
                    if self._check_coreference(entity1, entity2, relationships):
                        cluster_members.append(entity2)
                
                if len(cluster_members) > 1:
                    cluster = self._create_cluster(cluster_members)
                    clusters.append(cluster)
                    for member in cluster_members:
                        processed_ids.add(member.entity_id)
        
        return clusters
    
    def _check_coreference(
        self,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity,
        relationships: List[ExtractedRelationship]
    ) -> bool:
        """Check if two entities are coreferent."""
        # Exact name match
        if entity1.canonical_name.lower() == entity2.canonical_name.lower():
            return True
        
        # Normalized name match
        norm1 = self._normalize_for_comparison(entity1.canonical_name)
        norm2 = self._normalize_for_comparison(entity2.canonical_name)
        if norm1 == norm2:
            return True
        
        # Alternative name overlap
        all_names1 = {entity1.canonical_name.lower()} | \
                     {a.lower() for a in entity1.alternative_names}
        all_names2 = {entity2.canonical_name.lower()} | \
                     {a.lower() for a in entity2.alternative_names}
        if all_names1 & all_names2:
            return True
        
        # Semantic equivalence relationship
        for rel in relationships:
            if rel.relationship_type == RelationshipType.SEMANTICALLY_EQUIVALENT:
                if (rel.source_entity_id == entity1.entity_id and 
                    rel.target_entity_id == entity2.entity_id) or \
                   (rel.source_entity_id == entity2.entity_id and 
                    rel.target_entity_id == entity1.entity_id):
                    return True
        
        # Vector similarity check (placeholder)
        # In production, compare embeddings
        
        return False
    
    def _normalize_for_comparison(self, name: str) -> str:
        """Normalize name for coreference comparison."""
        # Remove common suffixes/prefixes
        stop_words = {'system', 'solution', 'platform', 'module', 'feature'}
        words = name.lower().split()
        words = [w for w in words if w not in stop_words]
        return ' '.join(sorted(words))
    
    def _create_cluster(
        self,
        members: List[ExtractedEntity]
    ) -> CoreferenceCluster:
        """Create a coreference cluster from member entities."""
        # Select canonical entity (highest confidence or shortest name)
        canonical = max(members, key=lambda e: (e.confidence_score, -len(e.canonical_name)))
        
        return CoreferenceCluster(
            cluster_id=f"cluster-{uuid.uuid4().hex[:8]}",
            canonical_entity_id=canonical.entity_id,
            canonical_name=canonical.canonical_name,
            entity_type=canonical.entity_type,
            member_entity_ids=[m.entity_id for m in members],
            confidence=canonical.confidence_score,
            resolution_method="rule_based"
        )


# =============================================================================
# ENTAILMENT VALIDATION MODULE
# =============================================================================

@dataclass
class ValidationRule:
    """Rule for validating extracted knowledge."""
    rule_id: str
    rule_type: str
    description: str
    severity: str  # ERROR, WARNING, INFO
    validation_function: str  # Name of validation function


@dataclass
class ValidationResult:
    """Result of validation check."""
    rule_id: str
    passed: bool
    severity: str
    message: str
    affected_entities: List[str]
    affected_relationships: List[str]
    suggestion: Optional[str] = None


class EntailmentValidator:
    """
    Validates extracted entities and relationships against ontology constraints.
    Performs logical consistency checks and inheritance validation.
    """
    
    def __init__(self, schema: OntologySchema):
        self.schema = schema
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """Initialize validation rule set."""
        return [
            ValidationRule(
                rule_id="VAL-001",
                rule_type="cardinality",
                description="Required properties must be present",
                severity="ERROR",
                validation_function="validate_required_properties"
            ),
            ValidationRule(
                rule_id="VAL-002",
                rule_type="domain_range",
                description="Relationships must respect domain/range constraints",
                severity="ERROR",
                validation_function="validate_domain_range"
            ),
            ValidationRule(
                rule_id="VAL-003",
                rule_type="cardinality",
                description="Relationship cardinality must be respected",
                severity="WARNING",
                validation_function="validate_relationship_cardinality"
            ),
            ValidationRule(
                rule_id="VAL-004",
                rule_type="hierarchy",
                description="Inheritance hierarchies must be acyclic",
                severity="ERROR",
                validation_function="validate_hierarchy_acyclic"
            ),
            ValidationRule(
                rule_id="VAL-005",
                rule_type="consistency",
                description="No contradictory relationships",
                severity="ERROR",
                validation_function="validate_consistency"
            ),
            ValidationRule(
                rule_id="VAL-006",
                rule_type="confidence",
                description="Confidence scores should be reasonable",
                severity="WARNING",
                validation_function="validate_confidence_scores"
            ),
        ]
    
    def validate_extraction(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """
        Validate extraction results against all rules.
        
        Args:
            entities: Extracted entities
            relationships: Extracted relationships
            
        Returns:
            List of validation results
        """
        results = []
        
        # Validate required properties
        results.extend(self._validate_required_properties(entities))
        
        # Validate domain/range constraints
        results.extend(self._validate_domain_range(entities, relationships))
        
        # Validate relationship cardinality
        results.extend(self._validate_relationship_cardinality(entities, relationships))
        
        # Validate hierarchy acyclicity
        results.extend(self._validate_hierarchy_acyclic(entities, relationships))
        
        # Validate consistency
        results.extend(self._validate_consistency(entities, relationships))
        
        # Validate confidence scores
        results.extend(self._validate_confidence_scores(entities, relationships))
        
        return results
    
    def _validate_required_properties(
        self,
        entities: List[ExtractedEntity]
    ) -> List[ValidationResult]:
        """Validate that all required properties are present."""
        results = []
        
        for entity in entities:
            class_def = self.schema.get_class_definition(entity.entity_type)
            if not class_def:
                continue
            
            for prop_name, prop_def in class_def.properties.items():
                if prop_def.cardinality_min > 0:
                    if prop_name not in entity.properties:
                        results.append(ValidationResult(
                            rule_id="VAL-001",
                            passed=False,
                            severity="ERROR",
                            message=f"Required property '{prop_name}' missing "
                                    f"from {entity.entity_type.value} '{entity.canonical_name}'",
                            affected_entities=[entity.entity_id],
                            affected_relationships=[],
                            suggestion=f"Add '{prop_name}' property or reduce cardinality requirement"
                        ))
        
        return results
    
    def _validate_domain_range(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """Validate domain/range constraints for relationships."""
        results = []
        entity_map = {e.entity_id: e for e in entities}
        
        for rel in relationships:
            constraint = self.schema.get_relationship_constraint(rel.relationship_type)
            if not constraint:
                continue
            
            source = entity_map.get(rel.source_entity_id)
            target = entity_map.get(rel.target_entity_id)
            
            if source and source.entity_type not in constraint.domain:
                results.append(ValidationResult(
                    rule_id="VAL-002",
                    passed=False,
                    severity="ERROR",
                    message=f"Entity type {source.entity_type} not in domain of "
                            f"{rel.relationship_type.value}",
                    affected_entities=[rel.source_entity_id],
                    affected_relationships=[rel.relationship_id],
                    suggestion="Change relationship type or source entity type"
                ))
            
            if target and target.entity_type not in constraint.range:
                results.append(ValidationResult(
                    rule_id="VAL-002",
                    passed=False,
                    severity="ERROR",
                    message=f"Entity type {target.entity_type} not in range of "
                            f"{rel.relationship_type.value}",
                    affected_entities=[rel.target_entity_id],
                    affected_relationships=[rel.relationship_id],
                    suggestion="Change relationship type or target entity type"
                ))
        
        return results
    
    def _validate_relationship_cardinality(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """Validate relationship cardinality constraints."""
        results = []
        
        # Count relationships per entity
        rel_count: Dict[str, Dict[RelationshipType, int]] = {}
        for rel in relationships:
            if rel.source_entity_id not in rel_count:
                rel_count[rel.source_entity_id] = {}
            if rel.relationship_type not in rel_count[rel.source_entity_id]:
                rel_count[rel.source_entity_id][rel.relationship_type] = 0
            rel_count[rel.source_entity_id][rel.relationship_type] += 1
        
        # Check against constraints
        for entity_id, type_counts in rel_count.items():
            for rel_type, count in type_counts.items():
                constraint = self.schema.get_relationship_constraint(rel_type)
                if not constraint:
                    continue
                
                if constraint.cardinality_max and count > constraint.cardinality_max:
                    results.append(ValidationResult(
                        rule_id="VAL-003",
                        passed=False,
                        severity="WARNING",
                        message=f"Entity {entity_id} has {count} {rel_type.value} "
                                f"relationships, exceeding max of {constraint.cardinality_max}",
                        affected_entities=[entity_id],
                        affected_relationships=[],
                        suggestion="Review and consolidate redundant relationships"
                    ))
        
        return results
    
    def _validate_hierarchy_acyclic(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """Validate that inheritance hierarchies contain no cycles."""
        results = []
        
        # Build hierarchy graph
        hierarchy_edges: Dict[str, str] = {}
        for rel in relationships:
            if rel.relationship_type == RelationshipType.CAPABILITY_SUBTYPE_OF:
                hierarchy_edges[rel.source_entity_id] = rel.target_entity_id
        
        # Check for cycles using DFS
        def has_cycle(node: str, visited: Set[str], path: Set[str]) -> bool:
            if node in path:
                return True
            if node in visited:
                return False
            visited.add(node)
            path.add(node)
            if node in hierarchy_edges:
                if has_cycle(hierarchy_edges[node], visited, path):
                    return True
            path.remove(node)
            return False
        
        visited: Set[str] = set()
        for node in hierarchy_edges:
            if has_cycle(node, visited, set()):
                results.append(ValidationResult(
                    rule_id="VAL-004",
                    passed=False,
                    severity="ERROR",
                    message=f"Cycle detected in hierarchy starting from {node}",
                    affected_entities=[node],
                    affected_relationships=[],
                    suggestion="Remove cyclic relationship to restore hierarchy"
                ))
        
        return results
    
    def _validate_consistency(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """Validate logical consistency of relationships."""
        results = []
        
        # Check for contradictory relationships
        rel_pairs: Dict[Tuple[str, str], List[RelationshipType]] = {}
        for rel in relationships:
            pair = tuple(sorted([rel.source_entity_id, rel.target_entity_id]))
            if pair not in rel_pairs:
                rel_pairs[pair] = []
            rel_pairs[pair].append(rel.relationship_type)
        
        # Define contradictory pairs
        contradictory = [
            {RelationshipType.CAPABILITY_SUBTYPE_OF, 
             RelationshipType.CAPABILITY_REQUIRES_CAPABILITY},
        ]
        
        for pair, rel_types in rel_pairs.items():
            rel_type_set = set(rel_types)
            for contra_set in contradictory:
                if rel_type_set & contra_set == contra_set:
                    results.append(ValidationResult(
                        rule_id="VAL-005",
                        passed=False,
                        severity="ERROR",
                        message=f"Contradictory relationships between {pair[0]} and {pair[1]}",
                        affected_entities=list(pair),
                        affected_relationships=[],
                        suggestion="Remove one of the contradictory relationships"
                    ))
        
        return results
    
    def _validate_confidence_scores(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[ValidationResult]:
        """Validate that confidence scores are within reasonable bounds."""
        results = []
        
        for entity in entities:
            if entity.confidence_score < 0.5:
                results.append(ValidationResult(
                    rule_id="VAL-006",
                    passed=False,
                    severity="WARNING",
                    message=f"Low confidence score ({entity.confidence_score}) for entity "
                            f"'{entity.canonical_name}'",
                    affected_entities=[entity.entity_id],
                    affected_relationships=[],
                    suggestion="Review extraction or provide more context"
                ))
            if entity.confidence_score > 1.0 or entity.confidence_score < 0.0:
                results.append(ValidationResult(
                    rule_id="VAL-006",
                    passed=False,
                    severity="ERROR",
                    message=f"Invalid confidence score ({entity.confidence_score}) for entity "
                            f"'{entity.canonical_name}'",
                    affected_entities=[entity.entity_id],
                    affected_relationships=[],
                    suggestion="Confidence must be between 0.0 and 1.0"
                ))
        
        return results


# =============================================================================
# MAIN EXTRACTION PIPELINE
# =============================================================================

@dataclass
class PipelineConfig:
    """Configuration for the extraction pipeline."""
    similarity_threshold: float = 0.85
    confidence_threshold: float = 0.5
    enable_coreference_resolution: bool = True
    enable_entailment_validation: bool = True
    max_entities_per_extraction: int = 100
    max_relationships_per_extraction: int = 200
    model_version: str = "gpt-4"
    prompt_version: str = "v1.0"


class ExtractionPipeline:
    """
    Main orchestration class for the schema-guided extraction pipeline.
    Coordinates prompt generation, LLM extraction, validation, and alignment.
    """
    
    def __init__(
        self,
        schema: OntologySchema,
        config: PipelineConfig,
        llm_client: Any,
        vector_store: Any
    ):
        self.schema = schema
        self.config = config
        self.llm_client = llm_client
        self.vector_store = vector_store
        
        # Initialize components
        self.prompt_template = PromptTemplate(schema)
        self.semantic_aligner = SemanticAligner(
            config.similarity_threshold,
            vector_store
        )
        self.coreference_resolver = CoreferenceResolver(schema)
        self.entailment_validator = EntailmentValidator(schema)
    
    async def process_document(
        self,
        source_id: str,
        document_text: str,
        target_entity_types: Optional[List[EntityType]] = None
    ) -> ExtractionResult:
        """
        Process a document through the full extraction pipeline.
        
        Args:
            source_id: Identifier for the source document
            document_text: Text content to extract from
            target_entity_types: Types of entities to extract
            
        Returns:
            ExtractionResult with validated entities and relationships
        """
        import time
        start_time = time.time()
        
        # Default to all entity types if not specified
        if target_entity_types is None:
            target_entity_types = [
                EntityType.CAPABILITY,
                EntityType.USE_CASE,
                EntityType.PERSONA,
                EntityType.VALUE_DRIVER,
                EntityType.FEATURE
            ]
        
        extraction_id = f"ext-{uuid.uuid4().hex[:12]}"
        
        # Stage 1: Entity Extraction
        entities = await self._extract_entities(
            source_id, document_text, target_entity_types
        )
        
        # Stage 2: Relationship Extraction
        relationships = await self._extract_relationships(
            source_id, document_text, entities
        )
        
        # Stage 3: Semantic Alignment
        entities, relationships = await self._perform_alignment(entities, relationships)
        
        # Stage 4: Coreference Resolution
        if self.config.enable_coreference_resolution:
            entities, relationships = self._resolve_coreferences(entities, relationships)
        
        # Stage 5: Entailment Validation
        validation_results = []
        if self.config.enable_entailment_validation:
            validation_results = self.entailment_validator.validate_extraction(
                entities, relationships
            )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build result
        result = ExtractionResult(
            extraction_id=extraction_id,
            source_id=source_id,
            entities=entities,
            relationships=relationships,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
            processing_time_ms=processing_time,
            validation_errors=[v.message for v in validation_results if not v.passed]
        )
        
        return result
    
    async def _extract_entities(
        self,
        source_id: str,
        document_text: str,
        entity_types: List[EntityType]
    ) -> List[ExtractedEntity]:
        """Extract entities using LLM with schema-guided prompt."""
        # Generate prompt
        prompt = self.prompt_template.generate_entity_extraction_prompt(
            entity_types, document_text
        )
        
        # Call LLM
        llm_response = await self.llm_client.complete(
            prompt,
            response_format="json",
            temperature=0.1
        )
        
        # Parse and validate response
        try:
            parsed = json.loads(llm_response)
            entities_data = parsed.get("entities", [])
        except json.JSONDecodeError:
            # Handle malformed response
            entities_data = []
        
        # Convert to ExtractedEntity objects
        entities = []
        for data in entities_data:
            entity = ExtractedEntity(
                entity_id=f"ent-{uuid.uuid4().hex[:8]}",
                entity_type=EntityType(data["entityType"]),
                canonical_name=data["canonicalName"],
                properties={
                    k: ExtractedProperty(name=k, **v)
                    for k, v in data.get("properties", {}).items()
                },
                confidence_score=data.get("confidenceScore", 0.8),
                extraction_source=source_id,
                alternative_names=data.get("alternativeNames", [])
            )
            entities.append(entity)
        
        return entities
    
    async def _extract_relationships(
        self,
        source_id: str,
        document_text: str,
        entities: List[ExtractedEntity]
    ) -> List[ExtractedRelationship]:
        """Extract relationships between entities."""
        # Generate prompt
        prompt = self.prompt_template.generate_relationship_extraction_prompt(
            entities, document_text
        )
        
        # Call LLM
        llm_response = await self.llm_client.complete(
            prompt,
            response_format="json",
            temperature=0.1
        )
        
        # Parse and validate response
        try:
            parsed = json.loads(llm_response)
            relationships_data = parsed.get("relationships", [])
        except json.JSONDecodeError:
            relationships_data = []
        
        # Convert to ExtractedRelationship objects
        relationships = []
        for data in relationships_data:
            relationship = ExtractedRelationship(
                relationship_id=f"rel-{uuid.uuid4().hex[:8]}",
                relationship_type=RelationshipType(data["relationshipType"]),
                source_entity_id=data["sourceEntityId"],
                target_entity_id=data["targetEntityId"],
                confidence_score=data.get("confidenceScore", 0.8),
                evidence_text=data.get("evidenceText"),
                extraction_source=source_id
            )
            relationships.append(relationship)
        
        return relationships
    
    async def _perform_alignment(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """Perform semantic alignment against existing ontology."""
        # Get candidate pool from vector store
        candidate_pool = await self._get_candidate_pool(entities)
        
        # Align each entity
        alignment_results = await self.semantic_aligner.align_batch(
            entities, candidate_pool
        )
        
        # Update entity IDs based on alignment
        id_mapping: Dict[str, str] = {}
        for entity, alignment in zip(entities, alignment_results):
            if not alignment.is_new_entity and alignment.aligned_entity_id:
                id_mapping[entity.entity_id] = alignment.aligned_entity_id
                entity.entity_id = alignment.aligned_entity_id
        
        # Update relationship references
        for rel in relationships:
            if rel.source_entity_id in id_mapping:
                rel.source_entity_id = id_mapping[rel.source_entity_id]
            if rel.target_entity_id in id_mapping:
                rel.target_entity_id = id_mapping[rel.target_entity_id]
        
        return entities, relationships
    
    async def _get_candidate_pool(
        self,
        entities: List[ExtractedEntity]
    ) -> List[AlignmentCandidate]:
        """Retrieve candidate entities from vector store for alignment."""
        # In production, query vector store for similar entities
        # Placeholder implementation
        return []
    
    def _resolve_coreferences(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """Resolve coreferences and merge duplicate entities."""
        clusters = self.coreference_resolver.resolve_coreferences(
            entities, relationships
        )
        
        # Build entity ID mapping from clusters
        id_mapping: Dict[str, str] = {}
        for cluster in clusters:
            for member_id in cluster.member_entity_ids:
                if member_id != cluster.canonical_entity_id:
                    id_mapping[member_id] = cluster.canonical_entity_id
        
        # Remove duplicate entities
        canonical_ids = set()
        filtered_entities = []
        for entity in entities:
            if entity.entity_id not in id_mapping:
                canonical_ids.add(entity.entity_id)
                filtered_entities.append(entity)
        
        # Update relationship references
        for rel in relationships:
            if rel.source_entity_id in id_mapping:
                rel.source_entity_id = id_mapping[rel.source_entity_id]
            if rel.target_entity_id in id_mapping:
                rel.target_entity_id = id_mapping[rel.target_entity_id]
        
        return filtered_entities, relationships


import uuid as uuid_module  # noqa: E402

uuid = uuid_module
