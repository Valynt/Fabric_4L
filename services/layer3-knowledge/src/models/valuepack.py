"""
ValuePack Framework v1.0 - Pydantic Models

Complete schema implementation for industry-specific value model templates.
All 8 industries: Enterprise SaaS, Healthcare, Manufacturing, Financial Services,
Energy, Retail, Logistics, Public Sector.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValuePackTier(int, Enum):
    """Tier classification for ValuePacks."""

    IMMEDIATE_TRACTION = 1  # Quick wins, easy implementation
    HIGH_ROI_UNDERSERVED = 2  # Strong value, less competition
    COMPLEX_BUT_POWERFUL = 3  # High effort, high reward


class SwitchingCost(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataRichness(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FeedbackLoopSpeed(str, Enum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class EvidenceLevel(int, Enum):
    """Universal evidence hierarchy (Level 1 = highest)."""

    PEER_REVIEWED_AUDITED = 1
    THIRD_PARTY_VALIDATED = 2
    CUSTOMER_MEASURED = 3
    PLATFORM_BENCHMARKED = 4
    INDUSTRY_ESTIMATED = 5


class ValueDriver(BaseModel):
    """A primary value driver that moves money for this industry."""

    id: str = Field(..., description="Unique identifier for this driver")
    name: str = Field(..., description="Human-readable driver name")
    description: str = Field(
        ..., description="What this driver means in this industry context"
    )
    typical_impact: str = Field(..., description="Typical financial impact range")
    measurement_approach: str = Field(..., description="How to measure this driver")


class CoreUseCase(BaseModel):
    """What customers actually buy - the use case."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Use case name")
    description: str = Field(..., description="Detailed description")
    target_persona: str = Field(..., description="Primary buyer/user persona")
    business_problem: str = Field(..., description="Problem this solves")


class EconomicModelType(BaseModel):
    """How value is calculated for this industry."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Model name")
    formula_shape: str = Field(
        ..., description="Input → Calculation → Output structure"
    )
    inputs: list[str] = Field(
        default_factory=list, description="Required input variables"
    )
    output_unit: str = Field(..., description="What the output represents")
    typical_range: str | None = Field(None, description="Typical output range")


class ProofRequirement(BaseModel):
    """What makes a value claim credible in this industry."""

    id: str = Field(..., description="Unique identifier")
    requirement: str = Field(..., description="What proof is required")
    evidence_type: str = Field(..., description="Type of evidence needed")
    minimum_level: EvidenceLevel = Field(
        ..., description="Minimum evidence hierarchy level"
    )


class WinStatement(BaseModel):
    """Why THIS platform is uniquely strong for this industry."""

    statement: str = Field(..., description="The win statement")
    differentiation: str = Field(
        ..., description="How this differs from generic claims"
    )
    proof_point: str = Field(..., description="Specific evidence supporting this claim")


class EndpointContribution(BaseModel):
    """What this ValuePack contributes to a specific endpoint."""

    enabled: bool = Field(default=True)
    contribution_summary: str = Field(..., description="What this ValuePack adds")
    data_format: str = Field(..., description="Format of contribution")
    specific_assets: list[str] = Field(
        default_factory=list, description="Asset IDs/URLs"
    )


class EndpointMappings(BaseModel):
    """How this ValuePack maps to each of the 5 product endpoints."""

    intelligence: EndpointContribution = Field(..., description="Context enrichment")
    ai_model: EndpointContribution = Field(..., description="Hypothesis generation")
    driver_tree: EndpointContribution = Field(..., description="Pre-built structures")
    calculator: EndpointContribution = Field(..., description="Pre-defined formulas")
    value_case: EndpointContribution = Field(
        ..., description="Industry-specific narratives"
    )


class ComposableModelTemplate(BaseModel):
    """Reusable calculation pattern that works across industries."""

    template_id: str = Field(..., description="Unique template identifier")
    template_name: str = Field(..., description="Human-readable name")
    formula_pattern: str = Field(..., description="Mathematical pattern")
    inputs_required: list[str] = Field(..., description="Input variables")
    output_definition: str = Field(..., description="What this calculates")
    applicable_industries: list[str] = Field(
        ..., description="Industry IDs using this template"
    )
    example_calculation: str = Field(..., description="Concrete example")


class OntologyTag(BaseModel):
    """Taxonomy tag for cross-industry linkage."""

    tag: str = Field(..., description="Tag name")
    category: str = Field(..., description="Tag category (driver, model, proof, etc.)")
    related_tags: list[str] = Field(default_factory=list, description="Related tags")


class EconomicNode(BaseModel):
    """Node in the pre-built economic graph."""

    node_id: str = Field(..., description="Unique node ID")
    node_type: Literal["driver", "intervention", "outcome", "metric"] = Field(...)
    name: str = Field(..., description="Node name")
    description: str = Field(..., description="Node description")
    default_value: str | None = Field(None, description="Default/typical value")


class EconomicRelationship(BaseModel):
    """Relationship between nodes in the economic graph."""

    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    relationship_type: Literal["drives", "enables", "measures", "depends_on"] = Field(
        ...
    )
    weight: float | None = Field(None, description="Relationship strength 0-1")
    formula: str | None = Field(None, description="Calculation between nodes")


class PreBuiltEconomicGraph(BaseModel):
    """Pre-built driver-tree skeleton with node relationships."""

    nodes: list[EconomicNode] = Field(..., description="All nodes in the graph")
    relationships: list[EconomicRelationship] = Field(
        ..., description="Node relationships"
    )
    root_node_id: str = Field(..., description="Root node of the graph")
    graph_description: str = Field(..., description="What this graph represents")


class EvidenceHierarchyRule(BaseModel):
    """Validation rule for evidence in this industry."""

    level: EvidenceLevel = Field(..., description="Hierarchy level")
    label: str = Field(..., description="Human-readable label")
    requirements: list[str] = Field(..., description="Requirements to meet this level")
    acceptable_sources: list[str] = Field(
        ..., description="Acceptable evidence sources"
    )


class EvidenceFramework(BaseModel):
    """Evidence types, hierarchy, and validation rules."""

    hierarchy: list[EvidenceHierarchyRule] = Field(..., description="Evidence ranking")
    required_level: EvidenceLevel = Field(
        ..., description="Minimum level for this industry"
    )
    validation_rules: list[str] = Field(
        default_factory=list, description="Custom validation"
    )


class ValuePackMetadata(BaseModel):
    """Metadata about this ValuePack's market characteristics."""

    deal_size_range: str = Field(..., description="Typical deal size")
    sales_cycle_length: str = Field(..., description="Typical sales cycle")
    switching_cost: SwitchingCost = Field(
        ..., description="Customer switching difficulty"
    )
    data_richness: DataRichness = Field(
        ..., description="Data availability in industry"
    )
    feedback_loop_speed: FeedbackLoopSpeed = Field(
        ..., description="Speed of value realization"
    )


class ValuePackBase(BaseModel):
    """Core ValuePack schema v1.0 fields."""

    industry_id: str = Field(
        ..., description="Unique industry slug", pattern=r"^[a-z0-9_-]+$"
    )
    tier: ValuePackTier = Field(..., description="ValuePack tier classification")
    display_name: str = Field(..., description="Human-readable industry name")
    description: str = Field(..., description="Industry overview")

    primary_value_drivers: list[ValueDriver] = Field(
        ..., min_length=1, max_length=4, description="What moves money (max 4)"
    )
    core_use_cases: list[CoreUseCase] = Field(
        ..., min_length=1, max_length=4, description="What customers buy (max 4)"
    )
    economic_model_types: list[EconomicModelType] = Field(
        ..., min_length=1, max_length=4, description="How value is calculated (max 4)"
    )
    proof_requirements: list[ProofRequirement] = Field(
        ..., min_length=1, max_length=3, description="What makes it credible (max 3)"
    )
    why_it_wins: list[WinStatement] = Field(
        ..., min_length=1, max_length=3, description="Platform differentiation (max 3)"
    )

    endpoint_mappings: EndpointMappings = Field(
        ..., description="5 endpoint contributions"
    )
    composable_model_templates: list[ComposableModelTemplate] = Field(
        default_factory=list, description="Reusable calculation patterns"
    )
    pre_wired_ontology_tags: list[OntologyTag] = Field(
        default_factory=list, description="Taxonomy tags"
    )
    pre_built_economic_graph: PreBuiltEconomicGraph = Field(
        ..., description="Driver-tree skeleton"
    )
    evidence_framework: EvidenceFramework = Field(
        ..., description="Evidence hierarchy and rules"
    )
    metadata: ValuePackMetadata = Field(..., description="Market characteristics")

    # System fields
    version: str = Field(default="1.0", description="Schema version")
    is_active: bool = Field(
        default=True, description="Whether this ValuePack is active"
    )
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")

    @field_validator("primary_value_drivers")
    @classmethod
    def validate_unique_driver_ids(cls, v):
        ids = [d.id for d in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Value driver IDs must be unique")
        return v

    @field_validator("primary_value_drivers")
    @classmethod
    def validate_driver_uniqueness_text(cls, v):
        """Ensure drivers are sufficiently differentiated (not copy-pasteable to other industries)."""
        # This is validated at creation time by comparing against existing ValuePacks
        return v


class ValuePackCreate(ValuePackBase):
    """Model for creating a new ValuePack."""

    pass


class ValuePackUpdate(BaseModel):
    """Model for updating an existing ValuePack."""

    tier: ValuePackTier | None = None
    display_name: str | None = None
    description: str | None = None
    primary_value_drivers: list[ValueDriver] | None = None
    core_use_cases: list[CoreUseCase] | None = None
    economic_model_types: list[EconomicModelType] | None = None
    proof_requirements: list[ProofRequirement] | None = None
    why_it_wins: list[WinStatement] | None = None
    endpoint_mappings: EndpointMappings | None = None
    composable_model_templates: list[ComposableModelTemplate] | None = None
    pre_wired_ontology_tags: list[OntologyTag] | None = None
    pre_built_economic_graph: PreBuiltEconomicGraph | None = None
    evidence_framework: EvidenceFramework | None = None
    metadata: ValuePackMetadata | None = None
    is_active: bool | None = None


class ValuePackResponse(ValuePackBase):
    """Model for ValuePack API responses."""

    completeness_score: float | None = Field(
        None, description="Schema completeness 0-1"
    )

    model_config = ConfigDict(from_attributes=True)


class ValuePackListResponse(BaseModel):
    """Paginated list of ValuePacks."""

    items: list[ValuePackResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class OntologyMapResponse(BaseModel):
    """Cross-industry ontology map response."""

    shared_drivers: list[dict[str, Any]] = Field(
        ..., description="Value drivers appearing across industries"
    )
    shared_model_types: list[dict[str, Any]] = Field(
        ..., description="Model types used across industries"
    )
    shared_proof_patterns: list[dict[str, Any]] = Field(
        ..., description="Proof patterns used across industries"
    )
    cross_reference_matrix: dict[str, dict[str, int]] = Field(
        ..., description="Overlap density matrix"
    )


class ComposableTemplateLibraryResponse(BaseModel):
    """Composable template library response."""

    templates: list[ComposableModelTemplate] = Field(
        ..., description="All reusable templates"
    )
    template_usage: dict[str, list[str]] = Field(
        ..., description="Template ID -> Industry IDs using it"
    )


class ValuePackComparisonRequest(BaseModel):
    """Request to compare multiple ValuePacks."""

    industry_ids: list[str] = Field(
        ..., min_length=2, max_length=5, description="Industries to compare"
    )
    dimensions: list[str] | None = Field(
        None, description="Specific dimensions to compare"
    )


class ValuePackComparisonResponse(BaseModel):
    """Response for ValuePack comparison."""

    valuepacks: list[ValuePackResponse] = Field(..., description="Full ValuePack data")
    comparison_matrix: dict[str, dict[str, Any]] = Field(
        ..., description="Dimension-by-dimension comparison"
    )
    shared_templates: list[str] = Field(
        ..., description="Templates shared between industries"
    )
    differentiation_analysis: dict[str, str] = Field(
        ..., description="Analysis of unique aspects"
    )


# Pre-built data for the 8 industries
ENTERPRISE_SAAS_VALUEPACK = ValuePackCreate(
    industry_id="enterprise_saas",
    tier=ValuePackTier.IMMEDIATE_TRACTION,
    display_name="Enterprise SaaS (AI / Data Platforms)",
    description="Labor replacement/augmentation, revenue uplift, cost efficiency, retention/expansion",
    primary_value_drivers=[
        ValueDriver(
            id="headcount_efficiency",
            name="Headcount Efficiency",
            description="Reduce manual work through AI automation",
            typical_impact="20-40% time savings",
            measurement_approach="Time tracking before/after",
        ),
        ValueDriver(
            id="revenue_uplift",
            name="Revenue Uplift",
            description="Increase revenue through better customer insights",
            typical_impact="10-25% ARR growth",
            measurement_approach="Revenue attribution analysis",
        ),
        ValueDriver(
            id="cost_avoidance",
            name="Cost Avoidance",
            description="Prevent costs through early issue detection",
            typical_impact="$500K-2M annual savings",
            measurement_approach="Issue prevention tracking",
        ),
        ValueDriver(
            id="retention_expansion",
            name="Retention & Expansion",
            description="Improve customer retention and expand accounts",
            typical_impact="5-15% churn reduction",
            measurement_approach="Churn rate analysis",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="ai_copilots",
            name="AI Copilots",
            description="AI assistants for customer-facing teams",
            target_persona="Customer Success Manager",
            business_problem="Manual research and response drafting",
        ),
        CoreUseCase(
            id="data_platform",
            name="Data Platform Economics",
            description="Unified customer data platform",
            target_persona="Revenue Operations",
            business_problem="Data silos and inconsistent metrics",
        ),
        CoreUseCase(
            id="revops_gtm",
            name="RevOps/GTM Tooling",
            description="Revenue operations and go-to-market tools",
            target_persona="VP Revenue Operations",
            business_problem="Pipeline visibility and forecasting",
        ),
        CoreUseCase(
            id="cs_optimization",
            name="CS Optimization",
            description="Customer success workflow optimization",
            target_persona="VP Customer Success",
            business_problem="Scale CS without linear headcount",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="headcount_displacement",
            name="Headcount Displacement Model",
            formula_shape="(Hours Saved × Hourly Rate × Headcount) - Tool Cost = Net Value",
            inputs=[
                "hours_saved_per_week",
                "hourly_rate",
                "affected_headcount",
                "tool_annual_cost",
            ],
            output_unit="Annual savings $",
            typical_range="$200K-1M",
        ),
        EconomicModelType(
            id="pipeline_velocity",
            name="Pipeline Velocity Model",
            formula_shape="(Deal Count × Win Rate Increase × Avg Deal Size) - Cost = Incremental Revenue",
            inputs=[
                "annual_deal_count",
                "win_rate_improvement_pct",
                "avg_deal_size",
                "tool_cost",
            ],
            output_unit="Annual revenue uplift $",
            typical_range="$500K-5M",
        ),
        EconomicModelType(
            id="ltv_churn",
            name="LTV/Churn Reduction Model",
            formula_shape="(Customers × Churn Reduction × LTV) - Cost = Retained Value",
            inputs=[
                "customer_count",
                "churn_reduction_pct",
                "customer_ltv",
                "tool_cost",
            ],
            output_unit="Retained annual revenue $",
            typical_range="$300K-2M",
        ),
        EconomicModelType(
            id="cost_per_query",
            name="Cost-Per-Query Model",
            formula_shape="(Query Volume × Old Cost Per Query × Reduction) - New Platform Cost = Savings",
            inputs=[
                "monthly_queries",
                "old_cost_per_query",
                "cost_reduction_pct",
                "platform_cost",
            ],
            output_unit="Monthly savings $",
            typical_range="$10K-100K",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="benchmarks",
            requirement="Platform benchmarks",
            evidence_type="Internal benchmark data",
            minimum_level=EvidenceLevel.PLATFORM_BENCHMARKED,
        ),
        ProofRequirement(
            id="usage_outcome",
            requirement="Usage-to-outcome linkage",
            evidence_type="Correlation analysis",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
        ProofRequirement(
            id="scenario_modeling",
            requirement="Scenario modeling",
            evidence_type="Customer-specific model",
            minimum_level=EvidenceLevel.INDUSTRY_ESTIMATED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Native sales cycle fit—value conversations embedded in SaaS buying process",
            differentiation="Unlike horizontal tools, our platform is designed for SaaS-specific value chains",
            proof_point="87% of SaaS customers cite 'native value approach' as key differentiator",
        ),
        WinStatement(
            statement="CFO-driven buying standard—built for finance scrutiny from day one",
            differentiation="Pre-answers CFO questions with audit-ready evidence frameworks",
            proof_point="Average CFO approval time reduced from 6 weeks to 2 weeks",
        ),
        WinStatement(
            statement="High model repeatability—SaaS value drivers are consistent across accounts",
            differentiation="Unlike custom consulting models, our SaaS templates work out of the box",
            proof_point="78% of SaaS implementations use standard templates with minimal customization",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Industry-specific signals: funding rounds, hiring velocity, tech stack changes",
            data_format="Structured enrichment data",
            specific_assets=["saas_intelligence_feed", "growth_signals_api"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Pre-trained on 500+ SaaS value models for instant hypothesis generation",
            data_format="ML model weights + inference API",
            specific_assets=["saas_value_model_v2", "expansion_predictor"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="SaaS-specific driver trees: acquisition, expansion, retention economics",
            data_format="JSON driver tree definitions",
            specific_assets=["saas_driver_tree_standard", "expansion_driver_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Pre-built calculators: CAC payback, net revenue retention, magic number",
            data_format="Formula definitions + UI components",
            specific_assets=["cac_calculator", "nrr_calculator", "magic_number_calc"],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Board-ready SaaS narratives with standard metrics (ARR, NRR, GRR, CAC)",
            data_format="Narrative templates + data bindings",
            specific_assets=["board_presentation_template", "cfo_summary_template"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="headcount_displacement",
            template_name="Headcount Displacement Model",
            formula_pattern="(Hours × Rate × Count) - Cost",
            inputs_required=["hours", "hourly_rate", "headcount", "tool_cost"],
            output_definition="Annual labor cost savings",
            applicable_industries=[
                "enterprise_saas",
                "healthcare",
                "financial_services",
                "public_sector",
            ],
            example_calculation="(10 hours/week × $75/hr × 50 reps) - $100K tool cost = $1.85M savings",
        ),
        ComposableModelTemplate(
            template_id="efficiency_uplift",
            template_name="Efficiency Uplift Model",
            formula_pattern="(Baseline Output × Improvement % × Value Per Output) - Investment",
            inputs_required=[
                "baseline_output",
                "improvement_pct",
                "value_per_unit",
                "investment",
            ],
            output_definition="Annual value from productivity gains",
            applicable_industries=[
                "enterprise_saas",
                "manufacturing",
                "financial_services",
            ],
            example_calculation="(1000 calls/week × 15% improvement × $500/call) - $50K = $625K",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="saas",
            category="industry",
            related_tags=["b2b", "subscription", "recurring_revenue"],
        ),
        OntologyTag(
            tag="ai_copilot",
            category="capability",
            related_tags=["automation", "productivity", "augmentation"],
        ),
        OntologyTag(
            tag="headcount_efficiency",
            category="value_driver",
            related_tags=["labor_cost", "productivity", "automation"],
        ),
        OntologyTag(
            tag="revenue_uplift",
            category="value_driver",
            related_tags=["growth", "expansion", "retention"],
        ),
        OntologyTag(
            tag="customer_ltv",
            category="value_driver",
            related_tags=["retention", "expansion", "growth"],
        ),
        OntologyTag(
            tag="compliance",
            category="compliance",
            related_tags=["soc2", "gdpr", "security"],
        ),
        OntologyTag(
            tag="cac_payback",
            category="economic_model",
            related_tags=["acquisition", "efficiency", "unit_economics"],
        ),
        OntologyTag(
            tag="nrr",
            category="economic_model",
            related_tags=["retention", "expansion", "recurring_revenue"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_arr",
                node_type="driver",
                name="Total ARR",
                description="Annual recurring revenue",
                default_value="$10M",
            ),
            EconomicNode(
                node_id="new_logo_growth",
                node_type="driver",
                name="New Logo Growth",
                description="Acquisition revenue",
                default_value="$3M",
            ),
            EconomicNode(
                node_id="expansion_revenue",
                node_type="driver",
                name="Expansion Revenue",
                description="Upsell/cross-sell",
                default_value="$2M",
            ),
            EconomicNode(
                node_id="churned_arr",
                node_type="outcome",
                name="Churned ARR",
                description="Lost revenue",
                default_value="-$500K",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="Platform Usage",
                description="Our platform adoption",
                default_value="80%",
            ),
            EconomicNode(
                node_id="nrr_rate",
                node_type="metric",
                name="Net Revenue Retention",
                description="NRR %",
                default_value="110%",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="new_logo_growth",
                to_node_id="total_arr",
                relationship_type="drives",
                weight=1.0,
                formula="+",
            ),
            EconomicRelationship(
                from_node_id="expansion_revenue",
                to_node_id="total_arr",
                relationship_type="drives",
                weight=1.0,
                formula="+",
            ),
            EconomicRelationship(
                from_node_id="total_arr",
                to_node_id="churned_arr",
                relationship_type="enables",
                weight=-0.05,
                formula="× -0.05",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="nrr_rate",
                relationship_type="drives",
                weight=0.3,
                formula="+ 10%",
            ),
            EconomicRelationship(
                from_node_id="nrr_rate",
                to_node_id="total_arr",
                relationship_type="measures",
                weight=1.0,
            ),
        ],
        root_node_id="total_arr",
        graph_description="SaaS recurring revenue flywheel with expansion and retention mechanics",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=["Published case study", "Third-party audit"],
                acceptable_sources=["Academic journals", "Big 4 audit firms"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=[
                    "Industry analyst validation",
                    "Customer public testimonial",
                ],
                acceptable_sources=["Gartner, Forrester", "Customer blog posts"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Customer internal measurement",
                    "Before/after comparison",
                ],
                acceptable_sources=["Customer success metrics", "Internal dashboards"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Platform aggregate data",
                    "Anonymized cross-customer analysis",
                ],
                acceptable_sources=["Platform analytics", "Aggregate studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=[
                    "Industry standard assumptions",
                    "Comparable company analysis",
                ],
                acceptable_sources=["Industry reports", "Comparables analysis"],
            ),
        ],
        required_level=EvidenceLevel.PLATFORM_BENCHMARKED,
        validation_rules=[
            "Must have at least one customer-measured data point",
            "ROI claims must have time-bound measurements",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$50K-500K ACV",
        sales_cycle_length="2-6 months",
        switching_cost=SwitchingCost.MEDIUM,
        data_richness=DataRichness.HIGH,
        feedback_loop_speed=FeedbackLoopSpeed.FAST,
    ),
)


# Export all 8 industries - COMPLETE

HEALTHCARE_VALUEPACK = ValuePackCreate(
    industry_id="healthcare_medtech",
    tier=ValuePackTier.IMMEDIATE_TRACTION,
    display_name="Healthcare & MedTech",
    description="Cost avoidance, outcome optimization, compliance, patient throughput - immediate, measurable, high-stakes value",
    primary_value_drivers=[
        ValueDriver(
            id="cost_avoidance",
            name="Cost Avoidance",
            description="Reduce healthcare costs through early detection and prevention",
            typical_impact="$500K-2M per preventable event",
            measurement_approach="Episode cost tracking and prevention metrics",
        ),
        ValueDriver(
            id="outcome_optimization",
            name="Outcome Optimization",
            description="Improve clinical outcomes and patient satisfaction scores",
            typical_impact="10-25% improvement in quality metrics",
            measurement_approach="HCAHPS scores, readmission rates, mortality indices",
        ),
        ValueDriver(
            id="compliance_automation",
            name="Compliance Automation",
            description="Automate regulatory compliance and documentation",
            typical_impact="$300K-1M annual compliance cost reduction",
            measurement_approach="Audit findings reduction, documentation time",
        ),
        ValueDriver(
            id="patient_throughput",
            name="Patient Throughput",
            description="Increase patient volume without linear resource increase",
            typical_impact="15-30% capacity increase",
            measurement_approach="Bed turnover, OR utilization, ED length of stay",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="readmission_reduction",
            name="Readmission Reduction",
            description="AI-powered readmission risk prediction and intervention",
            target_persona="Chief Medical Officer",
            business_problem="CMS penalties for excessive readmissions",
        ),
        CoreUseCase(
            id="clinical_documentation",
            name="Clinical Documentation Improvement",
            description="Automate coding and documentation for revenue capture",
            target_persona="Revenue Cycle Director",
            business_problem="Undercoding and missed revenue opportunities",
        ),
        CoreUseCase(
            id="capacity_optimization",
            name="Capacity Optimization",
            description="Predictive bed management and resource allocation",
            target_persona="Chief Operating Officer",
            business_problem="Emergency department boarding and throughput delays",
        ),
        CoreUseCase(
            id="quality_reporting",
            name="Automated Quality Reporting",
            description="Streamline MIPS, HEDIS, and quality measure reporting",
            target_persona="Quality Director",
            business_problem="Manual quality metric extraction and reporting burden",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="readmission_prevention",
            name="Readmission Prevention Model",
            formula_shape="(Readmissions Prevented × Cost Per Readmission) + (CMS Penalty Avoidance) = Total Savings",
            inputs=[
                "baseline_readmission_rate",
                "target_reduction_pct",
                "annual_admissions",
                "cost_per_readmission",
                "cms_penalty_risk",
            ],
            output_unit="Annual cost avoidance $",
            typical_range="$1M-5M",
        ),
        EconomicModelType(
            id="revenue_capture",
            name="Clinical Documentation Revenue Capture",
            formula_shape="(Cases × Severity Adjustment × Revenue Per Case) - Implementation Cost = Incremental Revenue",
            inputs=[
                "annual_cases",
                "complexity_uplift_pct",
                "avg_revenue_per_case",
                "implementation_cost",
            ],
            output_unit="Annual revenue uplift $",
            typical_range="$500K-3M",
        ),
        EconomicModelType(
            id="throughput_efficiency",
            name="Patient Throughput Efficiency",
            formula_shape="(Additional Patients × Margin Per Patient) - Platform Cost = Net Value",
            inputs=[
                "current_capacity",
                "utilization_improvement_pct",
                "patients_per_unit",
                "margin_per_encounter",
            ],
            output_unit="Annual margin contribution $",
            typical_range="$2M-10M",
        ),
        EconomicModelType(
            id="compliance_cost",
            name="Compliance Cost Reduction",
            formula_shape="(Audit Hours Saved × Cost Per Hour) + (Penalty Avoidance) + (Staff Efficiency) = Savings",
            inputs=[
                "audit_hours_annual",
                "hourly_cost",
                "historical_penalties",
                "fte_hours_saved",
            ],
            output_unit="Annual cost reduction $",
            typical_range="$300K-1.5M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="clinical_validation",
            requirement="Clinical outcome validation",
            evidence_type="Peer-reviewed studies",
            minimum_level=EvidenceLevel.PEER_REVIEWED_AUDITED,
        ),
        ProofRequirement(
            id="regulatory_alignment",
            requirement="Regulatory requirement alignment",
            evidence_type="HIPAA compliance, FDA clearance where applicable",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="roi_documentation",
            requirement="ROI documentation with patient-level tracking",
            evidence_type="Customer case studies with PHI anonymization",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Clinical validation standard—peer-reviewed outcomes, not just efficiency claims",
            differentiation="Unlike administrative tools, our platform demonstrates measurable clinical outcome improvements",
            proof_point="Published in 12 peer-reviewed journals with average 23% outcome improvement",
        ),
        WinStatement(
            statement="Regulatory defensibility—built for CMS, Joint Commission, state health department scrutiny",
            differentiation="Pre-validated against regulatory requirements, not retrofitted after audits",
            proof_point="98% audit pass rate vs. 73% industry average",
        ),
        WinStatement(
            statement="Physician workflow native—integrated into clinical decision-making, not administrative burden",
            differentiation="Embedded in EHR workflows vs. separate systems requiring dual documentation",
            proof_point="94% physician adoption rate vs. 34% for non-integrated solutions",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Clinical intelligence: outcome benchmarks, regulatory updates, evidence feeds",
            data_format="FHIR-compatible clinical data enrichment",
            specific_assets=["clinical_benchmarks_api", "regulatory_alert_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="MedTech-specific models: readmission risk, sepsis prediction, length-of-stay",
            data_format="ML models with clinical validation",
            specific_assets=["readmission_predictor_v3", "sepsis_early_warning"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Clinical outcome driver trees: quality → satisfaction → financial performance",
            data_format="Healthcare-specific driver relationships",
            specific_assets=["clinical_quality_tree", "revenue_cycle_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="CMS calculators: MIPS scoring, HCC risk adjustment, quality measures",
            data_format="Regulatory-compliant calculation engines",
            specific_assets=[
                "mips_calculator",
                "hcc_risk_adjustor",
                "quality_measure_calc",
            ],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Board-ready clinical narratives with outcome metrics and compliance alignment",
            data_format="Clinical narratives + data visualizations",
            specific_assets=["cmo_presentation_template", "board_quality_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="outcome_improvement",
            template_name="Clinical Outcome Improvement Model",
            formula_pattern="(Baseline Rate - Target Rate) × Volume × Cost Per Event",
            inputs_required=[
                "baseline_rate",
                "target_rate",
                "annual_volume",
                "cost_per_event",
            ],
            output_definition="Annual value from outcome improvement",
            applicable_industries=["healthcare_medtech", "public_sector"],
            example_calculation="(15% readmission rate - 12%) × 10,000 admissions × $15K = $4.5M savings",
        ),
        ComposableModelTemplate(
            template_id="compliance_automation",
            template_name="Compliance Automation ROI",
            formula_pattern="(Manual Hours × Hourly Cost × FTEs) + Penalty Risk - Platform Cost",
            inputs_required=[
                "manual_hours",
                "hourly_cost",
                "compliance_ftes",
                "penalty_exposure",
                "platform_cost",
            ],
            output_definition="Annual compliance cost reduction",
            applicable_industries=[
                "healthcare_medtech",
                "financial_services",
                "public_sector",
            ],
            example_calculation="(40 hrs/week × $85/hr × 3 FTEs) + $500K risk - $200K = $720K savings",
        ),
        ComposableModelTemplate(
            template_id="headcount_displacement",
            template_name="Headcount Displacement Model",
            formula_pattern="(Hours × Rate × Count) - Cost",
            inputs_required=["hours", "hourly_rate", "headcount", "tool_cost"],
            output_definition="Annual labor cost savings",
            applicable_industries=[
                "enterprise_saas",
                "healthcare",
                "financial_services",
                "public_sector",
            ],
            example_calculation="(10 hours/week × $75/hr × 50 reps) - $100K tool cost = $1.85M savings",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="healthcare",
            category="industry",
            related_tags=["medtech", "provider", "payer"],
        ),
        OntologyTag(
            tag="clinical_outcome",
            category="value_driver",
            related_tags=["quality", "safety", "satisfaction"],
        ),
        OntologyTag(
            tag="readmission",
            category="value_driver",
            related_tags=["cms", "penalty", "prevention"],
        ),
        OntologyTag(
            tag="revenue_capture",
            category="value_driver",
            related_tags=["coding", "documentation", "billing"],
        ),
        OntologyTag(
            tag="compliance",
            category="compliance",
            related_tags=["hipaa", "privacy", "security", "phi"],
        ),
        OntologyTag(
            tag="hipaa",
            category="compliance",
            related_tags=["privacy", "security", "phi"],
        ),
        OntologyTag(
            tag="mips",
            category="economic_model",
            related_tags=["quality", "cms", "reimbursement"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_revenue",
                node_type="driver",
                name="Total Revenue",
                description="Net patient revenue",
                default_value="$100M",
            ),
            EconomicNode(
                node_id="readmission_costs",
                node_type="driver",
                name="Readmission Costs",
                description="Cost of 30-day readmissions",
                default_value="$8M",
            ),
            EconomicNode(
                node_id="cms_penalties",
                node_type="driver",
                name="CMS Penalties",
                description="Hospital Readmissions Reduction Program penalties",
                default_value="$1.5M",
            ),
            EconomicNode(
                node_id="quality_score",
                node_type="outcome",
                name="Quality Score",
                description="Composite quality metric",
                default_value="75%",
            ),
            EconomicNode(
                node_id="patient_satisfaction",
                node_type="outcome",
                name="Patient Satisfaction",
                description="HCAHPS scores",
                default_value="4.2/5",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Platform",
                description="Predictive analytics deployment",
                default_value="85% adoption",
            ),
            EconomicNode(
                node_id="readmission_rate",
                node_type="metric",
                name="Readmission Rate",
                description="30-day all-cause readmission rate",
                default_value="14.5%",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="readmission_rate",
                relationship_type="drives",
                weight=0.3,
                formula="-3%",
            ),
            EconomicRelationship(
                from_node_id="readmission_rate",
                to_node_id="readmission_costs",
                relationship_type="drives",
                weight=1.0,
                formula="× $15K",
            ),
            EconomicRelationship(
                from_node_id="readmission_rate",
                to_node_id="cms_penalties",
                relationship_type="drives",
                weight=0.5,
                formula="× penalty multiplier",
            ),
            EconomicRelationship(
                from_node_id="quality_score",
                to_node_id="patient_satisfaction",
                relationship_type="enables",
                weight=0.7,
            ),
            EconomicRelationship(
                from_node_id="patient_satisfaction",
                to_node_id="total_revenue",
                relationship_type="drives",
                weight=0.2,
                formula="+ market share",
            ),
            EconomicRelationship(
                from_node_id="readmission_costs",
                to_node_id="total_revenue",
                relationship_type="enables",
                weight=-0.08,
            ),
        ],
        root_node_id="total_revenue",
        graph_description="Healthcare revenue and quality flywheel with readmission cost reduction",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=["Published in medical journals", "IRB-approved studies"],
                acceptable_sources=[
                    "JAMA, NEJM, Health Affairs",
                    "Academic medical centers",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=[
                    "Industry analyst validation",
                    "Clinical workflow assessment",
                ],
                acceptable_sources=[
                    "KLAS, Gartner Healthcare",
                    "Clinical consulting firms",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Health system internal measurement",
                    "EHR-integrated tracking",
                ],
                acceptable_sources=["Health system analytics", "Clinical dashboards"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=["Cross-hospital aggregate data", "Anonymized outcomes"],
                acceptable_sources=["Platform clinical network", "Aggregate studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=[
                    "Industry standard benchmarks",
                    "Comparative effectiveness research",
                ],
                acceptable_sources=["CMS benchmarks", "AHRQ data"],
            ),
        ],
        required_level=EvidenceLevel.CUSTOMER_MEASURED,
        validation_rules=[
            "Must have IRB approval for clinical outcome claims",
            "PHI must be de-identified per HIPAA",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$200K-2M ACV",
        sales_cycle_length="3-9 months",
        switching_cost=SwitchingCost.HIGH,
        data_richness=DataRichness.HIGH,
        feedback_loop_speed=FeedbackLoopSpeed.MEDIUM,
    ),
)

MANUFACTURING_VALUEPACK = ValuePackCreate(
    industry_id="manufacturing",
    tier=ValuePackTier.HIGH_ROI_UNDERSERVED,
    display_name="Manufacturing & Industrial",
    description="Asset optimization, downtime reduction, quality improvement, supply resilience - high ROI in traditionally underserved segment",
    primary_value_drivers=[
        ValueDriver(
            id="downtime_reduction",
            name="Downtime Reduction",
            description="Minimize unplanned production line stoppages through predictive maintenance",
            typical_impact="$50K-500K per hour avoided",
            measurement_approach="MTBF/MTTR tracking with revenue attribution",
        ),
        ValueDriver(
            id="yield_improvement",
            name="Yield Improvement",
            description="Reduce scrap and rework through quality optimization",
            typical_impact="2-8% yield increase",
            measurement_approach="First-pass yield metrics, defect tracking",
        ),
        ValueDriver(
            id="energy_efficiency",
            name="Energy Efficiency",
            description="Reduce energy consumption per unit produced",
            typical_impact="10-25% energy cost reduction",
            measurement_approach="Energy monitoring per SKU, carbon tracking",
        ),
        ValueDriver(
            id="inventory_optimization",
            name="Inventory Optimization",
            description="Reduce working capital tied in raw materials and WIP",
            typical_impact="$2M-20M working capital release",
            measurement_approach="Inventory turns, days of supply, carrying cost",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="predictive_maintenance",
            name="Predictive Maintenance",
            description="AI-powered equipment failure prediction and scheduling",
            target_persona="VP Operations",
            business_problem="Unplanned downtime costing millions per hour",
        ),
        CoreUseCase(
            id="quality_control",
            name="Automated Quality Control",
            description="Computer vision and ML for defect detection",
            target_persona="Quality Director",
            business_problem="Manual inspection missing defects and slowing production",
        ),
        CoreUseCase(
            id="energy_management",
            name="Smart Energy Management",
            description="Optimize energy usage across plant operations",
            target_persona="Chief Sustainability Officer",
            business_problem="Rising energy costs and carbon reduction targets",
        ),
        CoreUseCase(
            id="supply_resilience",
            name="Supply Chain Resilience",
            description="Multi-tier supplier visibility and risk management",
            target_persona="Chief Procurement Officer",
            business_problem="Supply disruptions and lack of visibility beyond tier 1",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="downtime_avoidance",
            name="Downtime Avoidance Model",
            formula_shape="(Downtime Hours Avoided × Revenue Per Hour) + (Maintenance Cost Reduction) = Total Value",
            inputs=[
                "baseline_downtime_hours",
                "prevention_rate",
                "revenue_per_hour",
                "maintenance_savings",
            ],
            output_unit="Annual value $",
            typical_range="$5M-50M",
        ),
        EconomicModelType(
            id="yield_optimization",
            name="Yield Optimization Model",
            formula_shape="(Volume × Yield Improvement × Margin Per Unit) - Implementation Cost = Net Value",
            inputs=[
                "annual_volume",
                "yield_improvement_pct",
                "unit_margin",
                "implementation_cost",
            ],
            output_unit="Annual margin contribution $",
            typical_range="$2M-15M",
        ),
        EconomicModelType(
            id="energy_savings",
            name="Energy Savings Model",
            formula_shape="(Annual kWh × Cost Per kWh × Reduction %) + (Carbon Credit Value) = Total Savings",
            inputs=["annual_kwh", "cost_per_kwh", "reduction_pct", "carbon_price"],
            output_unit="Annual savings $",
            typical_range="$500K-5M",
        ),
        EconomicModelType(
            id="working_capital",
            name="Working Capital Optimization",
            formula_shape="(Inventory Reduction × Carrying Cost %) + (Stockout Cost Avoidance) = Value Released",
            inputs=[
                "current_inventory_value",
                "target_reduction_pct",
                "carrying_cost_rate",
                "stockout_cost_annual",
            ],
            output_unit="Working capital released $",
            typical_range="$5M-30M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="operational_validation",
            requirement="Operational validation",
            evidence_type="Time studies and OEE improvement documentation",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
        ProofRequirement(
            id="financial_verification",
            requirement="Financial verification",
            evidence_type="CFO-approved cost-benefit analysis",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="technical_integrations",
            requirement="OT/IT integration validation",
            evidence_type="SCADA/PLC integration demonstrations",
            minimum_level=EvidenceLevel.PLATFORM_BENCHMARKED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="OT/IT convergence native—unified platform from shop floor to top floor",
            differentiation="Unlike IT-only solutions, we integrate directly with SCADA, PLCs, and manufacturing systems",
            proof_point="95% faster time-to-value vs. traditional MES implementations",
        ),
        WinStatement(
            statement="Asset-heavy expertise—purpose-built for capital-intensive operations",
            differentiation="Designed for high-volume, continuous operations vs. generic analytics",
            proof_point="87% of manufacturing customers achieve ROI within 6 months",
        ),
        WinStatement(
            statement="Retrofit-ready—works with brownfield, legacy equipment, not just greenfield",
            differentiation="Deploys on existing infrastructure vs. requiring full modernization",
            proof_point="Works with 150+ industrial protocols including legacy Siemens, Rockwell, Schneider",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Industrial intelligence: equipment benchmarks, supply risk signals, commodity price tracking",
            data_format="OT data enrichment + external signals",
            specific_assets=["industrial_benchmarks_api", "supply_risk_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Manufacturing models: predictive maintenance, demand forecasting, quality prediction",
            data_format="Industrial ML models with edge deployment",
            specific_assets=["vibration_anomaly_detector", "demand_forecaster_v2"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Manufacturing driver trees: OEE → throughput → margin optimization",
            data_format="Industrial KPI relationships",
            specific_assets=["oee_driver_tree", "margin_optimization_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Industrial calculators: OEE, MTBF/MTTR, energy per unit, carbon per SKU",
            data_format="Manufacturing calculation engines",
            specific_assets=[
                "oee_calculator",
                "carbon_per_sku_calc",
                "downtime_cost_calc",
            ],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Operations leadership narratives with uptime, yield, and sustainability metrics",
            data_format="Industrial narratives + KPI visualizations",
            specific_assets=["coo_presentation_template", "board_ops_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="downtime_avoidance",
            template_name="Downtime Avoidance Model",
            formula_pattern="(Hours Avoided × Revenue/Hour) + Maintenance Savings",
            inputs_required=[
                "hours_avoided",
                "revenue_per_hour",
                "maintenance_savings",
            ],
            output_definition="Annual value from downtime prevention",
            applicable_industries=["manufacturing", "energy", "logistics"],
            example_calculation="(48 hrs × $250K/hr) + $500K = $12.5M value",
        ),
        ComposableModelTemplate(
            template_id="yield_improvement",
            template_name="Yield Improvement Model",
            formula_pattern="(Volume × Yield Gain × Margin) - Investment",
            inputs_required=["volume", "yield_gain_pct", "unit_margin", "investment"],
            output_definition="Annual margin from quality improvement",
            applicable_industries=["manufacturing"],
            example_calculation="(1M units × 3% × $45) - $200K = $1.15M margin",
        ),
        ComposableModelTemplate(
            template_id="energy_efficiency",
            template_name="Energy Efficiency Model",
            formula_pattern="(kWh × Cost/kWh × Savings %) + Carbon Credits",
            inputs_required=[
                "annual_kwh",
                "cost_per_kwh",
                "savings_pct",
                "carbon_value",
            ],
            output_definition="Annual energy and carbon savings",
            applicable_industries=["manufacturing", "energy", "logistics"],
            example_calculation="(50M kWh × $0.08 × 15%) + $100K = $700K savings",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="manufacturing",
            category="industry",
            related_tags=["industrial", "ot", "automation"],
        ),
        OntologyTag(
            tag="oee",
            category="value_driver",
            related_tags=["efficiency", "uptime", "performance"],
        ),
        OntologyTag(
            tag="predictive_maintenance",
            category="capability",
            related_tags=["ai", "iot", "condition_monitoring"],
        ),
        OntologyTag(
            tag="yield",
            category="value_driver",
            related_tags=["quality", "scrap", "rework"],
        ),
        OntologyTag(
            tag="downtime",
            category="value_driver",
            related_tags=["mtbf", "mttr", "availability"],
        ),
        OntologyTag(
            tag="inventory",
            category="value_driver",
            related_tags=["wip", "raw_materials", "holding_cost"],
        ),
        OntologyTag(
            tag="headcount_efficiency",
            category="value_driver",
            related_tags=["labor_productivity", "automation", "throughput"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="plant_output",
                node_type="driver",
                name="Plant Output",
                description="Total production volume",
                default_value="100K units/day",
            ),
            EconomicNode(
                node_id="oee_score",
                node_type="metric",
                name="OEE Score",
                description="Overall Equipment Effectiveness",
                default_value="65%",
            ),
            EconomicNode(
                node_id="downtime_hours",
                node_type="outcome",
                name="Downtime Hours",
                description="Unplanned stoppages",
                default_value="8 hrs/day",
            ),
            EconomicNode(
                node_id="yield_rate",
                node_type="metric",
                name="First Pass Yield",
                description="Quality rate without rework",
                default_value="92%",
            ),
            EconomicNode(
                node_id="energy_cost",
                node_type="driver",
                name="Energy Cost",
                description="Electricity and fuel costs",
                default_value="$2M/month",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Platform",
                description="Predictive analytics deployment",
                default_value="Deployed",
            ),
            EconomicNode(
                node_id="maintenance_cost",
                node_type="driver",
                name="Maintenance Cost",
                description="Planned and unplanned maintenance",
                default_value="$500K/month",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="oee_score",
                relationship_type="drives",
                weight=0.25,
                formula="+15%",
            ),
            EconomicRelationship(
                from_node_id="oee_score",
                to_node_id="plant_output",
                relationship_type="drives",
                weight=0.3,
                formula="× throughput",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="downtime_hours",
                relationship_type="enables",
                weight=-0.5,
                formula="-60%",
            ),
            EconomicRelationship(
                from_node_id="downtime_hours",
                to_node_id="plant_output",
                relationship_type="enables",
                weight=-0.1,
            ),
            EconomicRelationship(
                from_node_id="yield_rate",
                to_node_id="plant_output",
                relationship_type="drives",
                weight=0.15,
                formula="+ yield",
            ),
            EconomicRelationship(
                from_node_id="energy_cost",
                to_node_id="plant_output",
                relationship_type="enables",
                weight=-0.05,
            ),
        ],
        root_node_id="plant_output",
        graph_description="Manufacturing OEE and throughput optimization with downtime reduction",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=[
                    "Published industrial engineering studies",
                    "Third-party efficiency audits",
                ],
                acceptable_sources=[
                    "IEEE, SME journals",
                    "Industrial engineering firms",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=["Industry analyst validation", "Operational assessments"],
                acceptable_sources=[
                    "Gartner, IDC Manufacturing",
                    "Operational consulting",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Manufacturer internal tracking",
                    "OEE system validation",
                ],
                acceptable_sources=["MES systems", "Operational dashboards"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-plant aggregate data",
                    "Anonymized performance data",
                ],
                acceptable_sources=["Platform industrial network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["Industry benchmark databases", "Operational standards"],
                acceptable_sources=["MESA International", "NIST manufacturing data"],
            ),
        ],
        required_level=EvidenceLevel.CUSTOMER_MEASURED,
        validation_rules=[
            "OEE calculations must follow ISO standards",
            "Energy claims require metered data",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$300K-3M ACV",
        sales_cycle_length="4-12 months",
        switching_cost=SwitchingCost.HIGH,
        data_richness=DataRichness.MEDIUM,
        feedback_loop_speed=FeedbackLoopSpeed.MEDIUM,
    ),
)

FINANCIAL_SERVICES_VALUEPACK = ValuePackCreate(
    industry_id="financial_services",
    tier=ValuePackTier.IMMEDIATE_TRACTION,
    display_name="Financial Services (Banking, Insurance, Capital Markets)",
    description="Risk reduction, fraud prevention, compliance automation, customer LTV - highly regulated, data-rich environment",
    primary_value_drivers=[
        ValueDriver(
            id="fraud_prevention",
            name="Fraud Prevention",
            description="Reduce financial losses from fraudulent transactions",
            typical_impact="$1M-10M annual loss prevention",
            measurement_approach="Fraud detection rate, false positive reduction",
        ),
        ValueDriver(
            id="risk_reduction",
            name="Risk Capital Reduction",
            description="Lower regulatory capital requirements through better risk models",
            typical_impact="$10M-100M capital relief",
            measurement_approach="Risk-weighted asset reduction, VaR improvement",
        ),
        ValueDriver(
            id="compliance_efficiency",
            name="Compliance Efficiency",
            description="Automate regulatory reporting and compliance monitoring",
            typical_impact="$500K-5M annual cost reduction",
            measurement_approach="Regulatory filing time, audit findings reduction",
        ),
        ValueDriver(
            id="customer_ltv",
            name="Customer LTV Optimization",
            description="Increase customer lifetime value through personalization",
            typical_impact="15-30% LTV improvement",
            measurement_approach="Revenue per customer, retention rates, cross-sell ratios",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="aml_monitoring",
            name="AML Transaction Monitoring",
            description="AI-powered anti-money laundering detection and alerting",
            target_persona="Chief Risk Officer",
            business_problem="High false positive rates and regulatory fines",
        ),
        CoreUseCase(
            id="credit_risk",
            name="Real-Time Credit Risk",
            description="Instant credit decisioning and risk scoring",
            target_persona="Head of Credit",
            business_problem="Slow credit approvals and suboptimal risk pricing",
        ),
        CoreUseCase(
            id="regulatory_reporting",
            name="Automated Regulatory Reporting",
            description="Streamlined BCBS 239, CCAR, CECL compliance",
            target_persona="Chief Compliance Officer",
            business_problem="Manual regulatory processes and audit findings",
        ),
        CoreUseCase(
            id="wealth_personalization",
            name="Wealth Management Personalization",
            description="AI-driven portfolio recommendations and client insights",
            target_persona="Head of Wealth Management",
            business_problem="Generic advice failing to differentiate and retain clients",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="fraud_roi",
            name="Fraud Prevention ROI",
            formula_shape="(Losses Prevented × Detection Rate) - (False Positive Cost) - Platform Cost = Net Value",
            inputs=[
                "baseline_fraud_losses",
                "detection_improvement",
                "false_positive_reduction",
                "platform_cost",
            ],
            output_unit="Annual fraud value $",
            typical_range="$2M-20M",
        ),
        EconomicModelType(
            id="capital_relief",
            name="Regulatory Capital Relief",
            formula_shape="(RWA Reduction × Cost of Capital) - Implementation Cost = Annual Benefit",
            inputs=[
                "current_rwa",
                "risk_model_improvement",
                "cost_of_capital",
                "implementation_cost",
            ],
            output_unit="Annual capital benefit $",
            typical_range="$5M-50M",
        ),
        EconomicModelType(
            id="compliance_automation",
            name="Compliance Cost Reduction",
            formula_shape="(Manual Hours Saved × Cost Per Hour) + (Penalty Avoidance) = Savings",
            inputs=[
                "compliance_fte_hours",
                "hourly_cost",
                "historical_penalties",
                "audit_cost_reduction",
            ],
            output_unit="Annual savings $",
            typical_range="$500K-3M",
        ),
        EconomicModelType(
            id="ltv_uplift",
            name="Customer LTV Uplift",
            formula_shape="(Customer Count × LTV Improvement × Margin) - Platform Cost = Net Value",
            inputs=[
                "customer_base",
                "ltv_improvement_pct",
                "avg_revenue_per_customer",
                "margin_pct",
            ],
            output_unit="Annual value $",
            typical_range="$5M-30M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="regulatory_approval",
            requirement="Regulatory model approval",
            evidence_type="SR 11-7 compliance documentation",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="risk_model_validation",
            requirement="Risk model validation",
            evidence_type="Independent model validation (IMV)",
            minimum_level=EvidenceLevel.PEER_REVIEWED_AUDITED,
        ),
        ProofRequirement(
            id="audit_trail",
            requirement="Complete audit trail",
            evidence_type="Immutable decision logs for regulatory examination",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Regulatory model risk management—SR 11-7 compliant from day one",
            differentiation="Pre-built model governance vs. retrofitted compliance",
            proof_point="100% SR 11-7 compliance on all models vs. 60% industry average",
        ),
        WinStatement(
            statement="Explainable AI for financial services—regulatory-ready transparency",
            differentiation="White-box models vs. black-box ML that regulators reject",
            proof_point="Zero regulatory rejection of models vs. 30% industry rejection rate",
        ),
        WinStatement(
            statement="Unified risk and marketing data—break down risk/compliance silos",
            differentiation="Single platform for risk and growth vs. separate systems",
            proof_point="65% faster regulatory response time with unified data",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Financial intelligence: market signals, regulatory updates, fraud patterns",
            data_format="Financial data enrichment",
            specific_assets=["market_intelligence_api", "fraud_pattern_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Financial models: credit risk, fraud detection, churn prediction, LTV",
            data_format="Regulatory-compliant ML models",
            specific_assets=["credit_risk_model_v3", "fraud_detector_v4"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Financial driver trees: risk capital → regulatory requirements → profitability",
            data_format="Financial services KPI relationships",
            specific_assets=["risk_capital_tree", "compliance_driver_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Financial calculators: RWA, VaR, CECL, expected credit loss",
            data_format="Regulatory calculation engines",
            specific_assets=["rwa_calculator", "cecl_calculator", "var_calc"],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Board-ready financial narratives with risk and compliance alignment",
            data_format="Financial narratives + regulatory visualizations",
            specific_assets=["cro_presentation_template", "board_risk_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="fraud_roi",
            template_name="Fraud Prevention ROI",
            formula_pattern="(Losses Prevented × Detection Rate) - FP Costs - Investment",
            inputs_required=[
                "baseline_losses",
                "detection_rate",
                "false_positive_cost",
                "investment",
            ],
            output_definition="Annual fraud prevention value",
            applicable_industries=["financial_services", "retail"],
            example_calculation="($10M × 85%) - $500K - $1M = $7M net value",
        ),
        ComposableModelTemplate(
            template_id="capital_relief",
            template_name="Regulatory Capital Relief",
            formula_pattern="(RWA Reduction × Cost of Capital) - Investment",
            inputs_required=["rwa_reduction", "cost_of_capital", "investment"],
            output_definition="Annual capital benefit",
            applicable_industries=["financial_services"],
            example_calculation="($100M RWA reduction × 8%) - $2M = $6M benefit",
        ),
        ComposableModelTemplate(
            template_id="compliance_automation",
            template_name="Compliance Automation ROI",
            formula_pattern="(Hours × Cost × FTEs) + Penalties - Platform",
            inputs_required=["hours", "cost", "ftes", "penalties", "platform_cost"],
            output_definition="Annual compliance savings",
            applicable_industries=["financial_services", "healthcare", "public_sector"],
            example_calculation="(80 hrs/week × $120/hr × 5 FTEs) + $1M - $300K = $2.2M savings",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="financial_services",
            category="industry",
            related_tags=["banking", "insurance", "capital_markets"],
        ),
        OntologyTag(
            tag="risk_management",
            category="value_driver",
            related_tags=["credit", "market", "operational"],
        ),
        OntologyTag(
            tag="compliance",
            category="compliance",
            related_tags=["regulatory", "reporting", "governance"],
        ),
        OntologyTag(
            tag="fraud_prevention",
            category="value_driver",
            related_tags=["detection", "prevention", "monitoring"],
        ),
        OntologyTag(
            tag="customer_ltv",
            category="value_driver",
            related_tags=["retention", "cross_sell", "personalization"],
        ),
        OntologyTag(
            tag="headcount_efficiency",
            category="value_driver",
            related_tags=["backoffice_automation", "efficiency"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_revenue",
                node_type="driver",
                name="Total Revenue",
                description="Net interest + fee income",
                default_value="$500M",
            ),
            EconomicNode(
                node_id="risk_weighted_assets",
                node_type="driver",
                name="Risk-Weighted Assets",
                description="RWA for capital ratios",
                default_value="$2B",
            ),
            EconomicNode(
                node_id="fraud_losses",
                node_type="outcome",
                name="Fraud Losses",
                description="Annual fraud write-offs",
                default_value="$5M",
            ),
            EconomicNode(
                node_id="compliance_cost",
                node_type="driver",
                name="Compliance Cost",
                description="Regulatory and compliance spend",
                default_value="$20M",
            ),
            EconomicNode(
                node_id="customer_ltv",
                node_type="metric",
                name="Customer LTV",
                description="Lifetime value per customer",
                default_value="$25K",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Risk Platform",
                description="Risk and compliance AI deployment",
                default_value="Active",
            ),
            EconomicNode(
                node_id="capital_ratio",
                node_type="metric",
                name="Capital Ratio",
                description="CET1 capital ratio",
                default_value="12%",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="fraud_losses",
                relationship_type="enables",
                weight=-0.4,
                formula="-40%",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="risk_weighted_assets",
                relationship_type="enables",
                weight=-0.15,
                formula="-15% RWA",
            ),
            EconomicRelationship(
                from_node_id="risk_weighted_assets",
                to_node_id="capital_ratio",
                relationship_type="drives",
                weight=1.0,
            ),
            EconomicRelationship(
                from_node_id="capital_ratio",
                to_node_id="total_revenue",
                relationship_type="enables",
                weight=0.1,
            ),
            EconomicRelationship(
                from_node_id="fraud_losses",
                to_node_id="total_revenue",
                relationship_type="enables",
                weight=-0.01,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="compliance_cost",
                relationship_type="enables",
                weight=-0.3,
                formula="-30%",
            ),
            EconomicRelationship(
                from_node_id="compliance_cost",
                to_node_id="total_revenue",
                relationship_type="enables",
                weight=-0.04,
            ),
        ],
        root_node_id="total_revenue",
        graph_description="Financial services risk, compliance, and revenue optimization",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=["Published financial research", "Big 4 audit validation"],
                acceptable_sources=[
                    "Journal of Financial Economics",
                    "Big 4 audit firms",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=[
                    "Model validation by independent party",
                    "Regulatory examination success",
                ],
                acceptable_sources=[
                    "OCC, Fed, FDIC examination",
                    "Independent model validation",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Financial institution internal validation",
                    "Risk committee approval",
                ],
                acceptable_sources=[
                    "Internal risk dashboards",
                    "Finance committee reports",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-institution aggregate data",
                    "Anonymized performance metrics",
                ],
                acceptable_sources=["Platform financial network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["Industry benchmark data", "Peer analysis"],
                acceptable_sources=["BAI, ABA benchmarks", "Federal Reserve data"],
            ),
        ],
        required_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        validation_rules=[
            "All risk models require SR 11-7 documentation",
            "Fraud models require documented detection/FP rates",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$500K-5M ACV",
        sales_cycle_length="4-9 months",
        switching_cost=SwitchingCost.HIGH,
        data_richness=DataRichness.HIGH,
        feedback_loop_speed=FeedbackLoopSpeed.SLOW,
    ),
)

ENERGY_UTILITIES_VALUEPACK = ValuePackCreate(
    industry_id="energy_utilities",
    tier=ValuePackTier.HIGH_ROI_UNDERSERVED,
    display_name="Energy & Utilities (Oil, Gas, Renewables, Grid)",
    description="Asset reliability, grid optimization, regulatory compliance, carbon management - critical infrastructure with massive capital at risk",
    primary_value_drivers=[
        ValueDriver(
            id="asset_reliability",
            name="Asset Reliability",
            description="Prevent catastrophic failures in critical infrastructure",
            typical_impact="$5M-50M per major failure avoided",
            measurement_approach="Asset health scoring, failure mode predictions",
        ),
        ValueDriver(
            id="grid_optimization",
            name="Grid Optimization",
            description="Balance supply/demand and reduce transmission losses",
            typical_impact="$2M-20M annual efficiency gains",
            measurement_approach="Load forecasting accuracy, outage duration reduction",
        ),
        ValueDriver(
            id="regulatory_compliance",
            name="Regulatory Compliance",
            description="Meet FERC, NERC, EPA requirements without penalties",
            typical_impact="$1M-10M penalty avoidance",
            measurement_approach="Compliance score, violation tracking, audit results",
        ),
        ValueDriver(
            id="carbon_management",
            name="Carbon Management",
            description="Track, report, and reduce carbon emissions",
            typical_impact="$500K-5M carbon credit value + avoidance",
            measurement_approach="Emissions monitoring, carbon intensity tracking",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="predictive_grid",
            name="Predictive Grid Maintenance",
            description="AI-powered transformer and line failure prediction",
            target_persona="VP Transmission",
            business_problem="Aging infrastructure causing unplanned outages",
        ),
        CoreUseCase(
            id="load_forecasting",
            name="AI Load Forecasting",
            description="Accurate demand prediction for generation planning",
            target_persona="Chief Operating Officer",
            business_problem="Over-generation waste and under-generation shortfalls",
        ),
        CoreUseCase(
            id="nerc_compliance",
            name="NERC CIP Compliance",
            description="Automated critical infrastructure protection compliance",
            target_persona="Chief Compliance Officer",
            business_problem="NERC violations costing millions in penalties",
        ),
        CoreUseCase(
            id="emissions_tracking",
            name="Emissions Tracking & Reporting",
            description="Automated GHG monitoring and ESG reporting",
            target_persona="Chief Sustainability Officer",
            business_problem="Manual carbon accounting and regulatory reporting burden",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="failure_prevention",
            name="Critical Asset Failure Prevention",
            formula_shape="(Major Failures Avoided × Cost Per Failure) - Platform Cost = Value",
            inputs=[
                "baseline_failure_rate",
                "prevention_rate",
                "cost_per_failure",
                "platform_cost",
            ],
            output_unit="Annual value $",
            typical_range="$10M-100M",
        ),
        EconomicModelType(
            id="grid_efficiency",
            name="Grid Efficiency Model",
            formula_shape="(Transmission Loss Reduction × Energy Value) + (Outage Cost Avoidance) = Savings",
            inputs=[
                "current_losses_pct",
                "improvement_pct",
                "energy_volume",
                "outage_cost_per_hour",
            ],
            output_unit="Annual savings $",
            typical_range="$2M-15M",
        ),
        EconomicModelType(
            id="compliance_value",
            name="Regulatory Compliance Value",
            formula_shape="(Penalty Avoidance) + (Fine Reduction) + (Audit Cost Savings) = Total Value",
            inputs=[
                "historical_penalties",
                "compliance_improvement",
                "audit_cost_reduction",
            ],
            output_unit="Annual value $",
            typical_range="$1M-8M",
        ),
        EconomicModelType(
            id="carbon_value",
            name="Carbon Value Creation",
            formula_shape="(Carbon Reduction × Carbon Price) + (Credit Generation × Credit Value) = Total Value",
            inputs=[
                "emissions_reduction_tons",
                "carbon_price_per_ton",
                "credits_generated",
                "credit_value",
            ],
            output_unit="Annual carbon value $",
            typical_range="$500K-5M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="reliability_standards",
            requirement="Reliability standards compliance",
            evidence_type="NERC GADS, IEEE 493 documentation",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="environmental_validation",
            requirement="Environmental impact validation",
            evidence_type="EPA-compliant emissions tracking",
            minimum_level=EvidenceLevel.PEER_REVIEWED_AUDITED,
        ),
        ProofRequirement(
            id="operational_evidence",
            requirement="Operational performance evidence",
            evidence_type="Control center integration results",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Critical infrastructure hardened—built for NERC CIP, FERC, and operational technology requirements",
            differentiation="Unlike IT-centric solutions, we meet utility operational and security standards",
            proof_point="100% NERC CIP compliance certification vs. 60% industry rate",
        ),
        WinStatement(
            statement="Unified OT/IT—bridges control room to board room without security gaps",
            differentiation="Secure by design for critical infrastructure vs. retrofitted security",
            proof_point="Zero security incidents in 5 years of utility deployments",
        ),
        WinStatement(
            statement="Grid-native AI—trained on actual grid data, not generic patterns",
            differentiation="Purpose-built for power systems vs. generic time series models",
            proof_point="40% more accurate load forecasting than generic ML approaches",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Energy intelligence: weather, commodity prices, grid conditions, regulatory updates",
            data_format="Energy-specific data feeds",
            specific_assets=["grid_conditions_api", "commodity_price_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Energy models: load forecasting, asset degradation, outage prediction",
            data_format="Energy grid ML models",
            specific_assets=["load_forecaster_grid", "transformer_degradation_model"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Energy driver trees: reliability → customer satisfaction → regulatory standing",
            data_format="Utility KPI relationships",
            specific_assets=["reliability_driver_tree", "regulatory_compliance_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Energy calculators: SAIDI/SAIFI, carbon intensity, fuel optimization",
            data_format="Utility calculation engines",
            specific_assets=[
                "reliability_calculator",
                "carbon_intensity_calc",
                "fuel_optimizer",
            ],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Regulatory commission and board narratives with reliability and sustainability metrics",
            data_format="Utility narratives + grid visualizations",
            specific_assets=["regulatory_filing_template", "board_utility_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="asset_reliability",
            template_name="Asset Reliability Model",
            formula_pattern="(Failures Avoided × Cost/Failure) - Investment",
            inputs_required=["failures_avoided", "cost_per_failure", "investment"],
            output_definition="Annual reliability value",
            applicable_industries=["energy_utilities", "manufacturing"],
            example_calculation="(3 major failures × $15M) - $5M = $40M value",
        ),
        ComposableModelTemplate(
            template_id="carbon_reduction",
            template_name="Carbon Reduction Value",
            formula_pattern="(Tons Reduced × Carbon Price) + Credits",
            inputs_required=["tons_reduced", "carbon_price", "credits"],
            output_definition="Annual carbon value",
            applicable_industries=["energy_utilities", "manufacturing"],
            example_calculation="(100K tons × $50) + $200K = $5.2M value",
        ),
        ComposableModelTemplate(
            template_id="downtime_avoidance",
            template_name="Downtime Avoidance Model",
            formula_pattern="(Hours Avoided × Revenue/Hour) + Penalty Avoidance",
            inputs_required=["hours_avoided", "revenue_per_hour", "penalties"],
            output_definition="Annual outage value",
            applicable_industries=["energy_utilities", "manufacturing", "logistics"],
            example_calculation="(24 hrs × $500K/hr) + $2M = $14M value",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="energy",
            category="industry",
            related_tags=["utilities", "oil_gas", "renewables"],
        ),
        OntologyTag(
            tag="grid_reliability",
            category="value_driver",
            related_tags=["saidi", "saifi", "outages"],
        ),
        OntologyTag(
            tag="asset_management",
            category="value_driver",
            related_tags=["predictive_maintenance", "degradation", "replacement"],
        ),
        OntologyTag(
            tag="predictive_maintenance",
            category="capability",
            related_tags=["predictive_maintenance", "degradation", "replacement"],
        ),
        OntologyTag(
            tag="downtime",
            category="value_driver",
            related_tags=["outages", "trips", "unplanned_maintenance"],
        ),
        OntologyTag(
            tag="carbon",
            category="value_driver",
            related_tags=["emissions", "esg", "sustainability"],
        ),
        OntologyTag(
            tag="compliance",
            category="compliance",
            related_tags=["ferc", "nerc", "regulatory"],
        ),
        OntologyTag(
            tag="nerc",
            category="compliance",
            related_tags=["cip", "reliability", "standards"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_revenue",
                node_type="driver",
                name="Total Revenue",
                description="Electricity sales and capacity payments",
                default_value="$1B",
            ),
            EconomicNode(
                node_id="system_reliability",
                node_type="metric",
                name="System Reliability",
                description="SAIDI/SAIFI composite score",
                default_value="120 min/year",
            ),
            EconomicNode(
                node_id="outage_cost",
                node_type="outcome",
                name="Outage Cost",
                description="Cost of customer outages",
                default_value="$50M",
            ),
            EconomicNode(
                node_id="carbon_emissions",
                node_type="driver",
                name="Carbon Emissions",
                description="CO2 equivalent emissions",
                default_value="5M tons",
            ),
            EconomicNode(
                node_id="asset_health",
                node_type="metric",
                name="Asset Health Score",
                description="Critical asset condition index",
                default_value="78%",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="Grid AI Platform",
                description="Predictive analytics for grid operations",
                default_value="Deployed",
            ),
            EconomicNode(
                node_id="compliance_score",
                node_type="metric",
                name="Compliance Score",
                description="NERC/FERC compliance rating",
                default_value="94%",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="system_reliability",
                relationship_type="drives",
                weight=0.35,
                formula="-30% SAIDI",
            ),
            EconomicRelationship(
                from_node_id="system_reliability",
                to_node_id="outage_cost",
                relationship_type="drives",
                weight=1.0,
            ),
            EconomicRelationship(
                from_node_id="outage_cost",
                to_node_id="total_revenue",
                relationship_type="enables",
                weight=-0.05,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="asset_health",
                relationship_type="drives",
                weight=0.25,
                formula="+12% health",
            ),
            EconomicRelationship(
                from_node_id="asset_health",
                to_node_id="outage_cost",
                relationship_type="enables",
                weight=-0.3,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="carbon_emissions",
                relationship_type="enables",
                weight=-0.15,
                formula="-15%",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="compliance_score",
                relationship_type="drives",
                weight=0.2,
                formula="+6%",
            ),
        ],
        root_node_id="total_revenue",
        graph_description="Energy utility reliability, asset health, and emissions optimization",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=[
                    "Published energy research",
                    "IEEE Power Engineering validation",
                ],
                acceptable_sources=["IEEE Transactions", "Energy Policy journal"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=["NERC compliance validation", "Grid operator assessment"],
                acceptable_sources=["NERC compliance audits", "ISO/RTO assessments"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Utility internal measurement",
                    "Control center integration validation",
                ],
                acceptable_sources=[
                    "Utility operational data",
                    "SCADA integration results",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-utility aggregate data",
                    "Anonymized reliability metrics",
                ],
                acceptable_sources=["Platform utility network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["Industry standard benchmarks", "DOE/EIA data"],
                acceptable_sources=["EIA databases", "DOE efficiency data"],
            ),
        ],
        required_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        validation_rules=[
            "Reliability claims must reference IEEE 1366 standards",
            "Carbon claims require EPA-compliant measurement",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$400K-4M ACV",
        sales_cycle_length="6-18 months",
        switching_cost=SwitchingCost.HIGH,
        data_richness=DataRichness.HIGH,
        feedback_loop_speed=FeedbackLoopSpeed.SLOW,
    ),
)

RETAIL_ECOMMERCE_VALUEPACK = ValuePackCreate(
    industry_id="retail_ecommerce",
    tier=ValuePackTier.IMMEDIATE_TRACTION,
    display_name="Retail & E-commerce",
    description="Personalization, inventory optimization, demand forecasting, customer acquisition - high-velocity, data-rich environment",
    primary_value_drivers=[
        ValueDriver(
            id="conversion_uplift",
            name="Conversion Rate Uplift",
            description="Increase purchase conversion through personalization",
            typical_impact="10-30% conversion improvement",
            measurement_approach="A/B testing, funnel analytics",
        ),
        ValueDriver(
            id="inventory_optimization",
            name="Inventory Optimization",
            description="Reduce stockouts and overstock through demand forecasting",
            typical_impact="$1M-10M working capital + margin improvement",
            measurement_approach="Inventory turns, stockout rate, carrying cost",
        ),
        ValueDriver(
            id="customer_acquisition",
            name="Customer Acquisition Efficiency",
            description="Reduce CAC through targeted marketing",
            typical_impact="20-40% CAC reduction",
            measurement_approach="Cost per acquisition, LTV/CAC ratio",
        ),
        ValueDriver(
            id="churn_reduction",
            name="Churn Reduction",
            description="Improve retention through personalized engagement",
            typical_impact="5-15% churn reduction",
            measurement_approach="Retention rate, cohort analysis, repeat purchase rate",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="product_recommendations",
            name="AI Product Recommendations",
            description="Personalized product suggestions across channels",
            target_persona="Chief Digital Officer",
            business_problem="Generic recommendations failing to drive conversion",
        ),
        CoreUseCase(
            id="demand_forecasting",
            name="Demand Forecasting",
            description="AI-powered inventory and demand planning",
            target_persona="VP Supply Chain",
            business_problem="Stockouts during peak demand and excess inventory markdowns",
        ),
        CoreUseCase(
            id="dynamic_pricing",
            name="Dynamic Pricing Optimization",
            description="Real-time price optimization for margin and velocity",
            target_persona="Chief Merchant",
            business_problem="Static pricing missing revenue and inventory optimization opportunities",
        ),
        CoreUseCase(
            id="customer_insights",
            name="Customer 360 Insights",
            description="Unified customer view for personalized marketing",
            target_persona="VP Marketing",
            business_problem="Siloed customer data preventing personalization",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="conversion_roi",
            name="Conversion Uplift ROI",
            formula_shape="(Traffic × Conversion Improvement × AOV × Margin) - Platform Cost = Value",
            inputs=[
                "monthly_traffic",
                "conversion_lift_pct",
                "aov",
                "margin_pct",
                "platform_cost",
            ],
            output_unit="Annual value $",
            typical_range="$2M-20M",
        ),
        EconomicModelType(
            id="inventory_value",
            name="Inventory Optimization Value",
            formula_shape="(Stockout Reduction × Lost Margin) + (Overstock Reduction × Carrying Cost) = Savings",
            inputs=[
                "stockout_rate_baseline",
                "improvement_pct",
                "avg_margin",
                "overstock_reduction",
                "carrying_cost_pct",
            ],
            output_unit="Annual value $",
            typical_range="$1M-8M",
        ),
        EconomicModelType(
            id="cac_efficiency",
            name="CAC Efficiency Model",
            formula_shape="(Customers Acquired × CAC Reduction × LTV) - Platform Cost = Value",
            inputs=[
                "annual_customers",
                "cac_reduction_pct",
                "customer_ltv",
                "platform_cost",
            ],
            output_unit="Annual value $",
            typical_range="$500K-5M",
        ),
        EconomicModelType(
            id="retention_value",
            name="Customer Retention Value",
            formula_shape="(Customer Base × Retention Improvement × Annual Value) - Platform Cost = Value",
            inputs=[
                "customer_base",
                "retention_lift_pct",
                "annual_value_per_customer",
                "platform_cost",
            ],
            output_unit="Annual value $",
            typical_range="$1M-10M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="conversion_evidence",
            requirement="Conversion lift evidence",
            evidence_type="A/B test results with statistical significance",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
        ProofRequirement(
            id="inventory_validation",
            requirement="Inventory accuracy validation",
            evidence_type="Forecast accuracy vs. actual sales",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
        ProofRequirement(
            id="customer_data",
            requirement="Customer data privacy",
            evidence_type="GDPR/CCPA compliance documentation",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Real-time personalization—sub-100ms recommendation latency at scale",
            differentiation="Unlike batch processing, we deliver real-time personalization",
            proof_point="95th percentile latency under 50ms at 100K requests/second",
        ),
        WinStatement(
            statement="Unified commerce—connects online, in-store, mobile in single view",
            differentiation="Single customer view across all channels vs. channel silos",
            proof_point="360-degree customer view increases LTV by 35% vs. channel-specific approaches",
        ),
        WinStatement(
            statement="Inventory intelligence—demand sensing, not just demand forecasting",
            differentiation="Real-time demand signals vs. historical-only forecasting",
            proof_point="25% improvement in forecast accuracy vs. traditional time series models",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Retail intelligence: trends, competitive pricing, customer signals",
            data_format="Retail data enrichment",
            specific_assets=["trend_api", "pricing_intelligence_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Retail models: recommendation engines, demand forecasting, price elasticity",
            data_format="Real-time retail ML",
            specific_assets=["recommendation_engine_v3", "demand_forecaster_retail"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Retail driver trees: traffic → conversion → AOV → revenue",
            data_format="E-commerce KPI relationships",
            specific_assets=["conversion_driver_tree", "inventory_optimization_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Retail calculators: conversion, inventory turns, CAC, LTV, gross margin",
            data_format="Retail calculation engines",
            specific_assets=["conversion_calc", "inventory_turn_calc", "ltv_cac_calc"],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Board-ready retail narratives with growth and efficiency metrics",
            data_format="Retail narratives + performance visualizations",
            specific_assets=["cmo_presentation_template", "board_retail_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="conversion_uplift",
            template_name="Conversion Uplift Model",
            formula_pattern="(Traffic × Conv Lift × AOV × Margin) - Investment",
            inputs_required=[
                "traffic",
                "conversion_lift",
                "aov",
                "margin",
                "investment",
            ],
            output_definition="Annual conversion value",
            applicable_industries=["retail_ecommerce", "enterprise_saas"],
            example_calculation="(10M visits × 15% × $85 × 35%) - $500K = $44M value",
        ),
        ComposableModelTemplate(
            template_id="ltv_cac",
            template_name="LTV/CAC Optimization",
            formula_pattern="(New Customers × LTV Gain) - (Reduction in CAC Spend)",
            inputs_required=["new_customers", "ltv_gain", "cac_savings"],
            output_definition="Annual customer economics value",
            applicable_industries=[
                "retail_ecommerce",
                "enterprise_saas",
                "financial_services",
            ],
            example_calculation="(100K customers × $50 LTV gain) - $1M = $4M value",
        ),
        ComposableModelTemplate(
            template_id="inventory_optimization",
            template_name="Inventory Optimization",
            formula_pattern="(Stockout Value + Overstock Savings) - Investment",
            inputs_required=["stockout_value", "overstock_savings", "investment"],
            output_definition="Annual inventory value",
            applicable_industries=["retail_ecommerce", "manufacturing", "logistics"],
            example_calculation="($3M stockout + $2M overstock) - $500K = $4.5M value",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="retail",
            category="industry",
            related_tags=["ecommerce", "omnichannel", "d2c"],
        ),
        OntologyTag(
            tag="conversion",
            category="value_driver",
            related_tags=["funnel", "personalization", "optimization"],
        ),
        OntologyTag(
            tag="inventory",
            category="value_driver",
            related_tags=["stockout", "overstock", "turns"],
        ),
        OntologyTag(
            tag="customer_ltv",
            category="value_driver",
            related_tags=["retention", "repeat", "loyalty"],
        ),
        OntologyTag(
            tag="revenue_uplift",
            category="value_driver",
            related_tags=["growth", "aov", "conversion"],
        ),
        OntologyTag(
            tag="fraud_prevention",
            category="value_driver",
            related_tags=["chargebacks", "payment_fraud", "account_takeover"],
        ),
        OntologyTag(
            tag="personalization",
            category="capability",
            related_tags=["recommendations", "targeting", "ai"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_revenue",
                node_type="driver",
                name="Total Revenue",
                description="Gross merchandise value",
                default_value="$500M",
            ),
            EconomicNode(
                node_id="conversion_rate",
                node_type="metric",
                name="Conversion Rate",
                description="Purchase conversion percentage",
                default_value="2.8%",
            ),
            EconomicNode(
                node_id="aov",
                node_type="metric",
                name="Average Order Value",
                description="Revenue per transaction",
                default_value="$75",
            ),
            EconomicNode(
                node_id="inventory_turns",
                node_type="metric",
                name="Inventory Turns",
                description="Annual inventory turnover",
                default_value="4x",
            ),
            EconomicNode(
                node_id="customer_ltv",
                node_type="metric",
                name="Customer LTV",
                description="Lifetime value per customer",
                default_value="$180",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Commerce Platform",
                description="Personalization and forecasting",
                default_value="Active",
            ),
            EconomicNode(
                node_id="cac",
                node_type="driver",
                name="Customer Acquisition Cost",
                description="Marketing cost per new customer",
                default_value="$45",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="conversion_rate",
                relationship_type="drives",
                weight=0.25,
                formula="+20%",
            ),
            EconomicRelationship(
                from_node_id="conversion_rate",
                to_node_id="total_revenue",
                relationship_type="drives",
                weight=0.5,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="aov",
                relationship_type="drives",
                weight=0.15,
                formula="+8%",
            ),
            EconomicRelationship(
                from_node_id="aov",
                to_node_id="total_revenue",
                relationship_type="drives",
                weight=0.3,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="inventory_turns",
                relationship_type="drives",
                weight=0.3,
                formula="+30%",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="cac",
                relationship_type="enables",
                weight=-0.2,
                formula="-25%",
            ),
            EconomicRelationship(
                from_node_id="cac",
                to_node_id="customer_ltv",
                relationship_type="enables",
                weight=-0.3,
            ),
            EconomicRelationship(
                from_node_id="customer_ltv",
                to_node_id="total_revenue",
                relationship_type="drives",
                weight=0.4,
            ),
        ],
        root_node_id="total_revenue",
        graph_description="Retail revenue optimization through conversion, AOV, and inventory efficiency",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=["Published retail research", "Academic validation"],
                acceptable_sources=["Journal of Retailing", "Marketing Science"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=[
                    "Industry analyst validation",
                    "A/B testing certification",
                ],
                acceptable_sources=[
                    "Gartner, Forrester",
                    "Testing platform validation",
                ],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Retailer internal measurement",
                    "Analytics platform validation",
                ],
                acceptable_sources=["Google Analytics", "Internal BI platforms"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-retailer aggregate data",
                    "Anonymized performance metrics",
                ],
                acceptable_sources=["Platform retail network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["Industry benchmark data", "E-commerce standards"],
                acceptable_sources=["NRF data", "Digital Commerce 360"],
            ),
        ],
        required_level=EvidenceLevel.CUSTOMER_MEASURED,
        validation_rules=[
            "Conversion claims require A/B test significance p<0.05",
            "Inventory claims require seasonal validation",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$100K-1M ACV",
        sales_cycle_length="1-4 months",
        switching_cost=SwitchingCost.LOW,
        data_richness=DataRichness.HIGH,
        feedback_loop_speed=FeedbackLoopSpeed.FAST,
    ),
)

LOGISTICS_SUPPLY_CHAIN_VALUEPACK = ValuePackCreate(
    industry_id="logistics_supply_chain",
    tier=ValuePackTier.HIGH_ROI_UNDERSERVED,
    display_name="Logistics & Supply Chain",
    description="Route optimization, warehouse efficiency, visibility, carrier management - operational excellence at massive scale",
    primary_value_drivers=[
        ValueDriver(
            id="transportation_savings",
            name="Transportation Cost Savings",
            description="Reduce freight spend through optimization",
            typical_impact="5-15% transportation cost reduction",
            measurement_approach="Cost per mile, cost per pound, mode optimization",
        ),
        ValueDriver(
            id="warehouse_efficiency",
            name="Warehouse Efficiency",
            description="Improve fulfillment speed and accuracy",
            typical_impact="20-40% productivity improvement",
            measurement_approach="Units per hour, pick accuracy, dock-to-stock time",
        ),
        ValueDriver(
            id="visibility_value",
            name="Supply Chain Visibility",
            description="End-to-end shipment tracking and ETAs",
            typical_impact="$500K-5M exception management value",
            measurement_approach="On-time delivery, proactive alerts, exception reduction",
        ),
        ValueDriver(
            id="inventory_positioning",
            name="Inventory Positioning",
            description="Optimize stock location across network",
            typical_impact="$2M-15M working capital optimization",
            measurement_approach="Network inventory turns, stock transfer reduction",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="route_optimization",
            name="Route Optimization",
            description="AI-powered dynamic routing for fleets",
            target_persona="VP Transportation",
            business_problem="Static routes missing efficiency opportunities and real-time conditions",
        ),
        CoreUseCase(
            id="warehouse_automation",
            name="Warehouse Optimization",
            description="Labor and process optimization for fulfillment",
            target_persona="VP Warehousing",
            business_problem="Rising labor costs and throughput constraints",
        ),
        CoreUseCase(
            id="predictive_visibility",
            name="Predictive ETAs",
            description="ML-powered arrival time predictions",
            target_persona="Customer Service Director",
            business_problem="Poor visibility causing customer service issues",
        ),
        CoreUseCase(
            id="carrier_selection",
            name="AI Carrier Selection",
            description="Optimal carrier selection by lane and cost",
            target_persona="Director of Procurement",
            business_problem="Suboptimal carrier choices costing money and service",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="transportation_roi",
            name="Transportation ROI",
            formula_shape="(Miles Saved × Cost Per Mile) + (Mode Optimization Savings) - Platform Cost = Value",
            inputs=[
                "fleet_miles_annual",
                "optimization_pct",
                "cost_per_mile",
                "mode_savings",
            ],
            output_unit="Annual savings $",
            typical_range="$2M-15M",
        ),
        EconomicModelType(
            id="warehouse_productivity",
            name="Warehouse Productivity",
            formula_shape="(Labor Hours Saved × Labor Cost) + (Accuracy Improvement Value) = Savings",
            inputs=[
                "annual_labor_hours",
                "productivity_gain_pct",
                "hourly_labor_cost",
                "error_reduction_value",
            ],
            output_unit="Annual savings $",
            typical_range="$1M-8M",
        ),
        EconomicModelType(
            id="visibility_value",
            name="Visibility Value",
            formula_shape="(Exceptions Prevented × Cost Per Exception) + (Customer Retention Value) = Total Value",
            inputs=[
                "annual_exceptions",
                "prevention_rate",
                "cost_per_exception",
                "retention_value",
            ],
            output_unit="Annual value $",
            typical_range="$500K-3M",
        ),
        EconomicModelType(
            id="network_optimization",
            name="Network Optimization",
            formula_shape="(Inventory Reduction × Carrying Cost) + (Transportation Savings) = Value",
            inputs=[
                "inventory_reduction_value",
                "carrying_cost_pct",
                "network_transport_savings",
            ],
            output_unit="Annual value $",
            typical_range="$2M-12M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="operational_metrics",
            requirement="Operational metrics validation",
            evidence_type="WMS/TMS data integration proof",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
        ProofRequirement(
            id="cost_verification",
            requirement="Cost verification",
            evidence_type="Invoice and GL reconciliation",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="service_validation",
            requirement="Service level validation",
            evidence_type="On-time delivery measurement",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="Real-time optimization—dynamic routing vs. static batch optimization",
            differentiation="Continuous optimization vs. daily/weekly batch runs",
            proof_point="8% additional cost savings vs. batch optimization approaches",
        ),
        WinStatement(
            statement="Unified supply chain—connects planning, execution, and visibility",
            differentiation="Single platform vs. siloed TMS, WMS, and visibility tools",
            proof_point="45% faster issue resolution with unified platform vs. point solutions",
        ),
        WinStatement(
            statement="Carrier ecosystem—direct carrier integrations, not just rate shopping",
            differentiation="Deep carrier integrations vs. surface-level API connections",
            proof_point="2x more carrier data depth than leading TMS platforms",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Logistics intelligence: carrier performance, port conditions, weather, traffic",
            data_format="Supply chain data enrichment",
            specific_assets=["carrier_scorecard_api", "port_conditions_feed"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Logistics models: ETA prediction, demand forecasting, route optimization",
            data_format="Supply chain ML models",
            specific_assets=["eta_predictor", "route_optimizer_ml"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Logistics driver trees: on-time → cost → customer satisfaction",
            data_format="Logistics KPI relationships",
            specific_assets=["service_driver_tree", "cost_optimization_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Logistics calculators: cost per mile, warehouse productivity, fill rates",
            data_format="Logistics calculation engines",
            specific_assets=["transportation_cost_calc", "warehouse_productivity_calc"],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="COO-ready logistics narratives with cost and service metrics",
            data_format="Logistics narratives + operational visualizations",
            specific_assets=["coo_presentation_template", "board_logistics_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="transportation_savings",
            template_name="Transportation Savings",
            formula_pattern="(Miles Saved × $/Mile) + Mode Optimization",
            inputs_required=["miles_saved", "cost_per_mile", "mode_savings"],
            output_definition="Annual transportation savings",
            applicable_industries=["logistics_supply_chain", "retail", "manufacturing"],
            example_calculation="(1M miles × $2.50) + $500K = $3M savings",
        ),
        ComposableModelTemplate(
            template_id="efficiency_uplift",
            template_name="Efficiency Uplift",
            formula_pattern="(Output × Improvement % × Value) - Investment",
            inputs_required=[
                "output",
                "improvement_pct",
                "value_per_unit",
                "investment",
            ],
            output_definition="Annual efficiency value",
            applicable_industries=[
                "logistics_supply_chain",
                "manufacturing",
                "enterprise_saas",
            ],
            example_calculation="(1M units × 25% × $5) - $200K = $1.05M value",
        ),
        ComposableModelTemplate(
            template_id="downtime_avoidance",
            template_name="Downtime Avoidance",
            formula_pattern="(Hours Avoided × Cost/Hour) + Penalty Avoidance",
            inputs_required=["hours_avoided", "cost_per_hour", "penalties"],
            output_definition="Annual downtime value",
            applicable_industries=["logistics_supply_chain", "manufacturing", "energy"],
            example_calculation="(48 hrs × $100K/hr) + $500K = $5.3M value",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="logistics",
            category="industry",
            related_tags=["supply_chain", "transportation", "warehousing"],
        ),
        OntologyTag(
            tag="transportation",
            category="value_driver",
            related_tags=["freight", "routing", "optimization"],
        ),
        OntologyTag(
            tag="warehouse",
            category="value_driver",
            related_tags=["fulfillment", "picking", "automation"],
        ),
        OntologyTag(
            tag="visibility",
            category="value_driver",
            related_tags=["tracking", "eta", "exceptions"],
        ),
        OntologyTag(
            tag="predictive_maintenance",
            category="capability",
            related_tags=["fleet_maintenance", "telematics", "condition_monitoring"],
        ),
        OntologyTag(
            tag="downtime",
            category="value_driver",
            related_tags=["vehicle_downtime", "warehouse_downtime"],
        ),
        OntologyTag(
            tag="inventory",
            category="value_driver",
            related_tags=["positioning", "turns", "safety_stock"],
        ),
        OntologyTag(
            tag="headcount_efficiency",
            category="value_driver",
            related_tags=["warehouse_labor", "productivity", "automation"],
        ),
        OntologyTag(
            tag="carrier",
            category="capability",
            related_tags=["freight", "procurement", "management"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="total_cost",
                node_type="driver",
                name="Total Logistics Cost",
                description="Transportation + warehousing + inventory",
                default_value="$100M",
            ),
            EconomicNode(
                node_id="transportation_cost",
                node_type="driver",
                name="Transportation Cost",
                description="Freight and fuel spend",
                default_value="$60M",
            ),
            EconomicNode(
                node_id="warehouse_cost",
                node_type="driver",
                name="Warehouse Cost",
                description="Labor and facility costs",
                default_value="$30M",
            ),
            EconomicNode(
                node_id="on_time_rate",
                node_type="metric",
                name="On-Time Rate",
                description="OTD percentage",
                default_value="92%",
            ),
            EconomicNode(
                node_id="cost_per_shipment",
                node_type="metric",
                name="Cost Per Shipment",
                description="All-in cost per delivery",
                default_value="$12.50",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Logistics Platform",
                description="Optimization and visibility",
                default_value="Active",
            ),
            EconomicNode(
                node_id="customer_satisfaction",
                node_type="outcome",
                name="Customer Satisfaction",
                description="Delivery satisfaction score",
                default_value="4.1/5",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="transportation_cost",
                relationship_type="enables",
                weight=-0.12,
                formula="-12%",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="warehouse_cost",
                relationship_type="enables",
                weight=-0.15,
                formula="-15%",
            ),
            EconomicRelationship(
                from_node_id="transportation_cost",
                to_node_id="total_cost",
                relationship_type="drives",
                weight=0.6,
            ),
            EconomicRelationship(
                from_node_id="warehouse_cost",
                to_node_id="total_cost",
                relationship_type="drives",
                weight=0.3,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="on_time_rate",
                relationship_type="drives",
                weight=0.08,
                formula="+8%",
            ),
            EconomicRelationship(
                from_node_id="on_time_rate",
                to_node_id="customer_satisfaction",
                relationship_type="drives",
                weight=0.5,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="cost_per_shipment",
                relationship_type="enables",
                weight=-0.1,
                formula="-10%",
            ),
        ],
        root_node_id="total_cost",
        graph_description="Logistics cost and service optimization through transportation and warehouse efficiency",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=[
                    "Published logistics research",
                    "Operations research validation",
                ],
                acceptable_sources=["Transportation Science", "Operations Research"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=[
                    "Industry analyst validation",
                    "TMS/WMS integration proof",
                ],
                acceptable_sources=["Gartner Supply Chain", "Blue Yonder validation"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Shipper internal measurement",
                    "WMS/TMS data validation",
                ],
                acceptable_sources=["TMS reporting", "WMS analytics"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-shipper aggregate data",
                    "Anonymized performance metrics",
                ],
                acceptable_sources=["Platform logistics network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["Industry benchmark data", "CSCMP standards"],
                acceptable_sources=["CSCMP State of Logistics", "Industry benchmarks"],
            ),
        ],
        required_level=EvidenceLevel.CUSTOMER_MEASURED,
        validation_rules=[
            "Transportation claims require freight invoice validation",
            "Warehouse claims require WMS productivity data",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$300K-3M ACV",
        sales_cycle_length="4-12 months",
        switching_cost=SwitchingCost.MEDIUM,
        data_richness=DataRichness.MEDIUM,
        feedback_loop_speed=FeedbackLoopSpeed.MEDIUM,
    ),
)

PUBLIC_SECTOR_VALUEPACK = ValuePackCreate(
    industry_id="public_sector",
    tier=ValuePackTier.COMPLEX_BUT_POWERFUL,
    display_name="Public Sector (Federal, State, Local, Education)",
    description="Citizen service, fraud prevention, compliance, operational efficiency - high stakes public impact with procurement complexity",
    primary_value_drivers=[
        ValueDriver(
            id="service_efficiency",
            name="Citizen Service Efficiency",
            description="Reduce time and cost to deliver government services",
            typical_impact="$500K-5M annual cost reduction",
            measurement_approach="Service delivery time, cost per transaction, wait time reduction",
        ),
        ValueDriver(
            id="fraud_waste",
            name="Fraud & Waste Prevention",
            description="Prevent improper payments and fraud",
            typical_impact="$2M-20M loss prevention",
            measurement_approach="Improper payment rate, fraud detection rate, recovery amounts",
        ),
        ValueDriver(
            id="compliance_assurance",
            name="Compliance Assurance",
            description="Meet regulatory and audit requirements",
            typical_impact="$1M-10M penalty avoidance",
            measurement_approach="Audit findings, compliance score, corrective actions",
        ),
        ValueDriver(
            id="operational_efficiency",
            name="Operational Efficiency",
            description="Improve internal government operations",
            typical_impact="20-40% process time reduction",
            measurement_approach="Process cycle time, FTE requirements, backoffice costs",
        ),
    ],
    core_use_cases=[
        CoreUseCase(
            id="benefits_optimization",
            name="Benefits Optimization",
            description="AI-powered eligibility and fraud detection",
            target_persona="Agency Director",
            business_problem="Improper payments and fraud in benefit programs",
        ),
        CoreUseCase(
            id="citizen_engagement",
            name="Citizen Engagement",
            description="Personalized government service delivery",
            target_persona="Chief Digital Officer",
            business_problem="Siloed services frustrating citizens and creating inefficiency",
        ),
        CoreUseCase(
            id="procurement_intelligence",
            name="Procurement Intelligence",
            description="AI-powered contract and spend analysis",
            target_persona="Chief Procurement Officer",
            business_problem="Lack of visibility into government spending",
        ),
        CoreUseCase(
            id="workforce_optimization",
            name="Workforce Optimization",
            description="Internal operations and case management",
            target_persona="HR Director",
            business_problem="Manual processes consuming staff time",
        ),
    ],
    economic_model_types=[
        EconomicModelType(
            id="efficiency_savings",
            name="Service Efficiency Savings",
            formula_shape="(Transactions × Time Saved × Hourly Cost) + (Error Reduction Value) = Savings",
            inputs=[
                "annual_transactions",
                "time_reduction_minutes",
                "hourly_cost",
                "error_reduction_value",
            ],
            output_unit="Annual savings $",
            typical_range="$500K-5M",
        ),
        EconomicModelType(
            id="fraud_prevention",
            name="Fraud Prevention Value",
            formula_shape="(Cases Prevented × Average Loss) + (Recovery Value) - Platform Cost = Net Value",
            inputs=[
                "baseline_fraud_cases",
                "prevention_rate",
                "avg_fraud_loss",
                "recovery_amount",
            ],
            output_unit="Annual value $",
            typical_range="$2M-20M",
        ),
        EconomicModelType(
            id="compliance_value",
            name="Compliance Value",
            formula_shape="(Penalty Avoidance) + (Audit Cost Reduction) + (Corrective Action Savings) = Total Value",
            inputs=[
                "historical_penalties",
                "audit_cost_reduction",
                "corrective_action_savings",
            ],
            output_unit="Annual value $",
            typical_range="$1M-8M",
        ),
        EconomicModelType(
            id="operational_roi",
            name="Operational ROI",
            formula_shape="(FTE Hours Saved × Loaded Cost) + (Process Cost Reduction) - Platform Cost = Value",
            inputs=[
                "fte_hours_saved",
                "loaded_hourly_cost",
                "process_cost_reduction",
                "platform_cost",
            ],
            output_unit="Annual value $",
            typical_range="$1M-10M",
        ),
    ],
    proof_requirements=[
        ProofRequirement(
            id="federal_compliance",
            requirement="Federal compliance validation",
            evidence_type="FedRAMP, FISMA, NIST compliance",
            minimum_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        ),
        ProofRequirement(
            id="audit_evidence",
            requirement="Audit-ready evidence",
            evidence_type="GAO-compliant documentation and trails",
            minimum_level=EvidenceLevel.PEER_REVIEWED_AUDITED,
        ),
        ProofRequirement(
            id="citizen_impact",
            requirement="Citizen impact measurement",
            evidence_type="Service level measurement",
            minimum_level=EvidenceLevel.CUSTOMER_MEASURED,
        ),
    ],
    why_it_wins=[
        WinStatement(
            statement="FedRAMP authorized—security cleared for federal deployment",
            differentiation="Pre-authorized vs. lengthy agency ATO processes",
            proof_point="FedRAMP Moderate authorization achieved vs. 12-18 month typical timeline",
        ),
        WinStatement(
            statement="Public sector purpose-built—designed for government workflows, not enterprise retrofits",
            differentiation="Government-specific forms, processes, and compliance vs. generic adaptation",
            proof_point="90% faster implementation vs. enterprise platforms adapted to government",
        ),
        WinStatement(
            statement="Audit-ready by design—GAO and IG-compliant documentation from inception",
            differentiation="Built-in audit trails vs. retroactive documentation",
            proof_point="100% audit finding resolution rate vs. 70% industry average",
        ),
    ],
    endpoint_mappings=EndpointMappings(
        intelligence=EndpointContribution(
            enabled=True,
            contribution_summary="Public sector intelligence: policy updates, program guidelines, grant opportunities",
            data_format="Government data enrichment",
            specific_assets=["policy_alert_feed", "grant_opportunity_api"],
        ),
        ai_model=EndpointContribution(
            enabled=True,
            contribution_summary="Public sector models: fraud detection, eligibility screening, document processing",
            data_format="Government-compliant ML models",
            specific_assets=["fraud_detector_public", "eligibility_scorer"],
        ),
        driver_tree=EndpointContribution(
            enabled=True,
            contribution_summary="Public sector driver trees: service quality → citizen satisfaction → program outcomes",
            data_format="Government KPI relationships",
            specific_assets=["service_driver_tree", "program_outcome_tree"],
        ),
        calculator=EndpointContribution(
            enabled=True,
            contribution_summary="Public sector calculators: cost per service, fraud rate, program ROI",
            data_format="Government calculation engines",
            specific_assets=["cost_per_service_calc", "program_roi_calc"],
        ),
        value_case=EndpointContribution(
            enabled=True,
            contribution_summary="Legislative and executive narratives with service and fiscal metrics",
            data_format="Government narratives + program visualizations",
            specific_assets=["legislative_template", "executive_report"],
        ),
    ),
    composable_model_templates=[
        ComposableModelTemplate(
            template_id="efficiency_savings",
            template_name="Efficiency Savings Model",
            formula_pattern="(Transactions × Time × Cost) + Error Value",
            inputs_required=[
                "transactions",
                "time_saved",
                "hourly_cost",
                "error_value",
            ],
            output_definition="Annual efficiency savings",
            applicable_industries=["public_sector", "healthcare", "financial_services"],
            example_calculation="(100K transactions × 15 min × $45/hr) + $100K = $1.2M savings",
        ),
        ComposableModelTemplate(
            template_id="fraud_prevention",
            template_name="Fraud Prevention Value",
            formula_pattern="(Cases × Loss × Prevention Rate) + Recovery",
            inputs_required=["cases", "avg_loss", "prevention_rate", "recovery"],
            output_definition="Annual fraud value",
            applicable_industries=["public_sector", "financial_services"],
            example_calculation="(500 cases × $50K × 80%) + $200K = $20.2M value",
        ),
        ComposableModelTemplate(
            template_id="compliance_automation",
            template_name="Compliance Automation",
            formula_pattern="(Hours × Cost × FTEs) + Penalties - Platform",
            inputs_required=["hours", "cost", "ftes", "penalties", "platform_cost"],
            output_definition="Annual compliance savings",
            applicable_industries=["public_sector", "healthcare", "financial_services"],
            example_calculation="(60 hrs/week × $65/hr × 4 FTEs) + $300K - $150K = $1.1M savings",
        ),
    ],
    pre_wired_ontology_tags=[
        OntologyTag(
            tag="public_sector",
            category="industry",
            related_tags=["government", "federal", "state", "local"],
        ),
        OntologyTag(
            tag="citizen_service",
            category="value_driver",
            related_tags=["efficiency", "access", "satisfaction"],
        ),
        OntologyTag(
            tag="fraud_prevention",
            category="value_driver",
            related_tags=["improper_payments", "waste", "abuse"],
        ),
        OntologyTag(
            tag="compliance",
            category="compliance",
            related_tags=["audit", "regulatory", "standards"],
        ),
        OntologyTag(
            tag="headcount_efficiency",
            category="value_driver",
            related_tags=["process_automation", "casework_efficiency"],
        ),
        OntologyTag(
            tag="fedramp",
            category="compliance",
            related_tags=["security", "authorization", "cloud"],
        ),
    ],
    pre_built_economic_graph=PreBuiltEconomicGraph(
        nodes=[
            EconomicNode(
                node_id="program_budget",
                node_type="driver",
                name="Program Budget",
                description="Total agency program spend",
                default_value="$50M",
            ),
            EconomicNode(
                node_id="citizens_served",
                node_type="metric",
                name="Citizens Served",
                description="Service delivery volume",
                default_value="500K",
            ),
            EconomicNode(
                node_id="fraud_losses",
                node_type="outcome",
                name="Fraud Losses",
                description="Improper payments and fraud",
                default_value="$3M",
            ),
            EconomicNode(
                node_id="service_cost",
                node_type="driver",
                name="Service Delivery Cost",
                description="Cost per transaction",
                default_value="$45",
            ),
            EconomicNode(
                node_id="compliance_score",
                node_type="metric",
                name="Compliance Score",
                description="Audit and regulatory compliance",
                default_value="88%",
            ),
            EconomicNode(
                node_id="platform_intervention",
                node_type="intervention",
                name="AI Government Platform",
                description="Service and fraud optimization",
                default_value="Deployed",
            ),
            EconomicNode(
                node_id="citizen_satisfaction",
                node_type="outcome",
                name="Citizen Satisfaction",
                description="Service satisfaction rating",
                default_value="3.8/5",
            ),
        ],
        relationships=[
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="fraud_losses",
                relationship_type="enables",
                weight=-0.5,
                formula="-50%",
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="service_cost",
                relationship_type="enables",
                weight=-0.25,
                formula="-25%",
            ),
            EconomicRelationship(
                from_node_id="service_cost",
                to_node_id="program_budget",
                relationship_type="enables",
                weight=-0.3,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="citizens_served",
                relationship_type="drives",
                weight=0.2,
                formula="+20% capacity",
            ),
            EconomicRelationship(
                from_node_id="citizens_served",
                to_node_id="citizen_satisfaction",
                relationship_type="enables",
                weight=0.3,
            ),
            EconomicRelationship(
                from_node_id="platform_intervention",
                to_node_id="compliance_score",
                relationship_type="drives",
                weight=0.12,
                formula="+12%",
            ),
            EconomicRelationship(
                from_node_id="fraud_losses",
                to_node_id="program_budget",
                relationship_type="enables",
                weight=-0.06,
            ),
        ],
        root_node_id="program_budget",
        graph_description="Public sector program efficiency, fraud prevention, and citizen service optimization",
    ),
    evidence_framework=EvidenceFramework(
        hierarchy=[
            EvidenceHierarchyRule(
                level=EvidenceLevel.PEER_REVIEWED_AUDITED,
                label="Peer-Reviewed / Audited",
                requirements=[
                    "GAO audit validation",
                    "Academic public administration research",
                ],
                acceptable_sources=["GAO reports", "Public Administration Review"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.THIRD_PARTY_VALIDATED,
                label="Third-Party Validated",
                requirements=["FedRAMP assessment", "IG audit success"],
                acceptable_sources=["FedRAMP JAB", "Office of Inspector General"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.CUSTOMER_MEASURED,
                label="Customer Measured",
                requirements=[
                    "Agency internal measurement",
                    "Program evaluation results",
                ],
                acceptable_sources=["Agency performance data", "Program analytics"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.PLATFORM_BENCHMARKED,
                label="Platform Benchmarked",
                requirements=[
                    "Cross-agency aggregate data",
                    "Anonymized performance metrics",
                ],
                acceptable_sources=["Platform government network", "Benchmark studies"],
            ),
            EvidenceHierarchyRule(
                level=EvidenceLevel.INDUSTRY_ESTIMATED,
                label="Industry Estimated",
                requirements=["OMB guidance alignment", "Federal standards"],
                acceptable_sources=["OMB A-11", "Federal performance standards"],
            ),
        ],
        required_level=EvidenceLevel.THIRD_PARTY_VALIDATED,
        validation_rules=[
            "All claims must align with OMB A-11 guidance",
            "Fraud claims require documented improper payment rates",
        ],
    ),
    metadata=ValuePackMetadata(
        deal_size_range="$200K-2M ACV",
        sales_cycle_length="6-24 months",
        switching_cost=SwitchingCost.HIGH,
        data_richness=DataRichness.MEDIUM,
        feedback_loop_speed=FeedbackLoopSpeed.SLOW,
    ),
)

DEFAULT_VALUEPACKS = [
    ENTERPRISE_SAAS_VALUEPACK,
    HEALTHCARE_VALUEPACK,
    MANUFACTURING_VALUEPACK,
    FINANCIAL_SERVICES_VALUEPACK,
    ENERGY_UTILITIES_VALUEPACK,
    RETAIL_ECOMMERCE_VALUEPACK,
    LOGISTICS_SUPPLY_CHAIN_VALUEPACK,
    PUBLIC_SECTOR_VALUEPACK,
]
