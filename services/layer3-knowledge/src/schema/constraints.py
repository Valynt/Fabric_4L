"""Neo4j schema definitions for Value Fabric Knowledge Graph.

NOTE: Property existence constraints (constraint_type="exists") require Neo4j
Enterprise Edition. For Community Edition compatibility, use application-level
validation via ingestion.validators.RequiredFieldValidator instead.

The CONSTRAINTS list below uses only unique constraints (constraint_type="unique")
which are supported on both Community and Enterprise editions.
"""

from dataclasses import dataclass

from ..config import get_settings


@dataclass
class Constraint:
    """Neo4j constraint definition."""

    name: str
    entity_type: str
    property_name: str | list[str]  # Single property or list for composite
    constraint_type: str = "unique"  # unique (Community+Enterprise), exists (Enterprise only), node_key (Enterprise only)

    @property
    def cypher(self) -> str:
        """Generate Cypher constraint creation statement."""
        # Handle composite properties
        if isinstance(self.property_name, list):
            if len(self.property_name) == 1:
                prop_str = f"n.{self.property_name[0]}"
            else:
                # Wrap composite properties in parentheses for valid Cypher
                prop_str = f"({', '.join(f'n.{p}' for p in self.property_name)})"
        else:
            prop_str = f"n.{self.property_name}"

        if self.constraint_type == "unique":
            return (
                f"CREATE CONSTRAINT {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"REQUIRE {prop_str} IS UNIQUE"
            )
        elif self.constraint_type == "exists":
            return (
                f"CREATE CONSTRAINT {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"REQUIRE {prop_str} IS NOT NULL"
            )
        elif self.constraint_type == "node_key":
            return (
                f"CREATE CONSTRAINT {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"REQUIRE {prop_str} IS NODE KEY"
            )
        return ""

    @property
    def drop_cypher(self) -> str:
        """Generate Cypher constraint drop statement."""
        return f"DROP CONSTRAINT {self.name} IF EXISTS"


@dataclass
class Index:
    """Neo4j index definition."""

    name: str
    entity_type: str
    properties: list[str]
    index_type: str = "btree"  # btree, fulltext, vector, lookup

    @property
    def cypher(self) -> str:
        """Generate Cypher index creation statement."""
        props = ", ".join(f"n.{p}" for p in self.properties)

        if self.index_type == "btree":
            return (
                f"CREATE INDEX {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"ON ({props})"
            )
        elif self.index_type == "fulltext":
            return (
                f"CREATE FULLTEXT INDEX {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"ON EACH [{props}]"
            )
        elif self.index_type == "vector":
            embedding_dimension = get_settings().embedding_dimension
            # Vector index only supports single property
            return (
                f"CREATE VECTOR INDEX {self.name} "
                f"IF NOT EXISTS "
                f"FOR (n:{self.entity_type}) "
                f"ON (n.{self.properties[0]}) "
                f"OPTIONS {{indexConfig: {{`vector.dimensions`: {embedding_dimension}, `vector.similarity_function`: 'cosine'}}}}"
            )
        elif self.index_type == "lookup":
            return f"CREATE LOOKUP INDEX {self.name} IF NOT EXISTS FOR (n) ON EACH labels(n)"
        return ""

    @property
    def drop_cypher(self) -> str:
        """Generate Cypher index drop statement."""
        return f"DROP INDEX {self.name} IF EXISTS"


# Entity types in the Value Fabric ontology (from value_fabric_ontology_schema.py spec)
ENTITY_TYPES = [
    # Primary Business Concepts
    "Capability",
    "UseCase",
    "Persona",
    "ValueDriver",
    "ValueMetric",
    # Product & Solution Domain
    "Product",
    "Feature",
    "Service",
    "Solution",
    "Technology",
    # Organizational Context
    "Organization",
    "BusinessUnit",
    "Process",
    "Activity",
    # Industry Reference Model Mappings
    "APQCProcess",
    "BIANServiceDomain",
    "FIBOEntity",
    # Supporting Concepts
    "Industry",
    "MarketSegment",
    "Geography",
    "Regulation",
    # Metadata & Provenance
    "DataSource",
    "ExtractionEvent",
    "ConfidenceScore",
    # Phase 2 Extensions
    "ValuePack",
    "Variable",
    "BenchmarkDataset",
    # Signal Extraction (Phase 3 - Operational Signals Vertical Slice)
    "PainSignal",
    "Evidence",
]

# Relationship types (aligned with value_fabric_ontology_schema.py spec)
RELATIONSHIP_TYPES = [
    # Capability Relationships
    "enables",  # Capability -> UseCase (was ENABLES)
    "requires",  # Capability -> Capability / UseCase -> Feature
    "subTypeOf",  # Capability -> Capability (hierarchy)
    "implementedBy",  # Capability -> Feature
    "measuredBy",  # Capability -> ValueMetric
    # Use Case Relationships
    "delivers",  # UseCase -> ValueDriver
    "involves",  # UseCase -> Persona (was BENEFITS)
    "requiresFeature",  # UseCase -> Feature
    "partOf",  # UseCase -> Process
    # Value Relationships
    "impacts",  # ValueDriver -> ValueMetric
    "drivenBy",  # ValueDriver -> UseCase
    "measures",  # ValueMetric -> Any
    # Product Relationships
    "implements",  # Feature -> Capability
    "hasFeature",  # Product -> Feature
    "addresses",  # Product -> UseCase
    "provides",  # Service -> Capability
    # Persona Relationships
    "performs",  # Persona -> UseCase
    "benefitsFrom",  # Persona -> ValueDriver
    "belongsTo",  # Persona -> Organization
    # Organizational Relationships
    "contains",  # Process -> Activity
    "operatesIn",  # Organization -> Industry/Geography
    "owns",  # BusinessUnit -> Process
    # Reference Model Mappings
    "mapsToAPQC",  # Process/Activity/Capability -> APQCProcess
    "mapsToBIAN",  # Capability/Service -> BIANServiceDomain
    "mapsToFIBO",  # Organization -> FIBOEntity
    "semanticallyEquivalent",  # Any -> Any (coreference)
    # Provenance Relationships
    "extractedFrom",  # Any -> DataSource
    "generatedBy",  # Any -> ExtractionEvent
    "validatedBy",  # Any -> Agent
    "supersedes",  # Entity -> Entity (versioning)
    # Phase 2: Value Pack Relationships
    "hasDriver",  # ValuePack -> ValueDriver
    "hasFormula",  # ValuePack -> Formula
    "hasBenchmark",  # ValuePack -> BenchmarkDataset
    "belongsToPack",  # Variable/Formula -> ValuePack
    "usedIn",  # Variable -> Formula
    "dependsOn",  # Formula -> Formula
    # Signal Extraction Relationships (Phase 3)
    "exhibits",  # Account -> PainSignal
    "supportedBy",  # PainSignal -> Evidence
    "quantifiedBy",  # PainSignal -> Formula
    "mapsTo",  # PainSignal -> ValueDriver
]

# Current retrieval set for vector similarity search.
# Keep this list aligned with src/retrieval/vector_store.py VECTOR_ENTITY_TYPES.
VECTOR_INDEX_ENTITY_TYPES = [
    "Capability",
    "UseCase",
    "Persona",
    "ValueDriver",
    # Phase 3: Evidence vector search for signal matching
    "Evidence",
]

# Constraints for data integrity
# NOTE: All entity constraints are composite (id, tenant_id) for tenant isolation.
# This allows the same id to exist in different tenants while preventing duplicates
# within a tenant. Composite unique constraints work on Neo4j Community Edition.
CONSTRAINTS: list[Constraint] = [
    # Composite unique constraints on (id, tenant_id) for tenant isolation
    # L2.5 Signal Refinery — ValueSignal node
    Constraint("valuesignal_id_tenant", "ValueSignal", ["id", "tenant_id"], "unique"),
    Constraint("capability_id_tenant", "Capability", ["id", "tenant_id"], "unique"),
    Constraint("usecase_id_tenant", "UseCase", ["id", "tenant_id"], "unique"),
    Constraint("persona_id_tenant", "Persona", ["id", "tenant_id"], "unique"),
    Constraint("valuedriver_id_tenant", "ValueDriver", ["id", "tenant_id"], "unique"),
    Constraint("valuemetric_id_tenant", "ValueMetric", ["id", "tenant_id"], "unique"),
    Constraint("product_id_tenant", "Product", ["id", "tenant_id"], "unique"),
    Constraint("feature_id_tenant", "Feature", ["id", "tenant_id"], "unique"),
    Constraint("service_id_tenant", "Service", ["id", "tenant_id"], "unique"),
    Constraint("solution_id_tenant", "Solution", ["id", "tenant_id"], "unique"),
    Constraint("technology_id_tenant", "Technology", ["id", "tenant_id"], "unique"),
    Constraint("organization_id_tenant", "Organization", ["id", "tenant_id"], "unique"),
    Constraint("businessunit_id_tenant", "BusinessUnit", ["id", "tenant_id"], "unique"),
    Constraint("process_id_tenant", "Process", ["id", "tenant_id"], "unique"),
    Constraint("activity_id_tenant", "Activity", ["id", "tenant_id"], "unique"),
    Constraint("apqcprocess_id_tenant", "APQCProcess", ["id", "tenant_id"], "unique"),
    Constraint("bianservicedomain_id_tenant", "BIANServiceDomain", ["id", "tenant_id"], "unique"),
    Constraint("fiboentity_id_tenant", "FIBOEntity", ["id", "tenant_id"], "unique"),
    Constraint("industry_id_tenant", "Industry", ["id", "tenant_id"], "unique"),
    Constraint("marketsegment_id_tenant", "MarketSegment", ["id", "tenant_id"], "unique"),
    Constraint("geography_id_tenant", "Geography", ["id", "tenant_id"], "unique"),
    Constraint("regulation_id_tenant", "Regulation", ["id", "tenant_id"], "unique"),
    Constraint("datasource_id_tenant", "DataSource", ["id", "tenant_id"], "unique"),
    Constraint("extractionevent_id_tenant", "ExtractionEvent", ["id", "tenant_id"], "unique"),
    Constraint("confidencescore_id_tenant", "ConfidenceScore", ["id", "tenant_id"], "unique"),
    # Phase 2: Value Pack and Variable constraints
    Constraint("valuepack_id_tenant", "ValuePack", ["id", "tenant_id"], "unique"),
    Constraint("variable_id_tenant", "Variable", ["id", "tenant_id"], "unique"),
    Constraint("benchmarkdataset_id_tenant", "BenchmarkDataset", ["id", "tenant_id"], "unique"),
    # Phase 3: Signal extraction constraints
    Constraint("painsignal_id_tenant", "PainSignal", ["id", "tenant_id"], "unique"),
    Constraint("evidence_id_tenant", "Evidence", ["id", "tenant_id"], "unique"),
    # Phase 2 (L3 Tenant Standardization): Missing constraints for unscoped route modules
    Constraint("formula_id_tenant", "Formula", ["id", "tenant_id"], "unique"),
    Constraint("benchmark_id_tenant", "Benchmark", ["id", "tenant_id"], "unique"),
    Constraint("valuemodel_id_tenant", "ValueModel", ["model_id", "tenant_id"], "unique"),
    Constraint("benchmarkpolicy_id_tenant", "BenchmarkPolicy", ["id", "tenant_id"], "unique"),
    Constraint("formulaversion_id_tenant", "FormulaVersion", ["id", "tenant_id"], "unique"),
    Constraint("sourcebinding_id_tenant", "SourceBinding", ["id", "tenant_id"], "unique"),
    # Enterprise tenant label registry coverage.
    Constraint("account_id_tenant", "Account", ["id", "tenant_id"], "unique"),
    Constraint("battlecard_id_tenant", "Battlecard", ["id", "tenant_id"], "unique"),
    Constraint("business_case_id_tenant", "BusinessCase", ["id", "tenant_id"], "unique"),
    Constraint("case_study_id_tenant", "CaseStudy", ["id", "tenant_id"], "unique"),
    Constraint("chunk_id_tenant", "Chunk", ["id", "tenant_id"], "unique"),
    Constraint("community_id_tenant", "Community", ["id", "tenant_id"], "unique"),
    Constraint("company_id_tenant", "Company", ["id", "tenant_id"], "unique"),
    Constraint("competitor_id_tenant", "Competitor", ["id", "tenant_id"], "unique"),
    Constraint("contact_id_tenant", "Contact", ["id", "tenant_id"], "unique"),
    Constraint("customer_id_tenant", "Customer", ["id", "tenant_id"], "unique"),
    Constraint("document_id_tenant", "Document", ["id", "tenant_id"], "unique"),
    Constraint("entity_id_tenant", "Entity", ["id", "tenant_id"], "unique"),
    Constraint("insight_id_tenant", "Insight", ["id", "tenant_id"], "unique"),
    Constraint("model_id_tenant", "Model", ["id", "tenant_id"], "unique"),
    Constraint("opportunity_id_tenant", "Opportunity", ["id", "tenant_id"], "unique"),
    Constraint("prospect_id_tenant", "Prospect", ["id", "tenant_id"], "unique"),
    Constraint("r_o_i_calculation_id_tenant", "ROICalculation", ["id", "tenant_id"], "unique"),
    Constraint("r_o_i_template_id_tenant", "ROITemplate", ["id", "tenant_id"], "unique"),
    Constraint("segment_id_tenant", "Segment", ["id", "tenant_id"], "unique"),
    Constraint("signal_id_tenant", "Signal", ["id", "tenant_id"], "unique"),
    Constraint("source_id_tenant", "Source", ["id", "tenant_id"], "unique"),
    Constraint("stakeholder_id_tenant", "Stakeholder", ["id", "tenant_id"], "unique"),
    Constraint("value_lever_id_tenant", "ValueLever", ["id", "tenant_id"], "unique"),
    Constraint("value_tree_id_tenant", "ValueTree", ["id", "tenant_id"], "unique"),
    # NOTE: Property existence constraints require Neo4j Enterprise Edition.
    # For Community Edition compatibility, we use composite unique constraints
    # and rely on application-level validation for tenant_id presence.
]

# P0-03: Tenant isolation constraints (requires Neo4j Enterprise Edition)
# These enforce that tenant_id cannot be null on any entity
# For Community Edition, tenant_id validation is done at application level
TENANT_CONSTRAINTS: list[Constraint] = [
    Constraint("capability_tenant_id", "Capability", "tenant_id", "exists"),
    Constraint("usecase_tenant_id", "UseCase", "tenant_id", "exists"),
    Constraint("persona_tenant_id", "Persona", "tenant_id", "exists"),
    Constraint("valuedriver_tenant_id", "ValueDriver", "tenant_id", "exists"),
    Constraint("valuemetric_tenant_id", "ValueMetric", "tenant_id", "exists"),
    Constraint("product_tenant_id", "Product", "tenant_id", "exists"),
    Constraint("feature_tenant_id", "Feature", "tenant_id", "exists"),
    Constraint("service_tenant_id", "Service", "tenant_id", "exists"),
    Constraint("solution_tenant_id", "Solution", "tenant_id", "exists"),
    Constraint("technology_tenant_id", "Technology", "tenant_id", "exists"),
    Constraint("organization_tenant_id", "Organization", "tenant_id", "exists"),
    Constraint("businessunit_tenant_id", "BusinessUnit", "tenant_id", "exists"),
    Constraint("process_tenant_id", "Process", "tenant_id", "exists"),
    Constraint("activity_tenant_id", "Activity", "tenant_id", "exists"),
    Constraint("valuepack_tenant_id", "ValuePack", "tenant_id", "exists"),
    Constraint("variable_tenant_id", "Variable", "tenant_id", "exists"),
    Constraint("formula_tenant_id", "Formula", "tenant_id", "exists"),
    # Phase 2 (L3 Tenant Standardization): Missing existence constraints for unscoped route modules
    Constraint("benchmark_tenant_id", "Benchmark", "tenant_id", "exists"),
    Constraint("valuemodel_tenant_id", "ValueModel", "tenant_id", "exists"),
    Constraint("benchmarkpolicy_tenant_id", "BenchmarkPolicy", "tenant_id", "exists"),
    Constraint("formulaversion_tenant_id", "FormulaVersion", "tenant_id", "exists"),
    Constraint("sourcebinding_tenant_id", "SourceBinding", "tenant_id", "exists"),
    # Enterprise tenant label registry coverage.
    Constraint("account_tenant_id", "Account", "tenant_id", "exists"),
    Constraint("battlecard_tenant_id", "Battlecard", "tenant_id", "exists"),
    Constraint("benchmark_dataset_tenant_id", "BenchmarkDataset", "tenant_id", "exists"),
    Constraint("business_case_tenant_id", "BusinessCase", "tenant_id", "exists"),
    Constraint("case_study_tenant_id", "CaseStudy", "tenant_id", "exists"),
    Constraint("chunk_tenant_id", "Chunk", "tenant_id", "exists"),
    Constraint("community_tenant_id", "Community", "tenant_id", "exists"),
    Constraint("company_tenant_id", "Company", "tenant_id", "exists"),
    Constraint("competitor_tenant_id", "Competitor", "tenant_id", "exists"),
    Constraint("contact_tenant_id", "Contact", "tenant_id", "exists"),
    Constraint("customer_tenant_id", "Customer", "tenant_id", "exists"),
    Constraint("document_tenant_id", "Document", "tenant_id", "exists"),
    Constraint("entity_tenant_id", "Entity", "tenant_id", "exists"),
    Constraint("industry_tenant_id", "Industry", "tenant_id", "exists"),
    Constraint("insight_tenant_id", "Insight", "tenant_id", "exists"),
    Constraint("model_tenant_id", "Model", "tenant_id", "exists"),
    Constraint("opportunity_tenant_id", "Opportunity", "tenant_id", "exists"),
    Constraint("prospect_tenant_id", "Prospect", "tenant_id", "exists"),
    Constraint("r_o_i_calculation_tenant_id", "ROICalculation", "tenant_id", "exists"),
    Constraint("r_o_i_template_tenant_id", "ROITemplate", "tenant_id", "exists"),
    Constraint("segment_tenant_id", "Segment", "tenant_id", "exists"),
    Constraint("signal_tenant_id", "Signal", "tenant_id", "exists"),
    Constraint("source_tenant_id", "Source", "tenant_id", "exists"),
    Constraint("stakeholder_tenant_id", "Stakeholder", "tenant_id", "exists"),
    Constraint("value_lever_tenant_id", "ValueLever", "tenant_id", "exists"),
    Constraint("value_tree_tenant_id", "ValueTree", "tenant_id", "exists"),
    # Phase 3: Signal extraction tenant constraints (Enterprise only)
    Constraint("painsignal_tenant_id", "PainSignal", "tenant_id", "exists"),
    Constraint("evidence_tenant_id", "Evidence", "tenant_id", "exists"),
    Constraint("valuesignal_tenant_id", "ValueSignal", "tenant_id", "exists"),
]

# Indexes for query performance
INDEXES: list[Index] = [
    # Tenant isolation indexes (P0-03) - for efficient tenant filtering
    Index("capability_tenant_idx", "Capability", ["tenant_id"], "btree"),
    Index("usecase_tenant_idx", "UseCase", ["tenant_id"], "btree"),
    Index("persona_tenant_idx", "Persona", ["tenant_id"], "btree"),
    Index("valuedriver_tenant_idx", "ValueDriver", ["tenant_id"], "btree"),
    Index("valuemetric_tenant_idx", "ValueMetric", ["tenant_id"], "btree"),
    Index("product_tenant_idx", "Product", ["tenant_id"], "btree"),
    Index("feature_tenant_idx", "Feature", ["tenant_id"], "btree"),
    Index("service_tenant_idx", "Service", ["tenant_id"], "btree"),
    Index("solution_tenant_idx", "Solution", ["tenant_id"], "btree"),
    Index("technology_tenant_idx", "Technology", ["tenant_id"], "btree"),
    Index("organization_tenant_idx", "Organization", ["tenant_id"], "btree"),
    Index("businessunit_tenant_idx", "BusinessUnit", ["tenant_id"], "btree"),
    Index("process_tenant_idx", "Process", ["tenant_id"], "btree"),
    Index("activity_tenant_idx", "Activity", ["tenant_id"], "btree"),
    Index("valuepack_tenant_idx", "ValuePack", ["tenant_id"], "btree"),
    Index("variable_tenant_id_idx", "Variable", ["tenant_id"], "btree"),
    Index("benchmarkdataset_tenant_idx", "BenchmarkDataset", ["tenant_id"], "btree"),
    # Phase 2 (L3 Tenant Standardization): Missing indexes for unscoped route modules
    Index("formula_tenant_id_idx", "Formula", ["tenant_id"], "btree"),
    Index("formula_tenant_lookup_idx", "Formula", ["tenant_id", "id"], "btree"),
    Index("benchmark_tenant_id_idx", "Benchmark", ["tenant_id"], "btree"),
    Index("valuemodel_tenant_id_idx", "ValueModel", ["tenant_id"], "btree"),
    Index("valuemodel_tenant_modelid_idx", "ValueModel", ["tenant_id", "model_id"], "btree"),
    Index("benchmarkpolicy_tenant_id_idx", "BenchmarkPolicy", ["tenant_id"], "btree"),
    Index("formulaversion_tenant_id_idx", "FormulaVersion", ["tenant_id"], "btree"),
    Index("sourcebinding_tenant_id_idx", "SourceBinding", ["tenant_id"], "btree"),
    # Tenant label registry coverage.
    Index("account_tenant_idx", "Account", ["tenant_id"], "btree"),
    Index("account_tenant_id_idx", "Account", ["tenant_id", "id"], "btree"),
    Index("battlecard_tenant_idx", "Battlecard", ["tenant_id"], "btree"),
    Index("battlecard_tenant_id_idx", "Battlecard", ["tenant_id", "id"], "btree"),
    Index("business_case_tenant_idx", "BusinessCase", ["tenant_id"], "btree"),
    Index("business_case_tenant_id_idx", "BusinessCase", ["tenant_id", "id"], "btree"),
    Index("case_study_tenant_idx", "CaseStudy", ["tenant_id"], "btree"),
    Index("case_study_tenant_id_idx", "CaseStudy", ["tenant_id", "id"], "btree"),
    Index("chunk_tenant_idx", "Chunk", ["tenant_id"], "btree"),
    Index("chunk_tenant_id_idx", "Chunk", ["tenant_id", "id"], "btree"),
    Index("community_tenant_idx", "Community", ["tenant_id"], "btree"),
    Index("community_tenant_id_idx", "Community", ["tenant_id", "id"], "btree"),
    Index("company_tenant_idx", "Company", ["tenant_id"], "btree"),
    Index("company_tenant_id_idx", "Company", ["tenant_id", "id"], "btree"),
    Index("competitor_tenant_idx", "Competitor", ["tenant_id"], "btree"),
    Index("competitor_tenant_id_idx", "Competitor", ["tenant_id", "id"], "btree"),
    Index("contact_tenant_idx", "Contact", ["tenant_id"], "btree"),
    Index("contact_tenant_id_idx", "Contact", ["tenant_id", "id"], "btree"),
    Index("customer_tenant_idx", "Customer", ["tenant_id"], "btree"),
    Index("customer_tenant_id_idx", "Customer", ["tenant_id", "id"], "btree"),
    Index("document_tenant_idx", "Document", ["tenant_id"], "btree"),
    Index("document_tenant_id_idx", "Document", ["tenant_id", "id"], "btree"),
    Index("entity_tenant_idx", "Entity", ["tenant_id"], "btree"),
    Index("entity_tenant_id_idx", "Entity", ["tenant_id", "id"], "btree"),
    Index("industry_tenant_idx", "Industry", ["tenant_id"], "btree"),
    Index("industry_tenant_id_idx", "Industry", ["tenant_id", "id"], "btree"),
    Index("insight_tenant_idx", "Insight", ["tenant_id"], "btree"),
    Index("insight_tenant_id_idx", "Insight", ["tenant_id", "id"], "btree"),
    Index("model_tenant_idx", "Model", ["tenant_id"], "btree"),
    Index("model_tenant_id_idx", "Model", ["tenant_id", "id"], "btree"),
    Index("opportunity_tenant_idx", "Opportunity", ["tenant_id"], "btree"),
    Index("opportunity_tenant_id_idx", "Opportunity", ["tenant_id", "id"], "btree"),
    Index("prospect_tenant_idx", "Prospect", ["tenant_id"], "btree"),
    Index("prospect_tenant_id_idx", "Prospect", ["tenant_id", "id"], "btree"),
    Index("r_o_i_calculation_tenant_idx", "ROICalculation", ["tenant_id"], "btree"),
    Index("r_o_i_calculation_tenant_id_idx", "ROICalculation", ["tenant_id", "id"], "btree"),
    Index("r_o_i_template_tenant_idx", "ROITemplate", ["tenant_id"], "btree"),
    Index("r_o_i_template_tenant_id_idx", "ROITemplate", ["tenant_id", "id"], "btree"),
    Index("segment_tenant_idx", "Segment", ["tenant_id"], "btree"),
    Index("segment_tenant_id_idx", "Segment", ["tenant_id", "id"], "btree"),
    Index("signal_tenant_idx", "Signal", ["tenant_id"], "btree"),
    Index("signal_tenant_id_idx", "Signal", ["tenant_id", "id"], "btree"),
    Index("source_tenant_idx", "Source", ["tenant_id"], "btree"),
    Index("source_tenant_id_idx", "Source", ["tenant_id", "id"], "btree"),
    Index("stakeholder_tenant_idx", "Stakeholder", ["tenant_id"], "btree"),
    Index("stakeholder_tenant_id_idx", "Stakeholder", ["tenant_id", "id"], "btree"),
    Index("value_lever_tenant_idx", "ValueLever", ["tenant_id"], "btree"),
    Index("value_lever_tenant_id_idx", "ValueLever", ["tenant_id", "id"], "btree"),
    Index("value_tree_tenant_idx", "ValueTree", ["tenant_id"], "btree"),
    Index("value_tree_tenant_id_idx", "ValueTree", ["tenant_id", "id"], "btree"),
    # Complete tenant label registry lookup coverage.
    Index("benchmark_tenant_id_idx", "Benchmark", ["tenant_id", "id"], "btree"),
    Index("benchmark_dataset_tenant_id_idx", "BenchmarkDataset", ["tenant_id", "id"], "btree"),
    Index("formula_version_tenant_id_idx", "FormulaVersion", ["tenant_id", "id"], "btree"),
    Index("product_tenant_id_idx", "Product", ["tenant_id", "id"], "btree"),
    Index("value_pack_tenant_id_idx", "ValuePack", ["tenant_id", "id"], "btree"),
    Index("variable_tenant_id_idx", "Variable", ["tenant_id", "id"], "btree"),
    # Composite index for common query pattern: tenant_id + id lookup
    Index("capability_tenant_id_idx", "Capability", ["tenant_id", "id"], "btree"),
    Index("usecase_tenant_id_idx", "UseCase", ["tenant_id", "id"], "btree"),
    Index("persona_tenant_id_idx", "Persona", ["tenant_id", "id"], "btree"),
    Index("valuedriver_tenant_id_idx", "ValueDriver", ["tenant_id", "id"], "btree"),
    # B-tree indexes for filtering
    Index("capability_name_idx", "Capability", ["name"], "btree"),
    Index("capability_confidence_idx", "Capability", ["confidence"], "btree"),
    Index("capability_level_idx", "Capability", ["capabilityLevel"], "btree"),
    Index("usecase_name_idx", "UseCase", ["name"], "btree"),
    Index("usecase_confidence_idx", "UseCase", ["confidence"], "btree"),
    Index("usecase_criticality_idx", "UseCase", ["businessCriticality"], "btree"),
    Index("persona_name_idx", "Persona", ["name"], "btree"),  # Fixed: was "title"
    Index("persona_department_idx", "Persona", ["department"], "btree"),
    Index("persona_roletype_idx", "Persona", ["role_type"], "btree"),
    Index(
        "persona_roletype_idx2", "Persona", ["roleType"], "btree"
    ),  # camelCase variant
    Index("valuedriver_name_idx", "ValueDriver", ["name"], "btree"),
    Index("valuedriver_category_idx", "ValueDriver", ["category"], "btree"),
    Index("valuedriver_valuecategory_idx", "ValueDriver", ["valueCategory"], "btree"),
    Index("valuemetric_name_idx", "ValueMetric", ["name"], "btree"),
    Index("product_name_idx", "Product", ["name"], "btree"),
    Index("product_vendor_idx", "Product", ["vendor"], "btree"),
    Index("feature_name_idx", "Feature", ["name"], "btree"),
    Index("apqcprocess_apqcid_idx", "APQCProcess", ["apqcId"], "btree"),
    Index("bianservicedomain_bianid_idx", "BIANServiceDomain", ["bianId"], "btree"),
    # Full-text indexes for search
    Index("capability_fulltext", "Capability", ["name", "description"], "fulltext"),
    Index("usecase_fulltext", "UseCase", ["name", "description"], "fulltext"),
    Index(
        "persona_fulltext", "Persona", ["name", "description", "department"], "fulltext"
    ),  # Fixed
    Index("valuedriver_fulltext", "ValueDriver", ["name", "description"], "fulltext"),
    Index("valuemetric_fulltext", "ValueMetric", ["name", "description"], "fulltext"),
    Index("product_fulltext", "Product", ["name", "description"], "fulltext"),
    Index("feature_fulltext", "Feature", ["name", "description"], "fulltext"),
    # Vector indexes for current retrieval entities.
    Index("capability_embedding_idx", "Capability", ["embedding"], "vector"),
    Index("usecase_embedding_idx", "UseCase", ["embedding"], "vector"),
    Index("persona_embedding_idx", "Persona", ["embedding"], "vector"),
    Index("valuedriver_embedding_idx", "ValueDriver", ["embedding"], "vector"),
    # NOTE: LOOKUP index for efficient label scanning
    # Neo4j 5.x automatically creates token lookup indexes, so we don't need to create it manually
    # Index("entity_lookup", "", [], "lookup"),  # Commented out - auto-created by Neo4j 5.x
    # Phase 2: Value Pack and Variable indexes
    Index("valuepack_name_idx", "ValuePack", ["name"], "btree"),
    Index("valuepack_industry_idx", "ValuePack", ["industry"], "btree"),
    Index("valuepack_status_idx", "ValuePack", ["status"], "btree"),
    Index("valuepack_fulltext", "ValuePack", ["name", "description"], "fulltext"),
    # Composite (tenant_id, name) indexes for efficient tenant-scoped name lookups
    Index("capability_tenant_name_idx", "Capability", ["tenant_id", "name"], "btree"),
    Index("usecase_tenant_name_idx", "UseCase", ["tenant_id", "name"], "btree"),
    Index("persona_tenant_name_idx", "Persona", ["tenant_id", "name"], "btree"),
    Index("valuedriver_tenant_name_idx", "ValueDriver", ["tenant_id", "name"], "btree"),
    Index("product_tenant_name_idx", "Product", ["tenant_id", "name"], "btree"),
    Index("organization_tenant_name_idx", "Organization", ["tenant_id", "name"], "btree"),
    Index("painsignal_tenant_name_idx", "PainSignal", ["tenant_id", "name"], "btree"),
    Index("evidence_tenant_name_idx", "Evidence", ["tenant_id", "name"], "btree"),
    Index("variable_name_idx", "Variable", ["name"], "btree"),
    Index("variable_datatype_idx", "Variable", ["dataType"], "btree"),
    Index("variable_industry_idx", "Variable", ["industry"], "btree"),
    Index("variable_fulltext", "Variable", ["name", "description"], "fulltext"),
    Index("benchmarkdataset_name_idx", "BenchmarkDataset", ["name"], "btree"),
    Index("benchmarkdataset_industry_idx", "BenchmarkDataset", ["industry"], "btree"),
    # Phase 3: Signal extraction indexes
    Index("painsignal_tenant_idx", "PainSignal", ["tenant_id"], "btree"),
    Index("painsignal_account_idx", "PainSignal", ["account_id"], "btree"),
    Index("painsignal_tenant_id_idx", "PainSignal", ["tenant_id", "id"], "btree"),
    Index("painsignal_category_idx", "PainSignal", ["category"], "btree"),
    Index("painsignal_confidence_idx", "PainSignal", ["confidence_score"], "btree"),
    Index("painsignal_name_idx", "PainSignal", ["name"], "btree"),
    Index("painsignal_fulltext", "PainSignal", ["name", "description"], "fulltext"),
    # Evidence indexes for vector search
    Index("evidence_tenant_idx", "Evidence", ["tenant_id"], "btree"),
    Index("evidence_tenant_id_idx", "Evidence", ["tenant_id", "id"], "btree"),
    Index("evidence_type_idx", "Evidence", ["evidence_type"], "btree"),
    Index("evidence_industry_idx", "Evidence", ["industry"], "btree"),
    Index("evidence_fulltext", "Evidence", ["title", "content"], "fulltext"),
    # Vector index for evidence semantic search
    Index("evidence_embedding_idx", "Evidence", ["embedding"], "vector"),
]

# Schema initialization order
SCHEMA_INIT_ORDER = [
    "constraints",
    "indexes",
    "entity_labels",
    "relationship_types",
]


def get_all_constraints() -> list[Constraint]:
    """Get all schema constraints."""
    return CONSTRAINTS


def get_tenant_constraints(edition: str = "community") -> list[Constraint]:
    """Get tenant isolation constraints (P0-03).

    These require Neo4j Enterprise Edition. Returns empty list for
    Community Edition compatibility.

    Args:
        edition: Neo4j edition string ("community" or "enterprise")

    Returns:
        List of tenant constraints for Enterprise, empty list for Community
    """
    if "enterprise" in edition.lower():
        return TENANT_CONSTRAINTS
    return []  # Community Edition doesn't support EXISTS constraints


def get_all_constraints_with_tenant(include_tenant: bool = False) -> list[Constraint]:
    """Get all constraints, optionally including tenant constraints.

    Args:
        include_tenant: If True, includes TENANT_CONSTRAINTS (Enterprise only)

    Returns:
        Combined list of constraints
    """
    if include_tenant:
        return CONSTRAINTS + TENANT_CONSTRAINTS
    return CONSTRAINTS


def get_all_indexes() -> list[Index]:
    """Get all schema indexes."""
    return INDEXES


def get_entity_types() -> list[str]:
    """Get all entity types in the ontology."""
    return ENTITY_TYPES


def get_relationship_types() -> list[str]:
    """Get all relationship types in the ontology."""
    return RELATIONSHIP_TYPES


def get_constraints_for_edition(edition: str = "community") -> list[Constraint]:
    """Get constraints appropriate for the Neo4j edition.

    This helper allows external code to check which constraints will be
    created based on the detected Neo4j edition.

    Args:
        edition: Neo4j edition string ("community", "enterprise", etc.)

    Returns:
        List of constraints that will be created for this edition.
        Enterprise Edition gets all constraints including property existence.
        Community Edition gets only unique constraints.
    """
    edition_lower = edition.lower()
    if edition_lower == "enterprise":
        return CONSTRAINTS + TENANT_CONSTRAINTS
    else:
        # Community and unknown editions get only Community-compatible constraints
        return CONSTRAINTS
