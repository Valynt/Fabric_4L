"""Core ontology models for Value Fabric extraction pipeline.

Defines the 4 core entity types: Capability, UseCase, Persona, ValueDriver
using Pydantic v2 with strict validation.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleType(str, Enum):
    """Valid persona role types in the enterprise buying process.

    Describes the buying-process function, distinct from organizational seniority.
    """

    ECONOMIC_BUYER = "economic_buyer"
    CHAMPION = "champion"
    OPERATIONAL_USER = "operational_user"
    TECHNICAL_BUYER = "technical_buyer"
    STAKEHOLDER = "stakeholder"


class SeniorityLevel(str, Enum):
    """Organizational seniority level for personas.

    Aligned with pack ontology role_type values:
    - EXECUTIVE_SPONSOR: Executive sponsor with budget authority
    - C_SUITE: C-level executive (CEO, CFO, CTO, etc.)
    - VP: Vice President level
    - DIRECTOR: Director level
    - MANAGER: Manager level
    - INDIVIDUAL_CONTRIBUTOR: Individual contributor / specialist
    - UNKNOWN: Seniority level not specified
    """

    EXECUTIVE_SPONSOR = "executive_sponsor"
    C_SUITE = "c_suite"
    VP = "vp"
    DIRECTOR = "director"
    MANAGER = "manager"
    INDIVIDUAL_CONTRIBUTOR = "individual_contributor"
    UNKNOWN = "unknown"


class ValueCategory(str, Enum):
    """Categories of value drivers in enterprise software.

    Aligned with pack ontology values:
    - CAPITAL_EFFICIENCY: Optimizes capital deployment (cash flow, inventory)
    - COST_REDUCTION: Reduces operational costs (automation, efficiency)
    - RISK_MITIGATION: Reduces business risk (compliance, security)
    - REVENUE_ENHANCEMENT: Increases revenue (up-sell, cross-sell, retention)
    """

    # Pack-aligned granular categories
    CAPITAL_EFFICIENCY = "capital_efficiency"
    COST_REDUCTION = "cost_reduction"
    RISK_MITIGATION = "risk_mitigation"
    REVENUE_ENHANCEMENT = "revenue_enhancement"

    # Legacy values (maintained for backward compatibility, map to new values)
    REVENUE = "revenue"  # Maps to REVENUE_ENHANCEMENT
    COST = "cost"  # Maps to COST_REDUCTION
    RISK = "risk"  # Maps to RISK_MITIGATION
    CAPITAL = "capital"  # Maps to CAPITAL_EFFICIENCY


class Capability(BaseModel):
    """A technical capability or feature of a product/service.

    Capabilities are the building blocks that enable use cases and
    contribute to value drivers.

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable capability name
        description: Detailed description of what the capability does
        technical_features: List of specific technical features
        api_endpoints: List of API endpoints if applicable
        integrations: List of supported integrations
        apqc_mapping: APQC Process Classification Framework code
        source_refs: URLs where this capability was extracted from
        confidence: LLM confidence score (0.0-1.0)
        extracted_at: Timestamp of extraction
        extraction_job_id: Reference to extraction job
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    technical_features: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    apqc_mapping: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name for matching while preserving original in display."""
        return v.strip()

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Real-Time Data Ingestion",
                "description": "Stream data from multiple sources with sub-second latency",
                "technical_features": ["Kafka streaming", "Change data capture", "Schema registry"],
                "confidence": 0.92,
            }
        }
    )


class UseCase(BaseModel):
    """A business use case that solves a specific problem.

    Use cases represent how capabilities are applied to solve business
    problems for specific personas.

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable use case name
        description: Detailed description of the use case
        industry_context: Industries where this applies
        required_capabilities: IDs of capabilities needed
        workflow_steps: Ordered steps in the workflow
        kpis: Key performance indicators for this use case
        confidence: LLM confidence score
        extracted_at: Timestamp of extraction
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    industry_context: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("required_capabilities")
    @classmethod
    def validate_capability_refs(cls, v: list[str]) -> list[str]:
        """Ensure all capability references are valid UUID strings."""
        for ref in v:
            try:
                UUID(ref)
            except ValueError:
                raise ValueError(f"Invalid capability reference: {ref}")
        return v

    model_config = ConfigDict(extra="forbid")


class Persona(BaseModel):
    """A stakeholder or user persona in the enterprise buying process.

    Personas represent the people involved in decisions, their pain points,
    and what drives value for them.

    Attributes:
        id: Unique identifier (UUID)
        role_type: Type of role in buying process
        seniority_level: Organizational seniority level
        title: Job title
        department: Department/organization
        pain_points: List of problems this persona faces
        success_metrics: How they measure success
        influenced_by: Other persona IDs that influence this one
        confidence: LLM confidence score
        extracted_at: Timestamp of extraction
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    role_type: RoleType
    seniority_level: SeniorityLevel = Field(default=SeniorityLevel.UNKNOWN)
    title: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    pain_points: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    influenced_by: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("influenced_by")
    @classmethod
    def validate_persona_refs(cls, v: list[str]) -> list[str]:
        """Ensure all persona references are valid UUID strings."""
        for ref in v:
            try:
                UUID(ref)
            except ValueError:
                raise ValueError(f"Invalid persona reference: {ref}")
        return v

    model_config = ConfigDict(extra="forbid")


class ValueDriver(BaseModel):
    """A quantifiable business value that drives ROI.

    Value drivers connect capabilities to business outcomes with
    mathematical formulas for calculating ROI.

    Attributes:
        id: Unique identifier (UUID)
        category: Type of value (revenue, cost, risk, capital)
        name: Human-readable value driver name
        description: Detailed description
        metrics: List of specific metrics
        formula_string: Mathematical formula for calculation
        unit: Unit of measurement (USD, percentage, hours, etc.)
        time_to_value: Expected time to realize value
        confidence: LLM confidence score
        extracted_at: Timestamp of extraction
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    category: ValueCategory
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    metrics: list[str] = Field(default_factory=list)
    formula_string: str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    time_to_value: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("formula_string")
    @classmethod
    def validate_formula(cls, v: str | None) -> str | None:
        """Basic validation that formula uses only allowed characters.

        Allows:
        - Numbers (0-9)
        - Operators (+, -, *, /)
        - Parentheses ((), {})
        - Underscore (_) for variable names
        - Whitespace
        - Letters (a-z, A-Z) for variable names inside {}
        """
        if v is None:
            return v
        # Allow: numbers, operators, parentheses, braces, underscore, whitespace, letters
        allowed = set("0123456789+-*/().{}_ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        invalid_chars = set(v) - allowed
        if invalid_chars:
            raise ValueError(
                f"Formula contains invalid characters: {invalid_chars}. "
                f"Only numbers, operators, parentheses, and {{variables}} allowed."
            )
        return v

    model_config = ConfigDict(extra="forbid")


class MetricDirection(str, Enum):
    """Direction of improvement for a value metric.

    Indicates whether a higher or lower value represents improvement.
    """

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    TARGET_VALUE = "target_value"


class ValueMetric(BaseModel):
    """A measurable KPI that quantifies the impact of a ValueDriver.

    ValueMetrics sit at the leaf of the value chain:
    Capability → enables → UseCase → delivers → ValueDriver → impacts → ValueMetric

    They provide the concrete, numeric evidence that a value driver has been
    realized, e.g. "Days Sales Outstanding reduced by 8 days".

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable metric name (e.g. "Days Sales Outstanding")
        description: Detailed description of what this metric measures
        unit: Unit of measurement (days, USD, %, FTEs, etc.)
        direction: Whether higher or lower values represent improvement
        baseline_value: Typical pre-solution baseline (optional)
        target_value: Expected post-solution value (optional)
        benchmark_source: Where the benchmark data came from (optional)
        formula_string: Mathematical formula for computing this metric (optional)
        value_driver_ids: IDs of ValueDrivers this metric quantifies
        source_refs: URLs where this metric was extracted from
        confidence: LLM confidence score (0.0-1.0)
        extracted_at: Timestamp of extraction
        extraction_job_id: Reference to extraction job
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    unit: str = Field(..., min_length=1, max_length=100)
    direction: MetricDirection = Field(default=MetricDirection.LOWER_IS_BETTER)
    baseline_value: float | None = None
    target_value: float | None = None
    benchmark_source: str | None = None
    formula_string: str | None = None
    value_driver_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("value_driver_ids")
    @classmethod
    def validate_driver_refs(cls, v: list[str]) -> list[str]:
        """Ensure all value driver references are valid UUID strings."""
        for ref in v:
            try:
                UUID(ref)
            except ValueError:
                raise ValueError(f"Invalid value driver reference: {ref}")
        return v

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name for matching while preserving original in display."""
        return v.strip()

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Days Sales Outstanding",
                "description": "Average number of days to collect payment after a sale",
                "unit": "days",
                "direction": "lower_is_better",
                "baseline_value": 45.0,
                "target_value": 37.0,
                "confidence": 0.88,
            }
        },
    )


class Feature(BaseModel):
    """A product feature that implements a capability.

    Features represent concrete product functionality that delivers
    one or more capabilities. They sit between raw capabilities
    and user-facing use cases in the ontology hierarchy.

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable feature name
        description: Detailed description of what the feature does
        parent_capability_id: ID of the capability this feature implements
        technical_spec: Technical specification details
        implementation_status: Current status (planned, beta, ga, deprecated)
        source_refs: URLs where this feature was extracted from
        confidence: LLM confidence score (0.0-1.0)
        extracted_at: Timestamp of extraction
        extraction_job_id: Reference to extraction job
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    parent_capability_id: str | None = None
    technical_spec: str | None = None
    implementation_status: str = Field(default="ga", pattern="^(planned|beta|ga|deprecated)$")
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_job_id: str | None = None
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = ""
    prompt_version_id: str = ""  # Immutable prompt template version ID from registry
    model_version: str = ""

    @field_validator("parent_capability_id")
    @classmethod
    def validate_capability_ref(cls, v: str | None) -> str | None:
        """Ensure capability reference is valid UUID if provided."""
        if v is None:
            return v
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid capability reference: {v}")
        return v

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name for matching while preserving original in display."""
        return v.strip()

    model_config = ConfigDict(extra="forbid")


class ExtractionResult(BaseModel):
    """Complete result from an extraction job.

    Contains all entities and relationships extracted from a document
    with provenance metadata.
    """

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    source_url: str
    source_content_id: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    use_cases: list[UseCase] = Field(default_factory=list)
    personas: list[Persona] = Field(default_factory=list)
    value_drivers: list[ValueDriver] = Field(default_factory=list)
    value_metrics: list[ValueMetric] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    chunks_processed: int = 0
    errors: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    schema_version: str = ""
    prompt_version: str = ""
    prompt_template_version: str = ""
    prompt_template_hash: str | None = None
    model_version: str = ""
    security_metadata: list["ExtractionSecurityMetadata"] = Field(default_factory=list)

    def get_all_entities(self) -> Sequence[BaseModel]:
        """Return all extracted entities as a flat list."""
        result: list[BaseModel] = []
        result.extend(self.capabilities)
        result.extend(self.use_cases)
        result.extend(self.personas)
        result.extend(self.value_drivers)
        result.extend(self.value_metrics)
        result.extend(self.features)
        return result

    def get_entity_by_id(self, entity_id: str) -> BaseModel | None:
        """Find an entity by its ID across all types."""
        for entity in self.get_all_entities():
            if entity.id == entity_id:
                return entity
        return None

    model_config = ConfigDict(extra="forbid")


class ExtractionSecurityMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suspicious_instruction_hits: list[str] = Field(default_factory=list)
    high_risk_token_hits: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: str = "none"
    rejection_tier: str = "allow"


# =============================================================================
# Schema-Level Models (Ontology Definition)
# =============================================================================
# These models define the structure of types, properties, and relationships
# that guide extraction. They represent the "schema" layer, distinct from the
# "instance" layer above (Capability, UseCase, etc.)


class PropertyType(str, Enum):
    """Valid property types for ontology type definitions."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"
    OBJECT = "object"
    REFERENCE = "reference"


class RelationshipType(str, Enum):
    """Valid relationship types between ontology types."""

    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    RELATES_TO = "relates_to"
    CONTAINS = "contains"


class Cardinality(str, Enum):
    """Cardinality constraints for relationships."""

    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class PropertyConstraints(BaseModel):
    """Constraints for ontology property definitions.

    Attributes:
        min_length: Minimum length for string properties
        max_length: Maximum length for string properties
        min: Minimum value for numeric properties
        max: Maximum value for numeric properties
        pattern: Regex pattern for string validation
        enum: Allowed values for enumerated properties
        reference_type_id: Type ID for reference properties
    """

    min_length: int | None = None
    max_length: int | None = None
    min: float | None = None
    max: float | None = None
    pattern: str | None = None
    enum: list[str] | None = None
    reference_type_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class OntologyProperty(BaseModel):
    """A property definition for an ontology type.

    Schema-level: defines what properties a type should have.
    Instance-level: extracted entities have actual values for these properties.

    Attributes:
        id: Unique identifier for this property definition
        name: Property name (snake_case recommended)
        type: Data type of the property
        description: Human-readable description
        required: Whether this property is required
        default_value: Default value if not specified
        constraints: Validation constraints
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    type: PropertyType
    description: str | None = Field(default=None, max_length=1000)
    required: bool = False
    default_value: str | int | float | bool | list | dict | None = None
    constraints: PropertyConstraints | None = None

    model_config = ConfigDict(extra="forbid")


class OntologyType(BaseModel):
    """An ontology type definition (schema-level).

    Defines the structure for a category of entities that can be extracted.
    For example, "Capability" type defines that all capabilities have:
    - name (required string)
    - description (required string)
    - technical_features (optional array)

    Attributes:
        id: Unique type identifier (e.g., "capability", "use_case")
        name: Human-readable type name
        description: Type description
        properties: Property definitions for this type
        parent_type_id: Parent type for inheritance (optional)
        is_active: Whether this type is currently active
        version: Schema version number
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    properties: list[OntologyProperty] = Field(default_factory=list)
    parent_type_id: str | None = None
    is_active: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("properties")
    @classmethod
    def validate_unique_property_names(cls, v: list[OntologyProperty]) -> list[OntologyProperty]:
        """Ensure property names are unique within the type."""
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Property names must be unique within a type")
        return v

    model_config = ConfigDict(extra="forbid")


class TypeRelationship(BaseModel):
    """A relationship definition between two ontology types.

    Schema-level: defines that type A can relate to type B via relationship R.
    Instance-level: extracted entities have actual relationships.

    Attributes:
        id: Unique relationship identifier
        source_type_id: Source type ID
        target_type_id: Target type ID
        relationship_type: Type of relationship
        description: Relationship description
        cardinality: Cardinality constraint
        created_at: Creation timestamp
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_type_id: str
    target_type_id: str
    relationship_type: RelationshipType
    description: str | None = Field(default=None, max_length=1000)
    cardinality: Cardinality = Cardinality.MANY_TO_MANY
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")


# Union type for any ontology entity handled by the deduplication pipeline.
# Required for type-safe entity collection processing.
OntologyEntity = Capability | UseCase | Persona | ValueDriver | Feature

