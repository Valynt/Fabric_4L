# Value Fabric SaaS Platform - Backend Logic Specifications
## Transforming the Graph into a Normalized Value Tree

---

## 1. VALUE TREE DATA MODEL

### 1.1 Node Type Definitions

#### 1.1.1 Capability Node (Base Layer)
```
Node Type: :Capability

Properties:
- capability_id: UUID (PK)
- name: String (required, unique within tenant)
- description: Text
- category: Enum [
    "DATA_PROCESSING",
    "AUTOMATION",
    "SECURITY",
    "ANALYTICS",
    "INTEGRATION",
    "COLLABORATION",
    "INFRASTRUCTURE"
  ]
- technical_specs: Map<String, String>
- source_document_ids: List<UUID>
- confidence_score: Float (0.0-1.0)
- extraction_metadata: JSON
- tenant_id: UUID (FK)
- created_at: Timestamp
- updated_at: Timestamp
- status: Enum ["DRAFT", "VALIDATED", "DEPRECATED", "ARCHIVED"]

Constraints:
- name + tenant_id must be unique
- confidence_score >= 0.0 AND <= 1.0
- Must have at least one :ENABLES relationship to UseCase OR marked as "ORPHAN"
```

#### 1.1.2 Use Case Node (Layer 2)
```
Node Type: :UseCase

Properties:
- use_case_id: UUID (PK)
- name: String (required, unique within tenant)
- description: Text
- operational_context: String
- industry_vertical: Enum [...]
- business_process: String
- required_capabilities: List<UUID> (derived from edges)
- automation_level: Enum ["FULLY_AUTOMATED", "SEMI_AUTOMATED", "ASSISTED", "MANUAL"]
- workflow_description: Text
- source_document_ids: List<UUID>
- confidence_score: Float (0.0-1.0)
- tenant_id: UUID (FK)
- created_at: Timestamp
- updated_at: Timestamp
- status: Enum ["DRAFT", "VALIDATED", "DEPRECATED", "ARCHIVED"]

Constraints:
- Must have at least one :ENABLES relationship from Capability
- Must have at least one :BENEFITS relationship to Persona
```

#### 1.1.3 Persona Node (Layer 3)
```
Node Type: :Persona

Properties:
- persona_id: UUID (PK)
- name: String (required, unique within tenant)
- role_type: Enum ["OPERATIONAL_USER", "ECONOMIC_BUYER", "TECHNICAL_EVALUATOR", "CHAMPION"]
- department: String
- seniority_level: Enum ["C_LEVEL", "VP", "DIRECTOR", "MANAGER", "INDIVIDUAL_CONTRIBUTOR"]
- job_title_variants: List<String>
- pain_points: List<Text>
- success_metrics: List<String>
- decision_making_authority: Enum ["FINAL", "INFLUENCER", "USER"]
- source_document_ids: List<UUID>
- confidence_score: Float (0.0-1.0)
- tenant_id: UUID (FK)
- created_at: Timestamp
- updated_at: Timestamp
- status: Enum ["DRAFT", "VALIDATED", "DEPRECATED", "ARCHIVED"]

Constraints:
- Must have at least one :BENEFITS relationship from UseCase
- Must have at least one :DRIVES relationship to ValueDriver
```

#### 1.1.4 Value Driver Node (Apex Layer)
```
Node Type: :ValueDriver

Properties:
- value_driver_id: UUID (PK)
- name: String (required, unique within tenant)
- description: Text
- category: Enum [
    "REVENUE_ENHANCEMENT",
    "COST_REDUCTION",
    "RISK_MITIGATION",
    "CAPITAL_EFFICIENCY"
  ]
- sub_category: String
- quantification_method: Enum ["FORMULA", "BENCHMARK", "ESTIMATED", "QUALITATIVE"]
- default_formula_id: UUID (FK to FormulaNode, optional)
- unit_of_measure: String
- typical_range_min: Float
- typical_range_max: Float
- industry_benchmarks: Map<String, Float>
- kpis: List<String>
- source_document_ids: List<UUID>
- confidence_score: Float (0.0-1.0)
- tenant_id: UUID (FK)
- created_at: Timestamp
- updated_at: Timestamp
- status: Enum ["DRAFT", "VALIDATED", "DEPRECATED", "ARCHIVED"]

Constraints:
- Must have at least one :DRIVES relationship from Persona
- category must be one of the four canonical types
```

### 1.2 Edge Type Definitions

#### 1.2.1 Capability -> UseCase (:ENABLES)
```
Edge Type: :ENABLES

Source: :Capability
Target: :UseCase

Properties:
- relationship_id: UUID (PK)
- enablement_type: Enum ["REQUIRED", "ENHANCES", "OPTIONAL"]
- contribution_weight: Float (0.0-1.0) - for multi-capability use cases
- evidence_quote: Text - excerpt from source document
- confidence_score: Float (0.0-1.0)
- extracted_by: String (model/agent identifier)
- tenant_id: UUID (FK)
- created_at: Timestamp

Constraints:
- No duplicate edges between same Capability-UseCase pair
- contribution_weight sum per UseCase should equal 1.0 (validated on write)
```

#### 1.2.2 UseCase -> Persona (:BENEFITS)
```
Edge Type: :BENEFITS

Source: :UseCase
Target: :Persona

Properties:
- relationship_id: UUID (PK)
- benefit_type: Enum ["TIME_SAVINGS", "ERROR_REDUCTION", "VISIBILITY", "COMPLIANCE", "DECISION_SUPPORT"]
- impact_level: Enum ["TRANSFORMATIONAL", "SIGNIFICANT", "MODERATE", "MINOR"]
- time_allocation_impact: Float (percentage of time affected)
- evidence_quote: Text
- confidence_score: Float (0.0-1.0)
- extracted_by: String
- tenant_id: UUID (FK)
- created_at: Timestamp

Constraints:
- No duplicate edges between same UseCase-Persona pair
```

#### 1.2.3 Persona -> ValueDriver (:DRIVES)
```
Edge Type: :DRIVES

Source: :Persona
Target: :ValueDriver

Properties:
- relationship_id: UUID (PK)
- driver_type: Enum ["PRIMARY", "SECONDARY", "TERTIARY"]
- influence_weight: Float (0.0-1.0)
- evidence_quote: Text
- confidence_score: Float (0.0-1.0)
- extracted_by: String
- tenant_id: UUID (FK)
- created_at: Timestamp

Constraints:
- No duplicate edges between same Persona-ValueDriver pair
- Each Persona must drive at least one ValueDriver
```

#### 1.2.4 Cross-Layer Direct (:CONTRIBUTES_TO)
```
Edge Type: :CONTRIBUTES_TO (for direct capability-to-value links)

Source: :Capability OR :UseCase
Target: :ValueDriver

Properties:
- relationship_id: UUID (PK)
- contribution_path: String (description of indirect contribution)
- bypassed_layers: Integer (count of skipped layers)
- confidence_score: Float (0.0-1.0)
- requires_validation: Boolean
- tenant_id: UUID (FK)
- created_at: Timestamp

Constraints:
- Should be used sparingly, primarily for inferred relationships
- Requires manual validation if confidence_score < 0.7
```

### 1.3 Hierarchical Traversal Patterns

#### 1.3.1 Bottom-Up Traversal (Capability -> Value Driver)
```cypher
// Cypher Query Pattern for Neo4j
MATCH path = (c:Capability)-[:ENABLES]->(u:UseCase)-[:BENEFITS]->(p:Persona)-[:DRIVES]->(v:ValueDriver)
WHERE c.tenant_id = $tenant_id AND c.capability_id = $capability_id
RETURN 
    c.name as capability,
    collect(DISTINCT {
        use_case: u.name,
        personas: collect(DISTINCT {
            persona: p.name,
            value_drivers: collect(DISTINCT v.name)
        })
    }) as value_tree_paths
```

#### 1.3.2 Top-Down Traversal (Value Driver -> Capabilities)
```cypher
MATCH path = (v:ValueDriver)<-[:DRIVES]-(p:Persona)<-[:BENEFITS]-(u:UseCase)<-[:ENABLES]-(c:Capability)
WHERE v.tenant_id = $tenant_id AND v.value_driver_id = $value_driver_id
RETURN 
    v.name as value_driver,
    collect(DISTINCT {
        persona: p.name,
        use_cases: collect(DISTINCT {
            use_case: u.name,
            capabilities: collect(DISTINCT c.name)
        })
    }) as supporting_capabilities
```

#### 1.3.3 Cross-Layer Impact Analysis
```cypher
// Find all paths from a set of capabilities to value drivers
MATCH path = (c:Capability)-[:ENABLES|BENEFITS|DRIVES*1..6]->(v:ValueDriver)
WHERE c.tenant_id = $tenant_id 
  AND c.capability_id IN $capability_ids
  AND v.category IN $value_categories
RETURN 
    c.name as starting_capability,
    v.name as impacted_value_driver,
    v.category as value_category,
    length(path) as path_length,
    [node in nodes(path) | node.name] as path_nodes
ORDER BY path_length
```

### 1.4 Tree Integrity Validation Rules

#### 1.4.1 Structural Validation
```python
class TreeIntegrityValidator:
    """
    Validation rules for Value Tree structural integrity
    """
    
    VALIDATION_RULES = {
        "capability_orphan_check": {
            "description": "Capabilities must enable at least one UseCase",
            "severity": "WARNING",
            "cypher": """
                MATCH (c:Capability)
                WHERE c.tenant_id = $tenant_id
                AND NOT (c)-[:ENABLES]->(:UseCase)
                AND c.status = 'VALIDATED'
                RETURN c.capability_id as orphan_id, c.name as orphan_name
            """
        },
        
        "use_case_connectivity": {
            "description": "UseCases must have at least one inbound Capability and one outbound Persona",
            "severity": "ERROR",
            "cypher": """
                MATCH (u:UseCase)
                WHERE u.tenant_id = $tenant_id
                AND (NOT (u)<-[:ENABLES]-(:Capability) 
                     OR NOT (u)-[:BENEFITS]->(:Persona))
                RETURN u.use_case_id as disconnected_id, u.name as disconnected_name
            """
        },
        
        "persona_value_link": {
            "description": "Personas must drive at least one ValueDriver",
            "severity": "ERROR",
            "cypher": """
                MATCH (p:Persona)
                WHERE p.tenant_id = $tenant_id
                AND NOT (p)-[:DRIVES]->(:ValueDriver)
                RETURN p.persona_id as unlinked_id, p.name as unlinked_name
            """
        },
        
        "circular_reference_check": {
            "description": "No circular references allowed in the hierarchy",
            "severity": "CRITICAL",
            "cypher": """
                MATCH path = (n)-[:ENABLES|BENEFITS|DRIVES*]->(n)
                WHERE n.tenant_id = $tenant_id
                RETURN [node in nodes(path) | node.name] as circular_path
            """
        },
        
        "weight_normalization": {
            "description": "Contribution weights for multi-capability use cases must sum to 1.0",
            "severity": "WARNING",
            "cypher": """
                MATCH (u:UseCase)<-[e:ENABLES]-(:Capability)
                WHERE u.tenant_id = $tenant_id
                WITH u, sum(e.contribution_weight) as total_weight
                WHERE abs(total_weight - 1.0) > 0.01
                RETURN u.use_case_id, u.name, total_weight
            """
        }
    }
```

#### 1.4.2 Semantic Validation
```python
class SemanticValidator:
    """
    Validation for semantic consistency across the Value Tree
    """
    
    def validate_capability_use_case_alignment(self, capability_id: UUID, use_case_id: UUID) -> ValidationResult:
        """
        Validate that a capability logically enables a use case
        """
        capability = self.get_capability(capability_id)
        use_case = self.get_use_case(use_case_id)
        
        # Check category alignment
        category_rules = {
            "DATA_PROCESSING": ["analytics", "reporting", "processing", "ingestion"],
            "AUTOMATION": ["automated", "touchless", "workflow", "orchestration"],
            "SECURITY": ["access control", "encryption", "compliance", "protection"],
            "ANALYTICS": ["insights", "forecasting", "prediction", "analysis"],
            "INTEGRATION": ["connect", "sync", "unify", "integrate"],
            "COLLABORATION": ["share", "collaborate", "communicate", "coordinate"],
            "INFRASTRUCTURE": ["scale", "deploy", "host", "infrastructure"]
        }
        
        expected_keywords = category_rules.get(capability.category, [])
        use_case_text = f"{use_case.name} {use_case.description}".lower()
        
        keyword_matches = [kw for kw in expected_keywords if kw in use_case_text]
        confidence = len(keyword_matches) / len(expected_keywords) if expected_keywords else 0.5
        
        return ValidationResult(
            is_valid=confidence >= 0.3,
            confidence=confidence,
            message=f"Category alignment confidence: {confidence:.2f}"
        )
```

---

## 2. CANONICAL DATA MODEL (CDM)

### 2.1 Entity Normalization Rules

#### 2.1.1 Normalization Configuration Schema
```yaml
# CDM Configuration File Format
cdm_version: "1.0.0"
tenant_id: "uuid"

entity_types:
  - name: "Account"
    canonical_form: "Account"
    description: "A business entity that purchases or uses services"
    synonyms:
      - "Customer"
      - "Client"
      - "Subscriber"
      - "End User"
      - "Organization"
      - "Company"
      - "Enterprise"
      - "Business"
    normalization_rules:
      - rule_type: "case_insensitive"
      - rule_type: "strip_prefixes"
        prefixes: ["the", "a", "an"]
      - rule_type: "strip_suffixes"
        suffixes: ["inc.", "llc", "corp.", "ltd."]
    validation_pattern: "^[A-Za-z0-9\\s\\-&.]+$"
    
  - name: "Invoice"
    canonical_form: "Invoice"
    description: "A bill for goods or services"
    synonyms:
      - "Bill"
      - "Statement"
      - "Charge"
      - "Billing Document"
      - "Payment Request"
    normalization_rules:
      - rule_type: "singularize"
    
  - name: "Payment"
    canonical_form: "Payment"
    description: "A financial transaction"
    synonyms:
      - "Transaction"
      - "Remittance"
      - "Settlement"
      - "Funds Transfer"
      - "Disbursement"

attribute_mappings:
  - source_attribute: "cust_name"
    target_attribute: "account_name"
    entity_type: "Account"
    
  - source_attribute: "client_id"
    target_attribute: "account_id"
    entity_type: "Account"
```

#### 2.1.2 Normalization Engine Logic
```python
from typing import List, Dict, Optional, Callable
import re
from dataclasses import dataclass
from enum import Enum

class NormalizationRuleType(Enum):
    CASE_INSENSITIVE = "case_insensitive"
    STRIP_PREFIXES = "strip_prefixes"
    STRIP_SUFFIXES = "strip_suffixes"
    SINGULARIZE = "singularize"
    STEMMING = "stemming"
    REMOVE_SPECIAL_CHARS = "remove_special_chars"
    STANDARDIZE_ABBREVIATIONS = "standardize_abbreviations"

@dataclass
class NormalizationRule:
    rule_type: NormalizationRuleType
    parameters: Dict[str, any]
    priority: int = 0

@dataclass
class CanonicalEntity:
    entity_type: str
    canonical_form: str
    original_forms: List[str]
    confidence_score: float
    source_context: Dict[str, any]

class NormalizationEngine:
    """
    Core normalization engine for CDM
    """
    
    def __init__(self, cdm_config: Dict):
        self.config = cdm_config
        self.synonym_index = self._build_synonym_index()
        self.rule_handlers = self._register_rule_handlers()
    
    def _build_synonym_index(self) -> Dict[str, str]:
        """Build inverted index for synonym lookup"""
        index = {}
        for entity_type in self.config["entity_types"]:
            canonical = entity_type["canonical_form"].lower()
            for synonym in entity_type["synonyms"]:
                index[synonym.lower()] = canonical
            index[canonical] = canonical
        return index
    
    def _register_rule_handlers(self) -> Dict[NormalizationRuleType, Callable]:
        """Register handlers for each normalization rule type"""
        return {
            NormalizationRuleType.CASE_INSENSITIVE: self._apply_case_insensitive,
            NormalizationRuleType.STRIP_PREFIXES: self._apply_strip_prefixes,
            NormalizationRuleType.STRIP_SUFFIXES: self._apply_strip_suffixes,
            NormalizationRuleType.SINGULARIZE: self._apply_singularize,
            NormalizationRuleType.STEMMING: self._apply_stemming,
            NormalizationRuleType.REMOVE_SPECIAL_CHARS: self._apply_remove_special_chars,
            NormalizationRuleType.STANDARDIZE_ABBREVIATIONS: self._apply_standardize_abbreviations,
        }
    
    def normalize(self, raw_text: str, entity_type_hint: Optional[str] = None) -> CanonicalEntity:
        """
        Main normalization entry point
        """
        original = raw_text
        normalized = raw_text.lower().strip()
        
        # Apply entity-type-specific rules if hint provided
        if entity_type_hint:
            entity_config = self._get_entity_config(entity_type_hint)
            if entity_config:
                for rule in sorted(entity_config.get("normalization_rules", []), 
                                   key=lambda r: r.get("priority", 0)):
                    handler = self.rule_handlers.get(NormalizationRuleType(rule["rule_type"]))
                    if handler:
                        normalized = handler(normalized, rule.get("parameters", {}))
        
        # Look up in synonym index
        canonical_form = self.synonym_index.get(normalized, normalized)
        
        # Calculate confidence based on match quality
        confidence = self._calculate_confidence(original, canonical_form)
        
        return CanonicalEntity(
            entity_type=entity_type_hint or "UNKNOWN",
            canonical_form=canonical_form,
            original_forms=[original],
            confidence_score=confidence,
            source_context={}
        )
    
    def _apply_case_insensitive(self, text: str, params: Dict) -> str:
        return text.lower()
    
    def _apply_strip_prefixes(self, text: str, params: Dict) -> str:
        prefixes = params.get("prefixes", [])
        for prefix in prefixes:
            if text.startswith(prefix.lower() + " "):
                text = text[len(prefix) + 1:]
        return text
    
    def _apply_strip_suffixes(self, text: str, params: Dict) -> str:
        suffixes = params.get("suffixes", [])
        for suffix in suffixes:
            if text.endswith(" " + suffix.lower()):
                text = text[:-(len(suffix) + 1)]
        return text
    
    def _apply_singularize(self, text: str, params: Dict) -> str:
        # Simple singularization rules
        if text.endswith("ies"):
            return text[:-3] + "y"
        elif text.endswith("es") and not text.endswith("sses"):
            return text[:-2]
        elif text.endswith("s") and not text.endswith("ss"):
            return text[:-1]
        return text
    
    def _apply_stemming(self, text: str, params: Dict) -> str:
        # Integration with Porter Stemmer or similar
        from nltk.stem import PorterStemmer
        ps = PorterStemmer()
        return ps.stem(text)
    
    def _apply_remove_special_chars(self, text: str, params: Dict) -> str:
        return re.sub(r'[^a-z0-9\\s]', '', text)
    
    def _apply_standardize_abbreviations(self, text: str, params: Dict) -> str:
        abbreviations = params.get("abbreviations", {})
        for abbr, full in abbreviations.items():
            text = text.replace(abbr.lower(), full.lower())
        return text
    
    def _calculate_confidence(self, original: str, canonical: str) -> float:
        """Calculate confidence score for normalization"""
        if original.lower().strip() == canonical:
            return 1.0
        # Simple string similarity - could use more sophisticated methods
        from difflib import SequenceMatcher
        return SequenceMatcher(None, original.lower(), canonical).ratio()
```

### 2.2 Synonym Resolution Logic

#### 2.2.1 Synonym Resolution Service
```python
from typing import Set, Tuple
import numpy as np

class SynonymResolver:
    """
    Advanced synonym resolution using embedding similarity and context
    """
    
    def __init__(self, embedding_model, similarity_threshold: float = 0.85):
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.context_cache = {}
    
    def resolve_synonyms(self, term: str, context: Dict) -> List[Tuple[str, float]]:
        """
        Resolve potential synonyms for a given term
        Returns list of (canonical_form, confidence) tuples
        """
        # Get embedding for input term
        term_embedding = self.embedding_model.encode(term)
        
        # Query synonym database for candidates
        candidates = self._get_candidate_synonyms(term, context)
        
        results = []
        for candidate in candidates:
            candidate_embedding = self.embedding_model.encode(candidate)
            similarity = self._cosine_similarity(term_embedding, candidate_embedding)
            
            # Boost score based on context match
            context_boost = self._calculate_context_boost(term, candidate, context)
            final_score = min(1.0, similarity * (1 + context_boost))
            
            if final_score >= self.similarity_threshold:
                results.append((candidate, final_score))
        
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def _calculate_context_boost(self, term: str, candidate: str, context: Dict) -> float:
        """Calculate context-based confidence boost"""
        boost = 0.0
        
        # Check industry context
        if context.get("industry"):
            industry_terms = self._get_industry_terms(context["industry"])
            if term in industry_terms and candidate in industry_terms:
                boost += 0.1
        
        # Check document type context
        if context.get("document_type"):
            doc_type_boosts = {
                "technical_spec": 0.05,
                "marketing": 0.03,
                "case_study": 0.08
            }
            boost += doc_type_boosts.get(context["document_type"], 0)
        
        return boost
    
    def batch_resolve(self, terms: List[str], context: Dict) -> Dict[str, List[Tuple[str, float]]]:
        """Batch process synonym resolution"""
        return {term: self.resolve_synonyms(term, context) for term in terms}
```

### 2.3 Cross-Source Mapping Procedures

#### 2.3.1 Source Mapping Configuration
```python
@dataclass
class SourceMapping:
    source_system: str
    source_entity: str
    source_attributes: Dict[str, str]
    target_entity: str
    transformation_rules: List[Dict]
    validation_rules: List[Dict]
    conflict_resolution: str  # "source_priority", "target_priority", "manual_review"

class CrossSourceMapper:
    """
    Manages mapping between different source systems to CDM
    """
    
    def __init__(self, mapping_registry: List[SourceMapping]):
        self.mappings = {m.source_system: m for m in mapping_registry}
    
    def map_record(self, source_system: str, record: Dict) -> CanonicalEntity:
        """Map a record from source system to canonical form"""
        mapping = self.mappings.get(source_system)
        if not mapping:
            raise ValueError(f"No mapping defined for source system: {source_system}")
        
        # Apply attribute transformations
        transformed = self._apply_transformations(record, mapping.transformation_rules)
        
        # Normalize entity type
        entity_type = self._normalize_entity_type(mapping.target_entity)
        
        # Create canonical entity
        return CanonicalEntity(
            entity_type=entity_type,
            canonical_form=transformed.get("canonical_name", ""),
            original_forms=[record.get(k) for k in mapping.source_attributes.keys()],
            confidence_score=self._calculate_mapping_confidence(record, transformed),
            source_context={
                "source_system": source_system,
                "source_entity": mapping.source_entity,
                "transformation_applied": True
            }
        )
    
    def _apply_transformations(self, record: Dict, rules: List[Dict]) -> Dict:
        """Apply transformation rules to source record"""
        result = record.copy()
        for rule in rules:
            rule_type = rule.get("type")
            if rule_type == "concatenate":
                fields = rule.get("fields", [])
                separator = rule.get("separator", " ")
                result[rule["target"]] = separator.join(
                    str(record.get(f, "")) for f in fields
                )
            elif rule_type == "map_values":
                value_map = rule.get("value_map", {})
                source_val = record.get(rule["source"])
                result[rule["target"]] = value_map.get(source_val, source_val)
            elif rule_type == "derive":
                formula = rule.get("formula")
                result[rule["target"]] = self._evaluate_formula(formula, record)
        return result
```

### 2.4 CDM Schema Definitions

#### 2.4.1 Core CDM Schema (Graph Model)
```cypher
// CDM Entity Node Schema
CREATE CONSTRAINT cdm_entity_id IF NOT EXISTS
FOR (e:CDMEntity) REQUIRE e.entity_id IS UNIQUE;

CREATE CONSTRAINT cdm_entity_canonical IF NOT EXISTS
FOR (e:CDMEntity) REQUIRE (e.tenant_id, e.entity_type, e.canonical_form) IS UNIQUE;

// CDM Synonym Node Schema
CREATE CONSTRAINT cdm_synonym_id IF NOT EXISTS
FOR (s:CDMSynonym) REQUIRE s.synonym_id IS UNIQUE;

// CDM Source Mapping Node Schema
CREATE CONSTRAINT cdm_source_mapping_id IF NOT EXISTS
FOR (sm:CDMSourceMapping) REQUIRE sm.mapping_id IS UNIQUE;

// Indexes for performance
CREATE INDEX cdm_entity_type_idx IF NOT EXISTS
FOR (e:CDMEntity) ON (e.entity_type);

CREATE INDEX cdm_entity_tenant_idx IF NOT EXISTS
FOR (e:CDMEntity) ON (e.tenant_id);

CREATE INDEX cdm_synonym_text_idx IF NOT EXISTS
FOR (s:CDMSynonym) ON (s.original_text);
```

#### 2.4.2 CDM Node Properties
```
Node Type: :CDMEntity

Properties:
- entity_id: UUID (PK)
- tenant_id: UUID (FK)
- entity_type: String (required)
- canonical_form: String (required)
- display_name: String
- description: Text
- metadata: JSON
- created_at: Timestamp
- updated_at: Timestamp
- version: Integer

Node Type: :CDMSynonym

Properties:
- synonym_id: UUID (PK)
- tenant_id: UUID (FK)
- original_text: String (required)
- normalized_text: String
- entity_type_hint: String
- confidence_score: Float
- source_system: String
- frequency_count: Integer
- created_at: Timestamp

Node Type: :CDMSourceMapping

Properties:
- mapping_id: UUID (PK)
- tenant_id: UUID (FK)
- source_system: String (required)
- source_entity: String (required)
- source_schema: JSON
- target_entity: String (required)
- transformation_rules: JSON
- active: Boolean
- created_at: Timestamp
- updated_at: Timestamp

Edge Type: :HAS_SYNONYM
Source: :CDMEntity
Target: :CDMSynonym
Properties:
- mapping_confidence: Float
- verified: Boolean

Edge Type: :MAPS_TO
Source: :CDMSourceMapping
Target: :CDMEntity
Properties:
- mapping_rule: JSON
- active: Boolean
```

---

## 3. MATHEMATICAL LOGIC ENCODING

### 3.1 Formula Node Structures

#### 3.1.1 Formula Node Schema
```
Node Type: :Formula

Properties:
- formula_id: UUID (PK)
- tenant_id: UUID (FK)
- name: String (required, unique within tenant)
- description: Text
- formula_type: Enum ["ROI", "NPV", "IRR", "CUSTOM", "BENCHMARK"]
- representation_format: Enum ["STRING_EXPRESSION", "OPENMATH", "MATHML", "JSON_TREE"]
- 
# For STRING_EXPRESSION format:
- expression_string: String
  Example: "({Incremental_Revenue} - {Implementation_Cost}) / {Implementation_Cost} * 100"
  
# For OPENMATH format:
- openmath_xml: XML/String
  Example: 
    <OMOBJ>
      <OMA>
        <OMS cd="arith1" name="times"/>
        <OMA>
          <OMS cd="arith1" name="divide"/>
          <OMA>
            <OMS cd="arith1" name="minus"/>
            <OMV name="Incremental_Revenue"/>
            <OMV name="Implementation_Cost"/>
          </OMA>
          <OMV name="Implementation_Cost"/>
        </OMA>
        <OMI>100</OMI>
      </OMA>
    </OMOBJ>

# For JSON_TREE format:
- expression_tree: JSON
  Example:
    {
      "operator": "multiply",
      "operands": [
        {
          "operator": "divide",
          "operands": [
            {
              "operator": "subtract",
              "operands": [
                {"variable": "Incremental_Revenue"},
                {"variable": "Implementation_Cost"}
              ]
            },
            {"variable": "Implementation_Cost"}
          ]
        },
        {"constant": 100}
      ]
    }

- unit_of_result: String
- precision: Integer (decimal places)
- valid_range_min: Float
- valid_range_max: Float
- required_variables: List<String>
- default_values: Map<String, Float>
- metadata: JSON
- created_at: Timestamp
- updated_at: Timestamp
- version: Integer
- status: Enum ["DRAFT", "VALIDATED", "DEPRECATED"]
```

#### 3.1.2 Variable Definition Node
```
Node Type: :FormulaVariable

Properties:
- variable_id: UUID (PK)
- tenant_id: UUID (FK)
- variable_name: String (required, unique within tenant)
- display_name: String
- description: Text
- data_type: Enum ["INTEGER", "FLOAT", "CURRENCY", "PERCENTAGE", "BOOLEAN", "STRING"]
- unit_of_measure: String
- default_value: Float
- valid_range_min: Float
- valid_range_max: Float
- source_type: Enum ["USER_INPUT", "DERIVED", "BENCHMARK", "LOOKUP"]
- derivation_formula_id: UUID (FK to Formula, optional)
- lookup_table: String
- validation_rules: JSON
- metadata: JSON
- created_at: Timestamp
- updated_at: Timestamp

Edge Type: :USES_VARIABLE
Source: :Formula
Target: :FormulaVariable
Properties:
- is_required: Boolean
- default_value_override: Float
- position_in_expression: Integer
```

### 3.2 Variable Substitution Mechanisms

#### 3.2.1 Variable Substitution Engine
```python
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

@dataclass
class SubstitutionContext:
    """Context for variable substitution"""
    prospect_data: Dict[str, Any]
    benchmark_data: Dict[str, Any]
    industry_vertical: Optional[str]
    company_size: Optional[str]
    tenant_id: str

class VariableSubstitutionEngine:
    """
    Engine for substituting variables in formula expressions
    """
    
    VARIABLE_PATTERN = re.compile(r'\{([^}]+)\}')
    
    def __init__(self, variable_repository, benchmark_service):
        self.variable_repo = variable_repository
        self.benchmark_service = benchmark_service
    
    def substitute(self, formula: 'FormulaNode', context: SubstitutionContext) -> Dict[str, Any]:
        """
        Substitute all variables in a formula with actual values
        """
        result = {
            "formula_id": formula.formula_id,
            "substituted_expression": None,
            "variable_values": {},
            "missing_variables": [],
            "substitution_confidence": 1.0
        }
        
        # Get all required variables
        variables = self._extract_variables(formula)
        
        substituted_expression = formula.expression_string
        variable_values = {}
        missing_variables = []
        
        for var_name in variables:
            value = self._resolve_variable(var_name, context)
            
            if value is not None:
                variable_values[var_name] = value
                # Replace in expression
                substituted_expression = substituted_expression.replace(
                    f"{{{var_name}}}", str(value)
                )
            else:
                missing_variables.append(var_name)
                # Try to use default value
                var_def = self.variable_repo.get_variable(var_name, context.tenant_id)
                if var_def and var_def.default_value is not None:
                    variable_values[var_name] = var_def.default_value
                    substituted_expression = substituted_expression.replace(
                        f"{{{var_name}}}", str(var_def.default_value)
                    )
                else:
                    result["substitution_confidence"] *= 0.8  # Reduce confidence
        
        result["substituted_expression"] = substituted_expression
        result["variable_values"] = variable_values
        result["missing_variables"] = missing_variables
        
        return result
    
    def _extract_variables(self, formula: 'FormulaNode') -> List[str]:
        """Extract variable names from formula expression"""
        if formula.representation_format == "STRING_EXPRESSION":
            return self.VARIABLE_PATTERN.findall(formula.expression_string)
        elif formula.representation_format == "JSON_TREE":
            return self._extract_from_json_tree(formula.expression_tree)
        return []
    
    def _extract_from_json_tree(self, tree: Dict) -> List[str]:
        """Recursively extract variables from JSON tree"""
        variables = []
        if "variable" in tree:
            variables.append(tree["variable"])
        if "operands" in tree:
            for operand in tree["operands"]:
                variables.extend(self._extract_from_json_tree(operand))
        return variables
    
    def _resolve_variable(self, var_name: str, context: SubstitutionContext) -> Optional[float]:
        """Resolve a single variable value from context"""
        # Priority: prospect_data > benchmark_data > default
        
        if var_name in context.prospect_data:
            return float(context.prospect_data[var_name])
        
        # Check for industry-specific benchmark
        if context.industry_vertical:
            benchmark = self.benchmark_service.get_benchmark(
                var_name, 
                context.industry_vertical,
                context.company_size
            )
            if benchmark:
                return benchmark.value
        
        return None
```

### 3.3 Expression Parsing and Evaluation

#### 3.3.1 Expression Evaluator
```python
import ast
import operator
import math
from typing import Any, Dict

class SafeExpressionEvaluator:
    """
    Safe mathematical expression evaluator
    """
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }
    
    # Allowed functions
    FUNCTIONS = {
        'abs': abs,
        'max': max,
        'min': min,
        'sum': sum,
        'round': round,
        'pow': pow,
        'sqrt': math.sqrt,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'ceil': math.ceil,
        'floor': math.floor,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
    }
    
    # Allowed constants
    CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
    }
    
    def evaluate(self, expression: str, variables: Dict[str, Any] = None) -> float:
        """
        Safely evaluate a mathematical expression
        """
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body, variables or {})
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")
        except Exception as e:
            raise ValueError(f"Evaluation error: {e}")
    
    def _eval_node(self, node: ast.AST, variables: Dict[str, Any]) -> Any:
        """Recursively evaluate AST nodes"""
        
        if isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, variables)
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")
        
        elif isinstance(node, ast.Name):
            name = node.id
            if name in variables:
                return variables[name]
            if name in self.CONSTANTS:
                return self.CONSTANTS[name]
            raise ValueError(f"Unknown variable or constant: {name}")
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name not in self.FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")
            
            args = [self._eval_node(arg, variables) for arg in node.args]
            return self.FUNCTIONS[func_name](*args)
        
        elif isinstance(node, ast.Expression):
            return self._eval_node(node.body, variables)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node)}")
    
    def validate(self, expression: str, expected_variables: List[str]) -> Dict[str, Any]:
        """
        Validate an expression without evaluating
        """
        result = {
            "is_valid": True,
            "errors": [],
            "detected_variables": [],
            "syntax_ok": False
        }
        
        try:
            tree = ast.parse(expression, mode='eval')
            result["syntax_ok"] = True
            
            # Extract variables
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id not in self.FUNCTIONS and node.id not in self.CONSTANTS:
                        result["detected_variables"].append(node.id)
            
            # Check for undefined variables
            undefined = set(result["detected_variables"]) - set(expected_variables)
            if undefined:
                result["is_valid"] = False
                result["errors"].append(f"Undefined variables: {undefined}")
            
        except SyntaxError as e:
            result["is_valid"] = False
            result["errors"].append(f"Syntax error: {e}")
        
        return result
```

### 3.4 OpenMath/MathML Integration Patterns

#### 3.4.1 OpenMath Parser/Generator
```python
from xml.etree import ElementTree as ET
from typing import Union

class OpenMathConverter:
    """
    Convert between OpenMath XML and internal representation
    """
    
    CD_MAP = {
        "arith1": {
            "plus": "+",
            "minus": "-",
            "times": "*",
            "divide": "/",
            "power": "**",
        },
        "relation1": {
            "eq": "==",
            "neq": "!=",
            "lt": "<",
            "gt": ">",
            "leq": "<=",
            "geq": ">=",
        },
        "logic1": {
            "and": "and",
            "or": "or",
            "not": "not",
        }
    }
    
    def parse_openmath(self, xml_string: str) -> Dict:
        """Parse OpenMath XML to internal JSON tree"""
        root = ET.fromstring(xml_string)
        return self._parse_omobj(root)
    
    def _parse_omobj(self, element: ET.Element) -> Dict:
        """Recursively parse OpenMath elements"""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        if tag == "OMOBJ":
            return self._parse_omobj(element[0]) if len(element) > 0 else {}
        
        elif tag == "OMA":  # Application (function call)
            children = list(element)
            if len(children) == 0:
                return {}
            
            operator = self._parse_omobj(children[0])
            operands = [self._parse_omobj(child) for child in children[1:]]
            
            return {
                "operator": operator.get("name", "unknown"),
                "operands": operands
            }
        
        elif tag == "OMS":  # Symbol
            cd = element.get("cd", "")
            name = element.get("name", "")
            return {
                "type": "symbol",
                "cd": cd,
                "name": name,
                "operator_symbol": self.CD_MAP.get(cd, {}).get(name)
            }
        
        elif tag == "OMV":  # Variable
            return {
                "type": "variable",
                "name": element.get("name", "")
            }
        
        elif tag == "OMI":  # Integer
            return {
                "type": "constant",
                "value": int(element.text or 0)
            }
        
        elif tag == "OMF":  # Float
            return {
                "type": "constant",
                "value": float(element.get("dec", 0))
            }
        
        return {}
    
    def generate_openmath(self, json_tree: Dict) -> str:
        """Generate OpenMath XML from internal JSON tree"""
        root = ET.Element("OMOBJ")
        self._build_omobj(root, json_tree)
        return ET.tostring(root, encoding='unicode')
    
    def _build_omobj(self, parent: ET.Element, node: Dict):
        """Recursively build OpenMath XML"""
        if "operator" in node:
            # Application
            oma = ET.SubElement(parent, "OMA")
            # Add operator symbol
            oms = ET.SubElement(oma, "OMS")
            oms.set("cd", "arith1")  # Simplified - should map properly
            oms.set("name", node["operator"])
            # Add operands
            for operand in node.get("operands", []):
                self._build_omobj(oma, operand)
        
        elif "variable" in node:
            omv = ET.SubElement(parent, "OMV")
            omv.set("name", node["variable"])
        
        elif "constant" in node:
            value = node["constant"]
            if isinstance(value, int):
                omi = ET.SubElement(parent, "OMI")
                omi.text = str(value)
            else:
                omf = ET.SubElement(parent, "OMF")
                omf.set("dec", str(value))
```

### 3.5 Dynamic Calculation Workflows

#### 3.5.1 Calculation Workflow Engine
```python
from typing import List, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio

class CalculationStepType(Enum):
    VARIABLE_RESOLUTION = "variable_resolution"
    FORMULA_EVALUATION = "formula_evaluation"
    BENCHMARK_LOOKUP = "benchmark_lookup"
    VALIDATION = "validation"
    AGGREGATION = "aggregation"
    FORMATTING = "formatting"

@dataclass
class CalculationStep:
    step_type: CalculationStepType
    step_id: str
    dependencies: List[str]
    config: Dict[str, Any]
    handler: Callable

class CalculationWorkflow:
    """
    Orchestrates multi-step calculation workflows
    """
    
    def __init__(self, workflow_id: str, tenant_id: str):
        self.workflow_id = workflow_id
        self.tenant_id = tenant_id
        self.steps: List[CalculationStep] = []
        self.results: Dict[str, Any] = {}
        self.errors: List[Dict] = []
    
    def add_step(self, step: CalculationStep):
        """Add a calculation step to the workflow"""
        self.steps.append(step)
    
    async def execute(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the calculation workflow
        """
        context = initial_context.copy()
        executed_steps = set()
        
        # Topological sort of steps based on dependencies
        sorted_steps = self._topological_sort()
        
        for step in sorted_steps:
            # Check dependencies
            if not all(dep in executed_steps for dep in step.dependencies):
                self.errors.append({
                    "step_id": step.step_id,
                    "error": f"Dependencies not met: {step.dependencies}"
                })
                continue
            
            try:
                # Execute step
                result = await step.handler(context, step.config)
                self.results[step.step_id] = result
                context[f"step_{step.step_id}_result"] = result
                executed_steps.add(step.step_id)
                
            except Exception as e:
                self.errors.append({
                    "step_id": step.step_id,
                    "error": str(e)
                })
                
                # Decide whether to continue or abort
                if step.config.get("abort_on_error", True):
                    break
        
        return {
            "workflow_id": self.workflow_id,
            "results": self.results,
            "errors": self.errors,
            "success": len(self.errors) == 0
        }
    
    def _topological_sort(self) -> List[CalculationStep]:
        """Sort steps based on dependencies"""
        # Simple implementation - could use more sophisticated algorithm
        step_map = {s.step_id: s for s in self.steps}
        sorted_steps = []
        visited = set()
        
        def visit(step_id: str):
            if step_id in visited:
                return
            step = step_map.get(step_id)
            if step:
                for dep in step.dependencies:
                    visit(dep)
                sorted_steps.append(step)
                visited.add(step_id)
        
        for step in self.steps:
            visit(step.step_id)
        
        return sorted_steps

# Example workflow definition
class ROICalculationWorkflow:
    """
    Pre-built workflow for ROI calculations
    """
    
    @staticmethod
    def create(formula_id: str, prospect_data: Dict) -> CalculationWorkflow:
        workflow = CalculationWorkflow(
            workflow_id=f"roi_{formula_id}_{int(time.time())}",
            tenant_id=prospect_data.get("tenant_id")
        )
        
        # Step 1: Resolve all variables
        workflow.add_step(CalculationStep(
            step_type=CalculationStepType.VARIABLE_RESOLUTION,
            step_id="resolve_variables",
            dependencies=[],
            config={"formula_id": formula_id},
            handler=VariableResolutionHandler()
        ))
        
        # Step 2: Look up benchmarks for missing variables
        workflow.add_step(CalculationStep(
            step_type=CalculationStepType.BENCHMARK_LOOKUP,
            step_id="lookup_benchmarks",
            dependencies=["resolve_variables"],
            config={"industry": prospect_data.get("industry")},
            handler=BenchmarkLookupHandler()
        ))
        
        # Step 3: Evaluate formula
        workflow.add_step(CalculationStep(
            step_type=CalculationStepType.FORMULA_EVALUATION,
            step_id="evaluate_formula",
            dependencies=["resolve_variables", "lookup_benchmarks"],
            config={"formula_id": formula_id},
            handler=FormulaEvaluationHandler()
        ))
        
        # Step 4: Validate result
        workflow.add_step(CalculationStep(
            step_type=CalculationStepType.VALIDATION,
            step_id="validate_result",
            dependencies=["evaluate_formula"],
            config={},
            handler=ResultValidationHandler()
        ))
        
        # Step 5: Format output
        workflow.add_step(CalculationStep(
            step_type=CalculationStepType.FORMATTING,
            step_id="format_output",
            dependencies=["validate_result"],
            config={"format": "currency"},
            handler=OutputFormattingHandler()
        ))
        
        return workflow
```

---

## 4. NORMALIZATION PIPELINE

### 4.1 Text-to-Entity Extraction Logic

#### 4.1.1 Entity Extraction Pipeline
```python
from typing import Iterator, AsyncIterator
import spacy
from transformers import pipeline

class EntityExtractionPipeline:
    """
    Pipeline for extracting entities from unstructured text
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.nlp = spacy.load(config.get("spacy_model", "en_core_web_lg"))
        self.ner_pipeline = pipeline(
            "ner", 
            model=config.get("ner_model", "dslim/bert-base-NER")
        )
        self.classifier = pipeline(
            "zero-shot-classification",
            model=config.get("classifier_model", "facebook/bart-large-mnli")
        )
    
    async def extract(self, document: 'Document') -> Iterator['ExtractedEntity']:
        """
        Main extraction entry point
        """
        # Stage 1: Preprocess text
        cleaned_text = self._preprocess(document.content)
        
        # Stage 2: Named Entity Recognition
        spacy_entities = self._extract_spacy_entities(cleaned_text)
        transformer_entities = self._extract_transformer_entities(cleaned_text)
        
        # Stage 3: Merge and deduplicate
        merged_entities = self._merge_entities(spacy_entities, transformer_entities)
        
        # Stage 4: Classify into Value Tree layers
        for entity in merged_entities:
            layer_classification = self._classify_layer(entity)
            entity.predicted_layer = layer_classification
            yield entity
    
    def _preprocess(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        return text
    
    def _extract_spacy_entities(self, text: str) -> List['ExtractedEntity']:
        """Extract entities using spaCy NER"""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append(ExtractedEntity(
                text=ent.text,
                start_char=ent.start_char,
                end_char=ent.end_char,
                label=ent.label_,
                source="spacy",
                confidence=0.85  # spaCy doesn't provide confidence by default
            ))
        
        # Also extract noun phrases as potential capabilities
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:  # Multi-word phrases
                entities.append(ExtractedEntity(
                    text=chunk.text,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    label="NOUN_PHRASE",
                    source="spacy_np",
                    confidence=0.70
                ))
        
        return entities
    
    def _extract_transformer_entities(self, text: str) -> List['ExtractedEntity']:
        """Extract entities using transformer-based NER"""
        results = self.ner_pipeline(text)
        entities = []
        
        for result in results:
            entities.append(ExtractedEntity(
                text=result["word"],
                start_char=result["start"],
                end_char=result["end"],
                label=result["entity"],
                source="transformer",
                confidence=result["score"]
            ))
        
        return entities
    
    def _merge_entities(self, *entity_lists: List['ExtractedEntity']) -> List['ExtractedEntity']:
        """Merge and deduplicate entities from multiple sources"""
        all_entities = []
        for entities in entity_lists:
            all_entities.extend(entities)
        
        # Sort by position
        all_entities.sort(key=lambda e: (e.start_char, -e.confidence))
        
        # Remove overlapping entities (keep higher confidence)
        merged = []
        last_end = -1
        for entity in all_entities:
            if entity.start_char >= last_end:
                merged.append(entity)
                last_end = entity.end_char
            elif entity.confidence > merged[-1].confidence:
                # Replace if higher confidence
                merged[-1] = entity
                last_end = entity.end_char
        
        return merged
    
    def _classify_layer(self, entity: 'ExtractedEntity') -> Dict:
        """Classify entity into Value Tree layer"""
        
        # Define layer characteristics
        layer_descriptions = {
            "CAPABILITY": [
                "technical feature", "software function", "system capability",
                "platform service", "technical functionality"
            ],
            "USE_CASE": [
                "business process", "workflow", "operational scenario",
                "use case", "application scenario"
            ],
            "PERSONA": [
                "job role", "professional title", "organizational position",
                "stakeholder", "business role"
            ],
            "VALUE_DRIVER": [
                "business outcome", "financial benefit", "ROI metric",
                "cost savings", "revenue impact"
            ]
        }
        
        # Zero-shot classification
        result = self.classifier(
            entity.text,
            candidate_labels=list(layer_descriptions.keys()),
            hypothesis_template="This text describes a {}."
        )
        
        return {
            "predicted_layer": result["labels"][0],
            "confidence": result["scores"][0],
            "all_scores": dict(zip(result["labels"], result["scores"]))
        }
```

### 4.2 Layer Assignment Algorithms

#### 4.2.1 Layer Assignment Engine
```python
class LayerAssignmentEngine:
    """
    Assigns extracted entities to appropriate Value Tree layers
    """
    
    LAYER_KEYWORDS = {
        "CAPABILITY": {
            "required": ["feature", "function", "capability", "service"],
            "optional": ["real-time", "automated", "advanced", "intelligent"],
            "indicators": ["API", "integration", "processing", "analytics"]
        },
        "USE_CASE": {
            "required": ["process", "workflow", "management"],
            "optional": ["automated", "streamlined", "optimized"],
            "indicators": ["processing", "handling", "orchestration"]
        },
        "PERSONA": {
            "required": [],
            "optional": ["chief", "senior", "lead", "head"],
            "indicators": [
                "officer", "director", "manager", "analyst", "specialist",
                "CFO", "CEO", "CTO", "COO", "VP", "controller"
            ]
        },
        "VALUE_DRIVER": {
            "required": [],
            "optional": ["increased", "decreased", "improved", "reduced"],
            "indicators": [
                "revenue", "cost", "savings", "ROI", "efficiency",
                "productivity", "risk", "compliance", "time-to-market"
            ]
        }
    }
    
    def assign_layer(self, entity: 'ExtractedEntity', context: Dict) -> 'LayerAssignment':
        """
        Assign entity to a Value Tree layer with confidence score
        """
        text_lower = entity.text.lower()
        scores = {}
        
        for layer, keywords in self.LAYER_KEYWORDS.items():
            score = 0.0
            
            # Check required keywords
            if keywords["required"]:
                required_matches = sum(1 for kw in keywords["required"] if kw in text_lower)
                score += (required_matches / len(keywords["required"])) * 0.4
            
            # Check optional keywords
            if keywords["optional"]:
                optional_matches = sum(1 for kw in keywords["optional"] if kw in text_lower)
                score += (optional_matches / len(keywords["optional"])) * 0.3
            
            # Check indicators
            if keywords["indicators"]:
                indicator_matches = sum(1 for kw in keywords["indicators"] if kw in text_lower)
                score += (indicator_matches / len(keywords["indicators"])) * 0.3
            
            # Context boost
            if context.get("document_type") == "technical_spec" and layer == "CAPABILITY":
                score *= 1.2
            elif context.get("document_type") == "case_study" and layer == "VALUE_DRIVER":
                score *= 1.2
            
            scores[layer] = min(1.0, score)
        
        # Get highest scoring layer
        best_layer = max(scores, key=scores.get)
        
        return LayerAssignment(
            entity=entity,
            assigned_layer=best_layer,
            confidence=scores[best_layer],
            all_scores=scores,
            reasoning=self._generate_reasoning(entity, best_layer, scores)
        )
    
    def _generate_reasoning(self, entity: 'ExtractedEntity', layer: str, scores: Dict) -> str:
        """Generate human-readable reasoning for layer assignment"""
        keywords = self.LAYER_KEYWORDS[layer]
        text_lower = entity.text.lower()
        
        matched_keywords = []
        for kw_list in [keywords["required"], keywords["optional"], keywords["indicators"]]:
            matched_keywords.extend([kw for kw in kw_list if kw in text_lower])
        
        return f"Assigned to {layer} based on matched keywords: {', '.join(matched_keywords)}"
```

### 4.3 Relationship Inference Rules

#### 4.3.1 Relationship Inference Engine
```python
class RelationshipInferenceEngine:
    """
    Infers relationships between entities in the Value Tree
    """
    
    def __init__(self, embedding_model, graph_client):
        self.embedding_model = embedding_model
        self.graph = graph_client
    
    def infer_relationships(self, source_entity: 'Entity', 
                           target_layer: str) -> List['InferredRelationship']:
        """
        Infer potential relationships from source entity to target layer
        """
        relationships = []
        
        # Get candidate target entities
        candidates = self._get_candidates(target_layer, source_entity.tenant_id)
        
        # Calculate semantic similarity
        source_embedding = self.embedding_model.encode(
            f"{source_entity.name} {source_entity.description}"
        )
        
        for candidate in candidates:
            candidate_embedding = self.embedding_model.encode(
                f"{candidate.name} {candidate.description}"
            )
            
            similarity = self._cosine_similarity(source_embedding, candidate_embedding)
            
            if similarity >= 0.6:  # Threshold for relationship consideration
                relationship_type = self._determine_relationship_type(
                    source_entity, candidate
                )
                
                relationships.append(InferredRelationship(
                    source=source_entity,
                    target=candidate,
                    relationship_type=relationship_type,
                    confidence=similarity,
                    evidence={"semantic_similarity": similarity}
                ))
        
        # Sort by confidence
        relationships.sort(key=lambda r: r.confidence, reverse=True)
        
        return relationships[:10]  # Return top 10
    
    def _determine_relationship_type(self, source: 'Entity', target: 'Entity') -> str:
        """Determine the type of relationship based on entity layers"""
        layer_order = ["CAPABILITY", "USE_CASE", "PERSONA", "VALUE_DRIVER"]
        
        source_idx = layer_order.index(source.layer)
        target_idx = layer_order.index(target.layer)
        
        if target_idx == source_idx + 1:
            return "DIRECT_HIERARCHICAL"
        elif target_idx > source_idx + 1:
            return "SKIP_LEVEL"
        elif target_idx == source_idx:
            return "SIBLING"
        else:
            return "REVERSE"
    
    def infer_enablement(self, capability: 'Capability', 
                         use_case: 'UseCase') -> 'EnablementInference':
        """
        Infer how a capability enables a use case
        """
        # Analyze text for enablement indicators
        enablement_indicators = [
            "enables", "allows", "supports", "facilitates",
            "powers", "drives", "makes possible"
        ]
        
        combined_text = f"{capability.description} {use_case.description}".lower()
        
        indicator_count = sum(1 for ind in enablement_indicators if ind in combined_text)
        
        # Determine enablement type
        if indicator_count >= 2:
            enablement_type = "REQUIRED"
        elif indicator_count == 1:
            enablement_type = "ENHANCES"
        else:
            enablement_type = "OPTIONAL"
        
        # Calculate contribution weight based on semantic overlap
        capability_embedding = self.embedding_model.encode(capability.description)
        use_case_embedding = self.embedding_model.encode(use_case.description)
        
        semantic_overlap = self._cosine_similarity(capability_embedding, use_case_embedding)
        
        return EnablementInference(
            capability=capability,
            use_case=use_case,
            enablement_type=enablement_type,
            contribution_weight=semantic_overlap,
            confidence=min(1.0, indicator_count * 0.3 + semantic_overlap * 0.7)
        )
```

### 4.4 Quality Validation Checks

#### 4.4.1 Quality Validation Framework
```python
from enum import Enum
from typing import List, Dict
from dataclasses import dataclass

class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    check_name: str
    severity: ValidationSeverity
    passed: bool
    message: str
    details: Dict
    remediation: str

class QualityValidator:
    """
    Comprehensive quality validation for normalized Value Tree
    """
    
    def __init__(self, graph_client, config: Dict):
        self.graph = graph_client
        self.config = config
        self.checks = self._register_checks()
    
    def _register_checks(self) -> Dict:
        """Register all validation checks"""
        return {
            "completeness": self._check_completeness,
            "connectivity": self._check_connectivity,
            "consistency": self._check_consistency,
            "confidence": self._check_confidence,
            "redundancy": self._check_redundancy,
            "orphan_detection": self._check_orphans,
        }
    
    def validate(self, tenant_id: str, scope: str = "full") -> List[ValidationResult]:
        """
        Run all validation checks
        """
        results = []
        
        for check_name, check_func in self.checks.items():
            if scope == "quick" and check_name in ["redundancy"]:
                continue
                
            try:
                result = check_func(tenant_id)
                results.extend(result if isinstance(result, list) else [result])
            except Exception as e:
                results.append(ValidationResult(
                    check_name=check_name,
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Validation check failed with error: {str(e)}",
                    details={"error": str(e)},
                    remediation="Review validation logic"
                ))
        
        return results
    
    def _check_completeness(self, tenant_id: str) -> List[ValidationResult]:
        """Check that all required fields are populated"""
        results = []
        
        # Check Capabilities
        query = """
            MATCH (c:Capability)
            WHERE c.tenant_id = $tenant_id
            AND (c.name IS NULL OR c.description IS NULL OR c.category IS NULL)
            RETURN c.capability_id as id, c.name as name
        """
        incomplete = self.graph.run(query, tenant_id=tenant_id).data()
        
        if incomplete:
            results.append(ValidationResult(
                check_name="capability_completeness",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"{len(incomplete)} capabilities have missing required fields",
                details={"incomplete_capabilities": incomplete[:10]},
                remediation="Run data enrichment pipeline to populate missing fields"
            ))
        
        # Similar checks for other node types...
        
        return results
    
    def _check_connectivity(self, tenant_id: str) -> List[ValidationResult]:
        """Check that the tree is properly connected"""
        results = []
        
        # Check for disconnected subtrees
        query = """
            MATCH (v:ValueDriver)
            WHERE v.tenant_id = $tenant_id
            AND NOT (v)<-[:DRIVES]-(:Persona)
            RETURN v.value_driver_id as id, v.name as name
        """
        disconnected_drivers = self.graph.run(query, tenant_id=tenant_id).data()
        
        if disconnected_drivers:
            results.append(ValidationResult(
                check_name="value_driver_connectivity",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"{len(disconnected_drivers)} value drivers have no connected personas",
                details={"disconnected_drivers": disconnected_drivers[:10]},
                remediation="Review extraction pipeline or manually connect personas"
            ))
        
        return results
    
    def _check_confidence(self, tenant_id: str) -> List[ValidationResult]:
        """Check confidence scores across the tree"""
        results = []
        
        threshold = self.config.get("confidence_threshold", 0.7)
        
        query = """
            MATCH (n)
            WHERE n.tenant_id = $tenant_id
            AND (n:Capability OR n:UseCase OR n:Persona OR n:ValueDriver)
            AND n.confidence_score < $threshold
            RETURN labels(n)[0] as node_type, 
                   count(n) as low_confidence_count
        """
        low_confidence = self.graph.run(query, 
                                       tenant_id=tenant_id, 
                                       threshold=threshold).data()
        
        total_low = sum(item["low_confidence_count"] for item in low_confidence)
        
        if total_low > 0:
            results.append(ValidationResult(
                check_name="confidence_scores",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"{total_low} nodes have confidence below {threshold}",
                details={"breakdown": low_confidence},
                remediation="Review low-confidence extractions for manual validation"
            ))
        
        return results
    
    def _check_orphans(self, tenant_id: str) -> List[ValidationResult]:
        """Detect orphan nodes with no relationships"""
        results = []
        
        query = """
            MATCH (n)
            WHERE n.tenant_id = $tenant_id
            AND (n:Capability OR n:UseCase OR n:Persona OR n:ValueDriver)
            AND NOT (n)-[]-()
            RETURN labels(n)[0] as node_type, 
                   collect(n.name)[:5] as orphan_names,
                   count(n) as orphan_count
        """
        orphans = self.graph.run(query, tenant_id=tenant_id).data()
        
        total_orphans = sum(item["orphan_count"] for item in orphans)
        
        if total_orphans > 0:
            results.append(ValidationResult(
                check_name="orphan_detection",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"{total_orphans} orphan nodes detected",
                details={"orphans": orphans},
                remediation="Run relationship inference or manually connect orphan nodes"
            ))
        
        return results
```

---

## 5. API INTERFACES

### 5.1 Value Tree Construction and Management

#### 5.1.1 REST API Endpoints
```yaml
# OpenAPI Specification for Value Tree API
openapi: 3.0.0
info:
  title: Value Tree API
  version: 1.0.0
  description: API for constructing and managing Value Trees

paths:
  # Capability Endpoints
  /api/v1/tenants/{tenant_id}/capabilities:
    get:
      summary: List all capabilities
      parameters:
        - name: tenant_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: category
          in: query
          schema:
            type: string
            enum: [DATA_PROCESSING, AUTOMATION, SECURITY, ANALYTICS, INTEGRATION, COLLABORATION, INFRASTRUCTURE]
        - name: status
          in: query
          schema:
            type: string
            enum: [DRAFT, VALIDATED, DEPRECATED, ARCHIVED]
      responses:
        200:
          description: List of capabilities
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Capability'
                  pagination:
                    $ref: '#/components/schemas/Pagination'
    
    post:
      summary: Create a new capability
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CapabilityCreate'
      responses:
        201:
          description: Capability created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Capability'
        409:
          description: Capability with this name already exists

  /api/v1/tenants/{tenant_id}/capabilities/{capability_id}:
    get:
      summary: Get a specific capability
      parameters:
        - name: tenant_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: capability_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        200:
          description: Capability details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CapabilityWithRelations'
    
    put:
      summary: Update a capability
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CapabilityUpdate'
      responses:
        200:
          description: Capability updated
    
    delete:
      summary: Delete a capability
      responses:
        204:
          description: Capability deleted

  # Relationship Endpoints
  /api/v1/tenants/{tenant_id}/relationships:
    post:
      summary: Create a relationship between nodes
      requestBody:
        required: true
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/EnablesRelationship'
                - $ref: '#/components/schemas/BenefitsRelationship'
                - $ref: '#/components/schemas/DrivesRelationship'
      responses:
        201:
          description: Relationship created

  # Tree Traversal Endpoints
  /api/v1/tenants/{tenant_id}/value-tree/traverse:
    get:
      summary: Traverse the Value Tree
      parameters:
        - name: tenant_id
          in: path
          required: true
        - name: start_node_id
          in: query
          required: true
          schema:
            type: string
            format: uuid
        - name: direction
          in: query
          required: true
          schema:
            type: string
            enum: [up, down, both]
        - name: max_depth
          in: query
          schema:
            type: integer
            default: 4
            maximum: 10
        - name: include_formulas
          in: query
          schema:
            type: boolean
            default: false
      responses:
        200:
          description: Traversal result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TreeTraversalResult'

  /api/v1/tenants/{tenant_id}/value-tree/impact-analysis:
    post:
      summary: Analyze impact of capabilities on value drivers
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                capability_ids:
                  type: array
                  items:
                    type: string
                    format: uuid
                include_metrics:
                  type: boolean
                  default: true
      responses:
        200:
          description: Impact analysis result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ImpactAnalysisResult'

components:
  schemas:
    Capability:
      type: object
      properties:
        capability_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        category:
          type: string
        confidence_score:
          type: number
          minimum: 0
          maximum: 1
        status:
          type: string
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
    
    CapabilityCreate:
      type: object
      required:
        - name
        - category
      properties:
        name:
          type: string
          maxLength: 255
        description:
          type: string
        category:
          type: string
          enum: [DATA_PROCESSING, AUTOMATION, SECURITY, ANALYTICS, INTEGRATION, COLLABORATION, INFRASTRUCTURE]
        technical_specs:
          type: object
    
    CapabilityWithRelations:
      allOf:
        - $ref: '#/components/schemas/Capability'
        - type: object
          properties:
            enables:
              type: array
              items:
                $ref: '#/components/schemas/UseCaseSummary'
            upstream_value_drivers:
              type: array
              items:
                $ref: '#/components/schemas/ValueDriverSummary'
    
    TreeTraversalResult:
      type: object
      properties:
        start_node:
          type: object
        paths:
          type: array
          items:
            type: object
            properties:
              nodes:
                type: array
              relationships:
                type: array
              depth:
                type: integer
    
    ImpactAnalysisResult:
      type: object
      properties:
        capabilities_analyzed:
          type: integer
        value_drivers_impacted:
          type: array
          items:
            type: object
            properties:
              value_driver:
                $ref: '#/components/schemas/ValueDriver'
              impact_paths:
                type: array
              estimated_value:
                type: number
    
    Pagination:
      type: object
      properties:
        page:
          type: integer
        page_size:
          type: integer
        total:
          type: integer
        total_pages:
          type: integer
```

### 5.2 Formula Definition and Validation

#### 5.2.1 Formula Management API
```yaml
paths:
  /api/v1/tenants/{tenant_id}/formulas:
    get:
      summary: List all formulas
      parameters:
        - name: formula_type
          in: query
          schema:
            type: string
            enum: [ROI, NPV, IRR, CUSTOM, BENCHMARK]
        - name: status
          in: query
          schema:
            type: string
            enum: [DRAFT, VALIDATED, DEPRECATED]
      responses:
        200:
          description: List of formulas
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Formula'

    post:
      summary: Create a new formula
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FormulaCreate'
      responses:
        201:
          description: Formula created
        400:
          description: Invalid formula syntax

  /api/v1/tenants/{tenant_id}/formulas/{formula_id}:
    get:
      summary: Get formula details
      responses:
        200:
          description: Formula details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FormulaWithVariables'

    put:
      summary: Update formula
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FormulaUpdate'
      responses:
        200:
          description: Formula updated

    delete:
      summary: Delete formula
      responses:
        204:
          description: Formula deleted

  /api/v1/tenants/{tenant_id}/formulas/validate:
    post:
      summary: Validate a formula without saving
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                expression_string:
                  type: string
                representation_format:
                  type: string
                  enum: [STRING_EXPRESSION, OPENMATH, MATHML, JSON_TREE]
                expected_variables:
                  type: array
                  items:
                    type: string
      responses:
        200:
          description: Validation result
          content:
            application/json:
              schema:
                type: object
                properties:
                  is_valid:
                    type: boolean
                  errors:
                    type: array
                    items:
                      type: object
                      properties:
                        message:
                          type: string
                        position:
                          type: integer
                  detected_variables:
                    type: array
                    items:
                      type: string

  /api/v1/tenants/{tenant_id}/formulas/{formula_id}/evaluate:
    post:
      summary: Evaluate a formula with provided variable values
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                variable_values:
                  type: object
                  additionalProperties:
                    type: number
                context:
                  type: object
                  properties:
                    industry_vertical:
                      type: string
                    company_size:
                      type: string
      responses:
        200:
          description: Evaluation result
          content:
            application/json:
              schema:
                type: object
                properties:
                  result:
                    type: number
                  unit:
                    type: string
                  substituted_expression:
                    type: string
                  variable_values_used:
                    type: object
                  confidence:
                    type: number

  /api/v1/tenants/{tenant_id}/formulas/variables:
    get:
      summary: List all formula variables
      responses:
        200:
          description: List of variables
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/FormulaVariable'

    post:
      summary: Create a new formula variable
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FormulaVariableCreate'
      responses:
        201:
          description: Variable created

components:
  schemas:
    Formula:
      type: object
      properties:
        formula_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        formula_type:
          type: string
        representation_format:
          type: string
        expression_string:
          type: string
        unit_of_result:
          type: string
        precision:
          type: integer
        status:
          type: string
        version:
          type: integer
    
    FormulaCreate:
      type: object
      required:
        - name
        - representation_format
      properties:
        name:
          type: string
        description:
          type: string
        formula_type:
          type: string
          enum: [ROI, NPV, IRR, CUSTOM, BENCHMARK]
        representation_format:
          type: string
          enum: [STRING_EXPRESSION, OPENMATH, MATHML, JSON_TREE]
        expression_string:
          type: string
        openmath_xml:
          type: string
        expression_tree:
          type: object
        unit_of_result:
          type: string
        precision:
          type: integer
          default: 2
        valid_range_min:
          type: number
        valid_range_max:
          type: number
    
    FormulaVariable:
      type: object
      properties:
        variable_id:
          type: string
          format: uuid
        variable_name:
          type: string
        display_name:
          type: string
        description:
          type: string
        data_type:
          type: string
          enum: [INTEGER, FLOAT, CURRENCY, PERCENTAGE, BOOLEAN, STRING]
        unit_of_measure:
          type: string
        default_value:
          type: number
        valid_range_min:
          type: number
        valid_range_max:
          type: number
        source_type:
          type: string
          enum: [USER_INPUT, DERIVED, BENCHMARK, LOOKUP]
```

### 5.3 Normalization Job Execution

#### 5.3.1 Normalization Pipeline API
```yaml
paths:
  /api/v1/tenants/{tenant_id}/normalization-jobs:
    get:
      summary: List normalization jobs
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [PENDING, RUNNING, COMPLETED, FAILED, CANCELLED]
        - name: job_type
          in: query
          schema:
            type: string
            enum: [EXTRACTION, NORMALIZATION, VALIDATION, FULL_PIPELINE]
      responses:
        200:
          description: List of jobs
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/NormalizationJob'

    post:
      summary: Submit a new normalization job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/ExtractionJobRequest'
                - $ref: '#/components/schemas/FullPipelineJobRequest'
      responses:
        202:
          description: Job accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobSubmissionResponse'

  /api/v1/tenants/{tenant_id}/normalization-jobs/{job_id}:
    get:
      summary: Get job status and results
      responses:
        200:
          description: Job details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NormalizationJobDetail'

    delete:
      summary: Cancel a running job
      responses:
        200:
          description: Job cancelled

  /api/v1/tenants/{tenant_id}/normalization-jobs/{job_id}/results:
    get:
      summary: Get detailed job results
      parameters:
        - name: include_entities
          in: query
          schema:
            type: boolean
            default: false
        - name: include_errors
          in: query
          schema:
            type: boolean
            default: true
      responses:
        200:
          description: Job results
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NormalizationJobResults'

  /api/v1/tenants/{tenant_id}/normalization-jobs/{job_id}/retry:
    post:
      summary: Retry a failed job
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                resume_from_stage:
                  type: string
                override_config:
                  type: object
      responses:
        202:
          description: Retry job accepted

components:
  schemas:
    NormalizationJob:
      type: object
      properties:
        job_id:
          type: string
          format: uuid
        job_type:
          type: string
        status:
          type: string
        progress_percentage:
          type: number
        created_at:
          type: string
          format: date-time
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        created_by:
          type: string
    
    ExtractionJobRequest:
      type: object
      required:
        - job_type
        - source_documents
      properties:
        job_type:
          type: string
          enum: [EXTRACTION]
        source_documents:
          type: array
          items:
            type: object
            properties:
              document_id:
                type: string
                format: uuid
              document_type:
                type: string
                enum: [technical_spec, marketing, case_study, whitepaper]
        extraction_config:
          type: object
          properties:
            extract_capabilities:
              type: boolean
              default: true
            extract_use_cases:
              type: boolean
              default: true
            extract_personas:
              type: boolean
              default: true
            extract_value_drivers:
              type: boolean
              default: true
            confidence_threshold:
              type: number
              default: 0.7
    
    FullPipelineJobRequest:
      type: object
      required:
        - job_type
        - source_documents
      properties:
        job_type:
          type: string
          enum: [FULL_PIPELINE]
        source_documents:
          type: array
          items:
            type: object
        pipeline_config:
          type: object
          properties:
            stages:
              type: array
              items:
                type: string
                enum: [EXTRACTION, NORMALIZATION, RELATIONSHIP_INFERENCE, VALIDATION]
            auto_approve_confident_extractions:
              type: boolean
              default: false
            confidence_threshold:
              type: number
              default: 0.8
    
    NormalizationJobDetail:
      allOf:
        - $ref: '#/components/schemas/NormalizationJob'
        - type: object
          properties:
            stages:
              type: array
              items:
                type: object
                properties:
                  stage_name:
                    type: string
                  status:
                    type: string
                  started_at:
                    type: string
                    format: date-time
                  completed_at:
                    type: string
                    format: date-time
                  progress:
                    type: number
                  metrics:
                    type: object
            current_stage:
              type: string
            error_details:
              type: object
    
    NormalizationJobResults:
      type: object
      properties:
        job_id:
          type: string
        summary:
          type: object
          properties:
            entities_extracted:
              type: integer
            entities_normalized:
              type: integer
            relationships_inferred:
              type: integer
            validation_issues:
              type: integer
        extracted_entities:
          type: array
          items:
            type: object
            properties:
              entity_type:
                type: string
              name:
                type: string
              confidence:
                type: number
              source_document:
                type: string
        errors:
          type: array
          items:
            type: object
            properties:
              stage:
                type: string
              message:
                type: string
              details:
                type: object
```

### 5.4 Tree Traversal and Querying

#### 5.4.1 Advanced Query API
```yaml
paths:
  /api/v1/tenants/{tenant_id}/query:
    post:
      summary: Execute a custom Cypher query (restricted)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                parameters:
                  type: object
      responses:
        200:
          description: Query results
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      type: object
                  columns:
                    type: array
                    items:
                      type: string

  /api/v1/tenants/{tenant_id}/value-tree/search:
    get:
      summary: Search the Value Tree
      parameters:
        - name: q
          in: query
          required: true
          description: Search query
          schema:
            type: string
        - name: entity_types
          in: query
          description: Filter by entity types
          schema:
            type: array
            items:
              type: string
              enum: [CAPABILITY, USE_CASE, PERSONA, VALUE_DRIVER]
        - name: include_paths
          in: query
          description: Include paths to connected nodes
          schema:
            type: boolean
            default: false
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        200:
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/SearchResult'
                  total:
                    type: integer

  /api/v1/tenants/{tenant_id}/value-tree/business-case:
    post:
      summary: Generate a business case from selected capabilities
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - capability_ids
                - prospect_data
              properties:
                capability_ids:
                  type: array
                  items:
                    type: string
                    format: uuid
                prospect_data:
                  type: object
                  properties:
                    company_name:
                      type: string
                    industry:
                      type: string
                    company_size:
                      type: string
                    annual_revenue:
                      type: number
                    current_challenges:
                      type: array
                      items:
                        type: string
                configuration:
                  type: object
                  properties:
                    include_roi_calculation:
                      type: boolean
                      default: true
                    include_implementation_timeline:
                      type: boolean
                      default: true
                    include_risk_assessment:
                      type: boolean
                      default: false
      responses:
        200:
          description: Generated business case
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BusinessCase'

components:
  schemas:
    SearchResult:
      type: object
      properties:
        entity_id:
          type: string
        entity_type:
          type: string
        name:
          type: string
        description:
          type: string
        confidence_score:
          type: number
        match_score:
          type: number
        paths:
          type: array
          items:
            type: object
    
    BusinessCase:
      type: object
      properties:
        business_case_id:
          type: string
          format: uuid
        prospect_info:
          type: object
        selected_capabilities:
          type: array
          items:
            $ref: '#/components/schemas/Capability'
        value_proposition:
          type: object
          properties:
            summary:
              type: string
            key_benefits:
              type: array
              items:
                type: string
        financial_analysis:
          type: object
          properties:
            roi_percentage:
              type: number
            payback_period_months:
              type: number
            npv:
              type: number
            total_benefits:
              type: number
            total_costs:
              type: number
            benefit_breakdown:
              type: array
              items:
                type: object
                properties:
                  value_driver:
                    type: string
                  estimated_value:
                    type: number
                  confidence:
                    type: number
        implementation_roadmap:
          type: array
          items:
            type: object
            properties:
              phase:
                type: string
              duration:
                type: string
              capabilities:
                type: array
                items:
                  type: string
        stakeholder_impact:
          type: array
          items:
            type: object
            properties:
              persona:
                $ref: '#/components/schemas/Persona'
              benefits:
                type: array
                items:
                  type: string
              time_savings_hours:
                type: number
        generated_at:
          type: string
          format: date-time
```

---

## 6. IMPLEMENTATION NOTES

### 6.1 Database Schema (Neo4j)

```cypher
// Core constraints and indexes for Value Tree

// Node constraints
CREATE CONSTRAINT capability_id IF NOT EXISTS
FOR (c:Capability) REQUIRE c.capability_id IS UNIQUE;

CREATE CONSTRAINT use_case_id IF NOT EXISTS
FOR (u:UseCase) REQUIRE u.use_case_id IS UNIQUE;

CREATE CONSTRAINT persona_id IF NOT EXISTS
FOR (p:Persona) REQUIRE p.persona_id IS UNIQUE;

CREATE CONSTRAINT value_driver_id IF NOT EXISTS
FOR (v:ValueDriver) REQUIRE v.value_driver_id IS UNIQUE;

CREATE CONSTRAINT formula_id IF NOT EXISTS
FOR (f:Formula) REQUIRE f.formula_id IS UNIQUE;

// Composite constraints for tenant isolation
CREATE CONSTRAINT capability_tenant_name IF NOT EXISTS
FOR (c:Capability) REQUIRE (c.tenant_id, c.name) IS UNIQUE;

CREATE CONSTRAINT use_case_tenant_name IF NOT EXISTS
FOR (u:UseCase) REQUIRE (u.tenant_id, u.name) IS UNIQUE;

CREATE CONSTRAINT persona_tenant_name IF NOT EXISTS
FOR (p:Persona) REQUIRE (p.tenant_id, p.name) IS UNIQUE;

CREATE CONSTRAINT value_driver_tenant_name IF NOT EXISTS
FOR (v:ValueDriver) REQUIRE (v.tenant_id, v.name) IS UNIQUE;

// Indexes for performance
CREATE INDEX capability_category_idx IF NOT EXISTS
FOR (c:Capability) ON (c.category);

CREATE INDEX value_driver_category_idx IF NOT EXISTS
FOR (v:ValueDriver) ON (v.category);

CREATE INDEX entity_status_idx IF NOT EXISTS
FOR (n) WHERE n:Capability OR n:UseCase OR n:Persona OR n:ValueDriver
ON (n.status);

CREATE INDEX entity_confidence_idx IF NOT EXISTS
FOR (n) WHERE n:Capability OR n:UseCase OR n:Persona OR n:ValueDriver
ON (n.confidence_score);
```

### 6.2 Event-Driven Architecture

```python
# Event definitions for async processing

class ValueTreeEvents:
    """Event types for Value Tree operations"""
    
    # Entity events
    CAPABILITY_CREATED = "capability.created"
    CAPABILITY_UPDATED = "capability.updated"
    CAPABILITY_DELETED = "capability.deleted"
    
    USE_CASE_CREATED = "use_case.created"
    USE_CASE_UPDATED = "use_case.updated"
    
    PERSONA_CREATED = "persona.created"
    PERSONA_UPDATED = "persona.updated"
    
    VALUE_DRIVER_CREATED = "value_driver.created"
    VALUE_DRIVER_UPDATED = "value_driver.updated"
    
    # Relationship events
    RELATIONSHIP_CREATED = "relationship.created"
    RELATIONSHIP_DELETED = "relationship.deleted"
    
    # Pipeline events
    EXTRACTION_STARTED = "extraction.started"
    EXTRACTION_COMPLETED = "extraction.completed"
    EXTRACTION_FAILED = "extraction.failed"
    
    NORMALIZATION_STARTED = "normalization.started"
    NORMALIZATION_COMPLETED = "normalization.completed"
    
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    
    # Formula events
    FORMULA_CREATED = "formula.created"
    FORMULA_EVALUATED = "formula.evaluated"
    FORMULA_VALIDATION_FAILED = "formula.validation_failed"
```

### 6.3 Security Considerations

```python
# Security middleware and access control

class ValueTreeAccessControl:
    """
    Access control for Value Tree operations
    """
    
    PERMISSIONS = {
        "capability": ["read", "create", "update", "delete"],
        "use_case": ["read", "create", "update", "delete"],
        "persona": ["read", "create", "update", "delete"],
        "value_driver": ["read", "create", "update", "delete"],
        "formula": ["read", "create", "update", "delete", "evaluate"],
        "pipeline": ["read", "execute", "cancel"],
    }
    
    ROLES = {
        "admin": list(PERMISSIONS.keys()),
        "editor": ["read", "create", "update"],
        "viewer": ["read"],
        "analyst": ["read", "evaluate"],
    }
    
    @staticmethod
    def check_permission(user_role: str, resource: str, action: str) -> bool:
        """Check if user role has permission for action on resource"""
        role_perms = ValueTreeAccessControl.ROLES.get(user_role, [])
        resource_perms = ValueTreeAccessControl.PERMISSIONS.get(resource, [])
        return action in role_perms and action in resource_perms
    
    @staticmethod
    def filter_by_tenant(query: str, tenant_id: str) -> str:
        """Inject tenant filter into Cypher query"""
        # This is a simplified example - actual implementation would use
        # parameterized queries and proper query parsing
        return query.replace(
            "WHERE", 
            f"WHERE tenant_id = '{tenant_id}' AND "
        )
```

---

## APPENDIX: GLOSSARY

- **Capability**: Intrinsic functionality or service provided by the platform
- **Use Case**: Practical application of capabilities within an operational context
- **Persona**: Organizational role whose workflows are affected by use cases
- **Value Driver**: Quantifiable business outcome justifying expenditure
- **CDM**: Canonical Data Model - universal semantic translator
- **OpenMath**: Standard for representing mathematical objects
- **MathML**: XML-based markup language for mathematical notation
- **RDF**: Resource Description Framework - graph data model
