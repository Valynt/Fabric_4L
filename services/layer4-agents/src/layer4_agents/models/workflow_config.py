from __future__ import annotations

"""Workflow configuration models.

Defines node configurations, edges, and conditional routing for workflows.
"""


from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    """Types of workflow nodes."""

    START = "start"
    END = "end"
    TOOL = "tool"
    LLM = "llm"
    CONDITION = "condition"
    AGENT = "agent"
    PARALLEL = "parallel"
    AGGREGATE = "aggregate"


class EdgeType(str, Enum):
    """Types of edges between nodes."""

    DEFAULT = "default"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    ERROR = "error"


class NodeConfig(BaseModel):
    """Configuration for a single workflow node.

    Attributes:
        id: Unique node identifier
        name: Human-readable node name
        node_type: Type of node
        tool_name: Tool to execute (for TOOL nodes)
        llm_prompt: Prompt template (for LLM nodes)
        condition: Condition expression (for CONDITION nodes)
        config: Additional node-specific configuration
        retry_policy: Retry configuration
        timeout_seconds: Maximum execution time
    """

    id: str
    name: str
    node_type: NodeType
    tool_name: str | None = None
    llm_prompt: str | None = None
    condition: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff_factor": 1.5}
    )
    timeout_seconds: int = 30

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str | None, info: Any) -> str | None:
        values = info.data
        if values.get("node_type") == NodeType.TOOL and not v:
            raise ValueError("tool_name is required for TOOL nodes")
        return v


class EdgeConfig(BaseModel):
    """Configuration for an edge between nodes.

    Attributes:
        source: Source node ID
        target: Target node ID
        edge_type: Type of edge
        condition: Condition for conditional edges
        priority: Priority for multiple edges from same source
    """

    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: str | None = None
    priority: int = 0


class WorkflowConfig(BaseModel):
    """Complete workflow configuration.

    Attributes:
        workflow_type: Type of workflow
        name: Human-readable workflow name
        description: Workflow description
        nodes: List of node configurations
        edges: List of edge configurations
        entry_point: Starting node ID
        global_config: Global workflow settings
        interrupt_before: Nodes to interrupt before (native LangGraph HITL)
        interrupt_after: Nodes to interrupt after (native LangGraph HITL)
    """

    workflow_type: str
    name: str
    description: str
    nodes: list[NodeConfig]
    edges: list[EdgeConfig]
    entry_point: str
    global_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "max_iterations": 50,
            "checkpoint_interval": 5,
            "enable_tracing": True,
        }
    )
    interrupt_before: list[str] | None = None
    interrupt_after: list[str] | None = None

    @field_validator("edges")
    @classmethod
    def validate_connected(cls, v: list[EdgeConfig], info: Any) -> list[EdgeConfig]:
        values = info.data
        nodes = values.get("nodes", [])
        node_ids = {n.id for n in nodes}
        entry = values.get("entry_point")

        if entry and entry not in node_ids:
            raise ValueError(f"Entry point '{entry}' not found in nodes")

        for edge in v:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' not found in nodes")

        return v


# Predefined workflow configurations
ROI_WORKFLOW_CONFIG = WorkflowConfig(
    workflow_type="roi_calculator",
    name="ROI Calculator",
    description="Calculates ROI from value driver formulas with prospect data",
    entry_point="load_prospect",
    nodes=[
        NodeConfig(
            id="load_prospect",
            name="Load Prospect Data",
            node_type=NodeType.TOOL,
            tool_name="get_prospect_data",
        ),
        NodeConfig(
            id="fetch_benchmarks",
            name="Fetch Benchmarks",
            node_type=NodeType.TOOL,
            tool_name="fetch_benchmarks",
        ),
        NodeConfig(
            id="substitute_vars",
            name="Substitute Variables",
            node_type=NodeType.TOOL,
            tool_name="substitute_variables",
        ),
        NodeConfig(
            id="evaluate",
            name="Evaluate Formula",
            node_type=NodeType.TOOL,
            tool_name="evaluate_formula",
        ),
        NodeConfig(id="validate", name="Validate Results", node_type=NodeType.CONDITION),
        NodeConfig(
            id="aggregate", name="Aggregate ROI", node_type=NodeType.TOOL, tool_name="aggregate_roi"
        ),
        NodeConfig(
            id="generate_hypotheses",
            name="Generate ROI Hypotheses",
            node_type=NodeType.TOOL,
            tool_name="generate_hypotheses",
        ),
        NodeConfig(id="end", name="End", node_type=NodeType.END),
    ],
    edges=[
        EdgeConfig(source="load_prospect", target="fetch_benchmarks"),
        EdgeConfig(source="fetch_benchmarks", target="substitute_vars"),
        EdgeConfig(source="substitute_vars", target="evaluate"),
        EdgeConfig(source="evaluate", target="validate"),
        EdgeConfig(source="validate", target="aggregate", condition="results_valid"),
        EdgeConfig(
            source="validate", target="substitute_vars", condition="retry_needed", priority=1
        ),
        EdgeConfig(source="aggregate", target="generate_hypotheses"),
        EdgeConfig(source="generate_hypotheses", target="end"),
    ],
)

WHITESPACE_WORKFLOW_CONFIG = WorkflowConfig(
    workflow_type="whitespace_analysis",
    name="Whitespace Analysis",
    description="Identifies gaps between prospect needs and solution capabilities",
    entry_point="analyze_prospect",
    nodes=[
        NodeConfig(
            id="analyze_prospect",
            name="Analyze Prospect",
            node_type=NodeType.TOOL,
            tool_name="analyze_prospect_needs",
        ),
        NodeConfig(
            id="query_capabilities",
            name="Query Capabilities",
            node_type=NodeType.TOOL,
            tool_name="query_graph",
        ),
        NodeConfig(
            id="identify_gaps",
            name="Identify Gaps",
            node_type=NodeType.TOOL,
            tool_name="identify_gaps",
        ),
        NodeConfig(
            id="score_opportunity",
            name="Score Opportunity",
            node_type=NodeType.TOOL,
            tool_name="score_opportunity",
        ),
        NodeConfig(
            id="generate_hypotheses",
            name="Generate Whitespace Hypotheses",
            node_type=NodeType.TOOL,
            tool_name="generate_hypotheses",
        ),
        NodeConfig(id="end", name="End", node_type=NodeType.END),
    ],
    edges=[
        EdgeConfig(source="analyze_prospect", target="query_capabilities"),
        EdgeConfig(source="query_capabilities", target="identify_gaps"),
        EdgeConfig(source="identify_gaps", target="score_opportunity"),
        EdgeConfig(source="score_opportunity", target="generate_hypotheses"),
        EdgeConfig(source="generate_hypotheses", target="end"),
    ],
)

BUSINESS_CASE_WORKFLOW_CONFIG = WorkflowConfig(
    workflow_type="business_case",
    name="Business Case Generator",
    description="Generates comprehensive business case documents",
    entry_point="gather_inputs",
    nodes=[
        NodeConfig(
            id="gather_inputs",
            name="Gather Inputs",
            node_type=NodeType.TOOL,
            tool_name="gather_case_inputs",
        ),
        NodeConfig(id="run_roi", name="Run ROI Calculation", node_type=NodeType.AGENT),
        NodeConfig(
            id="verify_truth_requirements",
            name="Verify Truth Requirements",
            node_type=NodeType.TOOL,
            tool_name="verify_truth_requirements",
        ),
        NodeConfig(
            id="generate_narrative",
            name="Generate Narrative",
            node_type=NodeType.LLM,
            llm_prompt="generate_business_case_section",
        ),
        NodeConfig(
            id="validate_claims",
            name="Validate Claims",
            node_type=NodeType.LLM,
            llm_prompt="validate_claims",
        ),
        NodeConfig(
            id="assemble",
            name="Assemble Document",
            node_type=NodeType.TOOL,
            tool_name="assemble_document",
        ),
        NodeConfig(id="end", name="End", node_type=NodeType.END),
    ],
    edges=[
        EdgeConfig(source="gather_inputs", target="run_roi"),
        EdgeConfig(source="run_roi", target="verify_truth_requirements"),
        EdgeConfig(source="verify_truth_requirements", target="generate_narrative"),
        EdgeConfig(source="generate_narrative", target="validate_claims"),
        EdgeConfig(source="validate_claims", target="assemble"),
        EdgeConfig(source="assemble", target="end"),
    ],
)
