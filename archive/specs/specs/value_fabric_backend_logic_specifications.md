# Value Fabric SaaS Platform - Backend Logic Specifications
## Empowering Downstream Agentic Workflows + Ensuring Auditability and Provenance

---

## Table of Contents

1. [Agent Orchestration Framework](#1-agent-orchestration-framework)
2. [Whitespace Analysis Logic](#2-whitespace-analysis-logic)
3. [Business Case Generation](#3-business-case-generation)
4. [Provenance Tracking System](#4-provenance-tracking-system)
5. [API Interfaces](#5-api-interfaces)

---

## 1. Agent Orchestration Framework

### 1.1 Agent Types and Capabilities

#### Core Agent Taxonomy

```yaml
AgentRegistry:
  DocumentIngestionAgent:
    agent_id: "doc-ingest-{uuid}"
    agent_type: "EXTRACTION"
    capabilities:
      - document_parsing
      - ocr_processing
      - metadata_extraction
      - source_validation
    supported_formats:
      - application/pdf
      - text/html
      - text/plain
      - application/vnd.openxmlformats-officedocument
    max_document_size_mb: 100
    concurrent_jobs: 5
    
  FinancialExtractionAgent:
    agent_id: "fin-extract-{uuid}"
    agent_type: "ANALYSIS"
    capabilities:
      - sec_filing_parsing
      - earnings_call_transcription
      - financial_metric_extraction
      - risk_factor_identification
    llm_config:
      model: "gpt-4-turbo"
      temperature: 0.1
      max_tokens: 8000
    prompt_templates:
      - 10k_extraction_v2
      - earnings_analysis_v3
      - risk_assessment_v1
    
  ValueTreeProjectionAgent:
    agent_id: "vt-project-{uuid}"
    agent_type: "REASONING"
    capabilities:
      - semantic_matching
      - graph_traversal
      - node_classification
      - relationship_inference
    graph_operations:
      - value_tree_projection
      - capability_mapping
      - use_case_alignment
    
  WhitespaceAnalysisAgent:
    agent_id: "ws-analyze-{uuid}"
    agent_type: "SYNTHESIS"
    capabilities:
      - gap_identification
      - maturity_assessment
      - expansion_pathway_generation
      - account_plan_synthesis
    output_formats:
      - json_structured
      - markdown_report
      - presentation_deck
      
  ROICalculationAgent:
    agent_id: "roi-calc-{uuid}"
    agent_type: "COMPUTATION"
    capabilities:
      - formula_execution
      - metric_substitution
      - sensitivity_analysis
      - scenario_modeling
    execution_engine: "deterministic"
    formula_validation: true
    
  NarrativeSynthesisAgent:
    agent_id: "narrative-{uuid}"
    agent_type: "GENERATION"
    capabilities:
      - executive_summary_generation
      - slide_deck_creation
      - risk_proposal_drafting
      - stakeholder_alignment
    template_library:
      - c_suite_executive_summary
      - board_presentation
      - procurement_proposal
      - technical_architecture_review
      
  ProvenanceTrackingAgent:
    agent_id: "prov-track-{uuid}"
    agent_type: "AUDIT"
    capabilities:
      - prov_o_generation
      - rdf_star_annotation
      - lineage_tracking
      - decision_trace_construction
    storage_backend: "triple_store"
    
  OrchestrationController:
    agent_id: "orch-control-{uuid}"
    agent_type: "COORDINATION"
    capabilities:
      - workflow_scheduling
      - task_distribution
      - failure_recovery
      - resource_management
    scaling_policy:
      min_instances: 2
      max_instances: 50
      scale_trigger: "queue_depth > 100"
```

### 1.2 Workflow State Machines

```yaml
WorkflowDefinitions:
  WhitespaceAnalysisWorkflow:
    workflow_id: "ws-analysis-v2"
    version: "2.1.0"
    description: "End-to-end whitespace analysis for account planning"
    
    states:
      - name: "DOCUMENT_INGESTION"
        type: "task"
        agent_type: "DocumentIngestionAgent"
        timeout_seconds: 300
        retry_policy:
          max_retries: 3
          backoff_strategy: "exponential"
        
      - name: "FINANCIAL_EXTRACTION"
        type: "task"
        agent_type: "FinancialExtractionAgent"
        dependencies: ["DOCUMENT_INGESTION"]
        timeout_seconds: 600
        
      - name: "VALUE_TREE_PROJECTION"
        type: "task"
        agent_type: "ValueTreeProjectionAgent"
        dependencies: ["FINANCIAL_EXTRACTION"]
        timeout_seconds: 300
        
      - name: "WHITESPACE_IDENTIFICATION"
        type: "task"
        agent_type: "WhitespaceAnalysisAgent"
        dependencies: ["VALUE_TREE_PROJECTION"]
        timeout_seconds: 400
        
      - name: "ACCOUNT_PLAN_GENERATION"
        type: "task"
        agent_type: "NarrativeSynthesisAgent"
        dependencies: ["WHITESPACE_IDENTIFICATION"]
        timeout_seconds: 300
        
      - name: "PROVENANCE_RECORDING"
        type: "parallel"
        agent_type: "ProvenanceTrackingAgent"
        dependencies: ["ACCOUNT_PLAN_GENERATION"]
        runs_in_parallel: true
        
      - name: "COMPLETED"
        type: "terminal"
        
      - name: "FAILED"
        type: "terminal"
    
    transitions:
      - from: "DOCUMENT_INGESTION"
        to: "FINANCIAL_EXTRACTION"
        condition: "success"
        
      - from: "DOCUMENT_INGESTION"
        to: "FAILED"
        condition: "failure"
        
      - from: "FINANCIAL_EXTRACTION"
        to: "VALUE_TREE_PROJECTION"
        condition: "success"
        
      - from: "FINANCIAL_EXTRACTION"
        to: "FAILED"
        condition: "failure"
        
      - from: "VALUE_TREE_PROJECTION"
        to: "WHITESPACE_IDENTIFICATION"
        condition: "success"
        
      - from: "WHITESPACE_IDENTIFICATION"
        to: "ACCOUNT_PLAN_GENERATION"
        condition: "success"
        
      - from: "ACCOUNT_PLAN_GENERATION"
        to: "PROVENANCE_RECORDING"
        condition: "success"
        
      - from: "PROVENANCE_RECORDING"
        to: "COMPLETED"
        condition: "always"
    
    error_handling:
      on_failure: "notify_and_rollback"
      notification_channels: ["slack", "email"]
      rollback_strategy: "compensating_transactions"

  BusinessCaseGenerationWorkflow:
    workflow_id: "biz-case-gen-v3"
    version: "3.0.0"
    description: "Dynamic ROI calculation and business case generation"
    
    states:
      - name: "OPPORTUNITY_EVALUATION"
        type: "task"
        agent_type: "ValueTreeProjectionAgent"
        timeout_seconds: 180
        
      - name: "FORMULA_RETRIEVAL"
        type: "task"
        agent_type: "ROICalculationAgent"
        dependencies: ["OPPORTUNITY_EVALUATION"]
        timeout_seconds: 120
        
      - name: "METRIC_SUBSTITUTION"
        type: "task"
        agent_type: "ROICalculationAgent"
        dependencies: ["FORMULA_RETRIEVAL"]
        timeout_seconds: 60
        
      - name: "ROI_COMPUTATION"
        type: "task"
        agent_type: "ROICalculationAgent"
        dependencies: ["METRIC_SUBSTITUTION"]
        timeout_seconds: 120
        computation_type: "deterministic"
        
      - name: "SENSITIVITY_ANALYSIS"
        type: "task"
        agent_type: "ROICalculationAgent"
        dependencies: ["ROI_COMPUTATION"]
        timeout_seconds: 300
        optional: true
        
      - name: "NARRATIVE_SYNTHESIS"
        type: "task"
        agent_type: "NarrativeSynthesisAgent"
        dependencies: ["ROI_COMPUTATION"]
        timeout_seconds: 400
        
      - name: "OUTPUT_GENERATION"
        type: "parallel"
        agent_type: "NarrativeSynthesisAgent"
        dependencies: ["NARRATIVE_SYNTHESIS"]
        parallel_tasks:
          - executive_summary
          - slide_deck
          - risk_proposal
          
      - name: "PROVENANCE_RECORDING"
        type: "task"
        agent_type: "ProvenanceTrackingAgent"
        dependencies: ["OUTPUT_GENERATION"]
        
      - name: "COMPLETED"
        type: "terminal"
        
      - name: "FAILED"
        type: "terminal"
```

### 1.3 Task Scheduling and Execution

```python
# task_scheduler.py - Core Implementation

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

@dataclass(order=True)
class ScheduledTask:
    """Task scheduled for execution"""
    priority: int
    scheduled_time: datetime
    task_id: str = field(compare=False)
    workflow_instance_id: str = field(compare=False)
    state_name: str = field(compare=False)
    agent_type: str = field(compare=False)
    context: Dict[str, Any] = field(compare=False, default_factory=dict)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    timeout_seconds: int = field(compare=False, default=300)

class TaskScheduler:
    """Priority-based task scheduler with backpressure"""
    
    def __init__(self, max_concurrent_tasks: int = 100):
        self.task_queue: List[ScheduledTask] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._shutdown = False
        
    async def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a task for execution"""
        async with self._lock:
            heapq.heappush(self.task_queue, task)
            return task.task_id
    
    def _calculate_backoff(self, task: ScheduledTask) -> int:
        """Calculate exponential backoff"""
        base_delay = 2
        max_delay = 300
        delay = min(base_delay ** task.retry_count, max_delay)
        return delay
```

### 1.4 Inter-Agent Communication Patterns

```python
# agent_messaging.py - Core Implementation

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio

class MessageType(Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    COORDINATION = "coordination"
    PROVENANCE_EVENT = "provenance_event"

@dataclass
class AgentMessage:
    """Message passed between agents"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    workflow_instance_id: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    priority: int = 5  # 1-10, lower is higher priority

class MessageBus:
    """Async message bus for inter-agent communication"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[AgentMessage] = []
```

---

## 2. Whitespace Analysis Logic

### 2.1 Document Ingestion Pipeline

```python
# document_ingestion.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, BinaryIO, Any
from datetime import datetime
from enum import Enum
import hashlib

class DocumentType(Enum):
    SEC_10K = "10-K"
    SEC_10Q = "10-Q"
    EARNINGS_CALL_TRANSCRIPT = "earnings_call"
    PRESS_RELEASE = "press_release"
    INVESTOR_PRESENTATION = "investor_presentation"
    ANNUAL_REPORT = "annual_report"
    CUSTOM_DOCUMENT = "custom"

@dataclass
class DocumentMetadata:
    """Metadata for ingested documents"""
    document_id: str
    source_url: Optional[str]
    company_name: str
    company_ticker: Optional[str]
    document_type: DocumentType
    fiscal_year: Optional[int]
    fiscal_quarter: Optional[int]
    filing_date: Optional[datetime]
    period_end_date: Optional[datetime]
    file_hash: str
    file_size_bytes: int
    page_count: Optional[int]
    ingestion_timestamp: datetime
    extraction_status: str = "pending"

@dataclass
class DocumentSegment:
    """Segment of a parsed document"""
    segment_id: str
    document_id: str
    segment_type: str  # 'section', 'paragraph', 'table', 'heading'
    content: str
    page_number: Optional[int]
    section_heading: Optional[str]
    hierarchy_level: int
    metadata: Dict[str, Any]
    embedding_vector: Optional[List[float]] = None
```

### 2.2 Pain Point Extraction

```python
# pain_point_extraction.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class PainPointCategory(Enum):
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    COST_MANAGEMENT = "cost_management"
    REVENUE_GROWTH = "revenue_growth"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    TECHNOLOGY_MODERNIZATION = "technology_modernization"
    TALENT_ACQUISITION = "talent_acquisition"
    CUSTOMER_EXPERIENCE = "customer_experience"
    SUPPLY_CHAIN = "supply_chain"
    DATA_MANAGEMENT = "data_management"
    RISK_MANAGEMENT = "risk_management"

class PainPointSeverity(Enum):
    CRITICAL = 5
    HIGH = 4
    MODERATE = 3
    LOW = 2
    MINIMAL = 1

@dataclass
class ExtractedPainPoint:
    """Pain point extracted from document"""
    pain_point_id: str
    source_document_id: str
    source_segment_id: str
    category: PainPointCategory
    severity: PainPointSeverity
    description: str
    original_text: str
    confidence_score: float
    related_capabilities: List[str]
    extraction_timestamp: datetime
    llm_model: str
    prompt_version: str

EXTRACTION_PROMPT_TEMPLATE = """
Analyze the following text from a {document_type} filing for {company_name}.
Identify operational challenges, strategic goals, and pain points mentioned.

TEXT:
{text}

For each pain point identified, provide:
1. Category (choose from: operational_efficiency, cost_management, revenue_growth, 
   regulatory_compliance, technology_modernization, talent_acquisition, 
   customer_experience, supply_chain, data_management, risk_management)
2. Severity level (critical, high, moderate, low, minimal)
3. Detailed description
4. Confidence score (0.0-1.0)
5. Relevant verbatim text

Format as JSON array.
"""
```

### 2.3 Value Tree Projection Algorithms

```python
# value_tree_projection.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

@dataclass
class ValueTreeNode:
    """Node in the Value Tree"""
    node_id: str
    node_type: str  # 'outcome', 'value_driver', 'use_case', 'capability', 'feature'
    name: str
    description: str
    parent_ids: List[str]
    child_ids: List[str]
    metrics: List[Dict[str, Any]]
    formulas: List[Dict[str, Any]]
    semantic_embedding: List[float]
    metadata: Dict[str, Any]

@dataclass
class ProjectionResult:
    """Result of projecting pain points onto Value Tree"""
    projection_id: str
    pain_point_id: str
    matched_nodes: List[Dict[str, Any]]
    match_scores: Dict[str, float]
    traversal_path: List[str]
    confidence: float
    projection_timestamp: datetime

# Cypher queries for Value Tree traversal
UPWARD_TRAVERSAL_QUERY = """
MATCH path = (start:ValueTreeNode {node_id: $start_id})-[:CONTRIBUTES_TO*1..5]->(outcome:ValueTreeNode {node_type: 'outcome'})
RETURN [node in nodes(path) | node.node_id] as path_nodes,
       [rel in relationships(path) | type(rel)] as path_relationships,
       length(path) as path_length
"""

DOWNWARD_TRAVERSAL_QUERY = """
MATCH path = (start:ValueTreeNode {node_id: $start_id})<-[:REQUIRES*1..5]-(capability:ValueTreeNode {node_type: 'capability'})
RETURN [node in nodes(path) | node.node_id] as path_nodes,
       [rel in relationships(path) | type(rel)] as path_relationships,
       length(path) as path_length
"""

SEMANTIC_MATCH_QUERY = """
MATCH (n:ValueTreeNode)
WHERE n.semantic_embedding IS NOT NULL
RETURN n.node_id, n.name, n.node_type, n.semantic_embedding
"""
```

### 2.4 Gap Identification Logic

```python
# gap_identification.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum

class GapType(Enum):
    MISSING_CAPABILITY = "missing_capability"
    UNDERUTILIZED_CAPABILITY = "underutilized_capability"
    MATURITY_GAP = "maturity_gap"
    INTEGRATION_GAP = "integration_gap"

class MaturityLevel(Enum):
    AD_HOC = 1
    DEVELOPING = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZING = 5

@dataclass
class IdentifiedGap:
    """Gap identified during whitespace analysis"""
    gap_id: str
    gap_type: GapType
    prospect_company: str
    required_capability_id: str
    required_capability_name: str
    current_state: Optional[str]
    target_state: str
    maturity_gap: Optional[int]
    business_impact: str
    estimated_value: Optional[float]
    confidence_score: float
    supporting_evidence: List[str]
    related_pain_points: List[str]
    expansion_pathways: List[Dict[str, Any]]

# Cypher query for extracting required capabilities
REQUIRED_CAPABILITIES_QUERY = """
MATCH (n:ValueTreeNode {node_id: $node_id})-[:REQUIRES*1..3]->(c:Capability)
RETURN c.node_id, c.name, c.description, c.maturity_indicators,
       c.typical_implementations, c.success_metrics
"""

# Cypher query for expansion pathways
EXPANSION_PATHWAYS_QUERY = """
MATCH (c:Capability {node_id: $cap_id})<-[:REQUIRES]-(uc:UseCase)
OPTIONAL MATCH (uc)-[:IMPLEMENTS]->(vd:ValueDriver)
OPTIONAL MATCH (uc)-[:TARGETS]->(p:Persona)
RETURN uc.node_id, uc.name, uc.description, uc.implementation_complexity,
       collect(DISTINCT vd.name) as value_drivers,
       collect(DISTINCT p.name) as target_personas
ORDER BY uc.implementation_complexity
"""
```

### 2.5 Account Plan Generation

```python
# account_plan_generation.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class AccountPlanStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    ARCHIVED = "archived"

@dataclass
class AccountPlan:
    """Generated account plan"""
    plan_id: str
    prospect_company: str
    prospect_ticker: Optional[str]
    generated_at: datetime
    status: AccountPlanStatus
    
    # Executive Summary
    executive_summary: str
    key_insights: List[str]
    strategic_alignment_score: float
    
    # Gap Analysis
    identified_gaps: List[IdentifiedGap]
    gap_summary_by_category: Dict[str, int]
    total_estimated_value: float
    
    # Expansion Pathways
    expansion_pathways: List[Dict[str, Any]]
    prioritized_initiatives: List[Dict[str, Any]]
    
    # Multi-threaded Strategy
    business_unit_targets: List[Dict[str, Any]]
    stakeholder_map: List[Dict[str, Any]]
    engagement_sequence: List[Dict[str, Any]]
    
    # Supporting Materials
    source_documents: List[str]
    confidence_assessment: Dict[str, float]
    risk_factors: List[str]
```

---

## 3. Business Case Generation

### 3.1 ROI Calculation Workflows

```python
# roi_calculation.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

@dataclass
class FormulaNode:
    """Formula stored in graph"""
    formula_id: str
    name: str
    description: str
    formula_expression: str  # Mathematical expression
    variables: List[Dict[str, Any]]  # Variable definitions
    constants: Dict[str, float]
    output_metric: str
    applicable_personas: List[str]
    applicable_use_cases: List[str]
    assumptions: List[str]
    validation_rules: List[str]

@dataclass
class ROIResult:
    """Result of ROI calculation"""
    calculation_id: str
    formula_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    intermediate_values: Dict[str, float]
    execution_trace: List[Dict[str, Any]]
    confidence_score: float
    sensitivity_analysis: Optional[Dict[str, Any]]
    calculation_timestamp: datetime

# Formula retrieval query
FORMULA_RETRIEVAL_QUERY = """
MATCH (uc:UseCase {node_id: $use_case_id})-[:GENERATES]->(vd:ValueDriver)
MATCH (vd)-[:CALCULATED_BY]->(f:Formula)
RETURN f.formula_id, f.name, f.description, f.formula_expression,
       f.variables, f.constants, f.output_metric, f.assumptions
"""

# Safe execution environment for formulas
SAFE_EXECUTION_DICT = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
    'Decimal': Decimal
}
```

### 3.2 Formula Retrieval and Execution

```python
# formula_management.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Cypher query for creating formula
CREATE_FORMULA_QUERY = """
CREATE (f:Formula {
    formula_id: $formula_id,
    name: $name,
    description: $description,
    formula_expression: $expression,
    variables: $variables,
    constants: $constants,
    output_metric: $output_metric,
    assumptions: $assumptions,
    created_at: datetime(),
    version: '1.0'
})
RETURN f.formula_id
"""

# Cypher query for linking formula to use case
LINK_FORMULA_QUERY = """
MATCH (f:Formula {formula_id: $formula_id})
MATCH (uc:UseCase {node_id: $use_case_id})
MATCH (vd:ValueDriver)
WHERE vd.node_id IN uc.value_driver_ids
CREATE (vd)-[:CALCULATED_BY]->(f)
"""
```

### 3.3 Narrative Synthesis Logic

```python
# narrative_synthesis.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class OutputFormat(Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    SLIDE_DECK = "slide_deck"
    RISK_PROPOSAL = "risk_proposal"
    TECHNICAL_SPEC = "technical_spec"
    BOARD_PRESENTATION = "board_presentation"

@dataclass
class SynthesizedNarrative:
    """Synthesized narrative output"""
    narrative_id: str
    format: OutputFormat
    title: str
    content: Dict[str, Any]
    raw_text: str
    structured_data: Dict[str, Any]
    generated_at: datetime
    template_used: str
    customization_applied: Dict[str, Any]

# Standard slide deck structure
SLIDE_DECK_STRUCTURE = [
    {'slide_number': 1, 'layout': 'title', 'title': 'Business Case'},
    {'slide_number': 2, 'layout': 'executive_summary', 'title': 'Executive Summary'},
    {'slide_number': 3, 'layout': 'challenges', 'title': 'Current State Challenges'},
    {'slide_number': 4, 'layout': 'solution', 'title': 'Proposed Solution'},
    {'slide_number': 5, 'layout': 'financial', 'title': 'Financial Analysis'},
    {'slide_number': 6, 'layout': 'sensitivity', 'title': 'Sensitivity Analysis'},
    {'slide_number': 7, 'layout': 'roadmap', 'title': 'Implementation Roadmap'},
    {'slide_number': 8, 'layout': 'risks', 'title': 'Risk Mitigation'},
    {'slide_number': 9, 'layout': 'next_steps', 'title': 'Recommended Next Steps'}
]
```

### 3.4 Output Formatting and Template Management

```python
# template_management.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Template:
    """Template for narrative generation"""
    template_id: str
    name: str
    description: str
    format_type: str
    version: str
    content: str  # Jinja2 template or similar
    variables: List[Dict[str, Any]]
    styles: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

# Template filters
TEMPLATE_FILTERS = {
    'currency': 'format_currency',
    'percentage': 'format_percentage',
    'number': 'format_number',
    'month_year': 'format_month_year'
}

# Default templates
DEFAULT_TEMPLATES = {
    'executive_summary_v2': 'executive_summary_template',
    'slide_deck_standard_v3': 'slide_deck_template',
    'risk_proposal_v1': 'risk_proposal_template'
}
```

---

## 4. Provenance Tracking System

### 4.1 PROV-O Implementation Schema

```python
# provenance_schema.py - PROV-O Schema Definition

"""
PROV-O (Provenance Ontology) Implementation for Value Fabric

PROV-O Core Classes:
- prov:Entity - Things that exist
- prov:Activity - Processes that create/change entities  
- prov:Agent - Responsible for activities

PROV-O Core Properties:
- prov:wasGeneratedBy - Entity -> Activity
- prov:wasDerivedFrom - Entity -> Entity
- prov:wasAttributedTo - Entity -> Agent
- prov:used - Activity -> Entity
- prov:wasAssociatedWith - Activity -> Agent
- prov:actedOnBehalfOf - Agent -> Agent
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class PROVEntityType(Enum):
    DOCUMENT = "prov:Entity:Document"
    SEGMENT = "prov:Entity:Segment"
    PAIN_POINT = "prov:Entity:PainPoint"
    VALUE_NODE = "prov:Entity:ValueNode"
    CALCULATION = "prov:Entity:Calculation"
    NARRATIVE = "prov:Entity:Narrative"
    ACCOUNT_PLAN = "prov:Entity:AccountPlan"
    FORMULA = "prov:Entity:Formula"

class PROVActivityType(Enum):
    DOCUMENT_INGESTION = "prov:Activity:DocumentIngestion"
    EXTRACTION = "prov:Activity:Extraction"
    PROJECTION = "prov:Activity:Projection"
    TRAVERSAL = "prov:Activity:Traversal"
    CALCULATION = "prov:Activity:Calculation"
    SYNTHESIS = "prov:Activity:Synthesis"
    PLAN_GENERATION = "prov:Activity:PlanGeneration"

class PROVAgentType(Enum):
    LLM_MODEL = "prov:Agent:LLMModel"
    AI_AGENT = "prov:Agent:AIAgent"
    USER = "prov:Agent:User"
    SYSTEM = "prov:Agent:System"
    EXTERNAL_SERVICE = "prov:Agent:ExternalService"

# Namespace definitions
PROV_NAMESPACES = {
    'prov': 'http://www.w3.org/ns/prov#',
    'vf': 'http://valuefabric.io/prov/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'rdf-star': 'http://www.w3.org/ns/rdf-star#'
}

# PROV-O Cypher queries
CREATE_ENTITY_QUERY = """
CREATE (e:PROVEntity:{{ entity_type }} {
    entity_id: $entity_id,
    entity_type: $entity_type,
    label: $label,
    generated_at: datetime(),
    {{ additional_properties }}
})
RETURN e.entity_id
"""

CREATE_ACTIVITY_QUERY = """
CREATE (a:PROVActivity:{{ activity_type }} {
    activity_id: $activity_id,
    activity_type: $activity_type,
    label: $label,
    started_at: datetime(),
    {{ additional_properties }}
})
RETURN a.activity_id
"""

WAS_GENERATED_BY_QUERY = """
MATCH (e:PROVEntity {entity_id: $entity_id})
MATCH (a:PROVActivity {activity_id: $activity_id})
CREATE (e)-[:wasGeneratedBy {timestamp: datetime()}]->(a)
"""

USED_QUERY = """
MATCH (a:PROVActivity {activity_id: $activity_id})
MATCH (e:PROVEntity {entity_id: $entity_id})
CREATE (a)-[:used {timestamp: datetime()}]->(e)
"""

WAS_ATTRIBUTED_TO_QUERY = """
MATCH (e:PROVEntity {entity_id: $entity_id})
MATCH (ag:PROVAgent {agent_id: $agent_id})
CREATE (e)-[:wasAttributedTo {timestamp: datetime()}]->(ag)
"""

WAS_ASSOCIATED_WITH_QUERY = """
MATCH (a:PROVActivity {activity_id: $activity_id})
MATCH (ag:PROVAgent {agent_id: $agent_id})
CREATE (a)-[:wasAssociatedWith {timestamp: datetime(), role: $role}]->(ag)
"""

WAS_DERIVED_FROM_QUERY = """
MATCH (e1:PROVEntity {entity_id: $derived_entity_id})
MATCH (e2:PROVEntity {entity_id: $source_entity_id})
CREATE (e1)-[:wasDerivedFrom {timestamp: datetime(), derivation_type: $derivation_type}]->(e2)
"""
```

### 4.2 RDF-star Annotation Patterns

```python
# rdf_star_implementation.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

@dataclass
class RDFStarAnnotation:
    """RDF-star annotation for an edge"""
    annotation_id: str
    subject: str
    predicate: str
    object: str
    annotations: Dict[str, Any]
    created_at: datetime

# RDF-star schema for mathematical operations
RDF_STAR_SCHEMA = """
RDF-star allows making statements about statements (annotating edges).

Example for ROI calculation edge:

<<(:calculation123 :produces :roi_value_456)>> 
    vf:executionTrace "{trace_data}";
    vf:algorithmVersion "2.1.0";
    vf:executedAt "2024-01-15T10:30:00Z"^^xsd:dateTime.

This creates a triple about a triple, enabling:
- Full execution trace storage on edges
- Algorithm versioning
- Precise timestamping of operations
"""

# Cypher for RDF-star annotation
CREATE_RDF_STAR_ANNOTATION = """
INSERT DATA {
    <<(vf:{{ subject }} vf:{{ predicate }} vf:{{ object }})>>
        vf:executionTrace $execution_trace;
        vf:algorithmVersion $algorithm_version;
        vf:executedAt $executed_at;
        vf:executedBy $executed_by;
        vf:inputValues $input_values;
        vf:outputValue $output_value.
}
"""

QUERY_RDF_STAR_ANNOTATION = """
SELECT ?trace ?version ?executedAt
WHERE {
    <<(vf:{{ subject }} vf:{{ predicate }} vf:{{ object }})>>
        vf:executionTrace ?trace;
        vf:algorithmVersion ?version;
        vf:executedAt ?executedAt.
}
"""
```

### 4.3 Decision Trace Construction

```python
# decision_trace.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class DecisionStepType(Enum):
    INPUT = "input"
    EXTRACTION = "extraction"
    PROJECTION = "projection"
    TRAVERSAL = "traversal"
    CALCULATION = "calculation"
    SYNTHESIS = "synthesis"
    OUTPUT = "output"

@dataclass
class DecisionStep:
    """Single step in a decision trace"""
    step_id: str
    step_type: DecisionStepType
    step_number: int
    timestamp: datetime
    description: str
    input_refs: List[str]
    output_refs: List[str]
    agent_id: Optional[str]
    llm_model: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]
    supporting_evidence: List[Dict[str, Any]]
    alternatives_considered: List[Dict[str, Any]]

@dataclass
class DecisionTrace:
    """Complete decision trace for an AI-generated output"""
    trace_id: str
    workflow_id: str
    workflow_instance_id: str
    output_type: str
    output_id: str
    created_at: datetime
    completed_at: Optional[datetime]
    steps: List[DecisionStep]
    final_output_ref: str
    audit_status: str
    verification_hash: str

# Cypher query for trace reconstruction
RECONSTRUCT_TRACE_QUERY = """
MATCH (output:PROVEntity {entity_id: $output_id})
MATCH (output)-[:wasGeneratedBy*]->(activity:PROVActivity)
MATCH (activity)-[:used]->(input:PROVEntity)
OPTIONAL MATCH (activity)-[:wasAssociatedWith]->(agent:PROVAgent)
RETURN activity.activity_id, activity.activity_type, activity.started_at,
       collect(DISTINCT input.entity_id) as inputs,
       agent.agent_id, agent.agent_type
ORDER BY activity.started_at
"""
```

### 4.4 Audit Trail Storage and Retrieval

```python
# audit_trail.py - Core Implementation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class AuditEventType(Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    AGENT_INVOKED = "agent_invoked"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    EXTRACTION_PERFORMED = "extraction_performed"
    CALCULATION_EXECUTED = "calculation_executed"
    NARRATIVE_GENERATED = "narrative_generated"
    PROVENANCE_RECORDED = "provenance_recorded"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"

@dataclass
class AuditEvent:
    """Single audit event"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    workflow_id: Optional[str]
    workflow_instance_id: Optional[str]
    agent_id: Optional[str]
    user_id: Optional[str]
    tenant_id: str
    severity: str
    message: str
    details: Dict[str, Any]
    provenance_refs: List[str]
```

### 4.5 Lineage Visualization Logic

```python
# lineage_visualization.py - Core Implementation

from typing import Dict, List, Any

# Cypher query for lineage traversal
LINEAGE_QUERY = """
MATCH (target:PROVEntity {entity_id: $entity_id})
CALL apoc.path.subgraphNodes(target, {
    relationshipFilter: "wasDerivedFrom>|<wasGeneratedBy>|<used",
    minLevel: 0,
    maxLevel: 10
}) YIELD node
WITH node
OPTIONAL MATCH (node)-[r]->(related)
WHERE type(r) IN ['wasDerivedFrom', 'wasGeneratedBy', 'used', 'wasAttributedTo', 'wasAssociatedWith']
RETURN node, collect(DISTINCT {rel: type(r), target: related.entity_id}) as relationships
"""

# Cypher query for backward trace (from output to sources)
BACKWARD_TRACE_QUERY = """
MATCH (output:PROVEntity {entity_id: $entity_id})
CALL apoc.path.expandConfig(output, {
    relationshipFilter: "wasDerivedFrom>|<wasGeneratedBy|<used",
    minLevel: 1,
    maxLevel: 20,
    uniqueness: "NODE_GLOBAL"
}) YIELD path
RETURN [node in nodes(path) | node.entity_id] as lineage_path,
       [rel in relationships(path) | type(rel)] as relation_types
"""

# Cypher query for forward trace (from source to all outputs)
FORWARD_TRACE_QUERY = """
MATCH (source:PROVEntity {entity_id: $entity_id})
CALL apoc.path.expandConfig(source, {
    relationshipFilter: "wasDerivedFrom>|wasGeneratedBy>|used>",
    minLevel: 1,
    maxLevel: 20,
    uniqueness: "NODE_GLOBAL"
}) YIELD path
RETURN [node in nodes(path) | node.entity_id] as impact_path,
       [rel in relationships(path) | type(rel)] as relation_types
"""
```

---

## 5. API Interfaces

### 5.1 Agent Workflow Management API

```yaml
openapi: 3.0.0
info:
  title: Value Fabric Agent Workflow API
  version: 1.0.0
  description: API for managing agent workflows

paths:
  /api/v1/workflows:
    post:
      summary: Submit a new workflow
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                workflow_type:
                  type: string
                  enum: [whitespace_analysis, business_case_generation]
                tenant_id:
                  type: string
                user_id:
                  type: string
                inputs:
                  type: object
      responses:
        201:
          description: Workflow created
          content:
            application/json:
              schema:
                type: object
                properties:
                  workflow_instance_id:
                    type: string
                  status:
                    type: string
                  estimated_duration_seconds:
                    type: integer

  /api/v1/workflows/{instance_id}:
    get:
      summary: Get workflow status
      parameters:
        - name: instance_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Workflow status
          content:
            application/json:
              schema:
                type: object
                properties:
                  workflow_instance_id:
                    type: string
                  workflow_type:
                    type: string
                  status:
                    type: string
                  current_state:
                    type: string
                  progress_percentage:
                    type: number
                  started_at:
                    type: string
                    format: date-time
                  completed_at:
                    type: string
                    format: date-time
                  results:
                    type: object

    delete:
      summary: Cancel workflow
      parameters:
        - name: instance_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Workflow cancelled

  /api/v1/workflows/{instance_id}/events:
    get:
      summary: Get workflow events
      parameters:
        - name: instance_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Workflow events
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    event_id:
                      type: string
                    event_type:
                      type: string
                    timestamp:
                      type: string
                      format: date-time
                    message:
                      type: string
```

### 5.2 Business Case Generation API

```yaml
openapi: 3.0.0
info:
  title: Value Fabric Business Case API
  version: 1.0.0
  description: API for business case generation

paths:
  /api/v1/business-cases:
    post:
      summary: Generate a new business case
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                prospect_company:
                  type: string
                prospect_ticker:
                  type: string
                use_case_ids:
                  type: array
                  items:
                    type: string
                prospect_metrics:
                  type: object
                output_formats:
                  type: array
                  items:
                    type: string
                    enum: [executive_summary, slide_deck, risk_proposal]
      responses:
        201:
          description: Business case generation started
          content:
            application/json:
              schema:
                type: object
                properties:
                  business_case_id:
                    type: string
                  workflow_instance_id:
                    type: string
                  status:
                    type: string

  /api/v1/business-cases/{case_id}:
    get:
      summary: Get business case
      parameters:
        - name: case_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Business case
          content:
            application/json:
              schema:
                type: object
                properties:
                  business_case_id:
                    type: string
                  status:
                    type: string
                  executive_summary:
                    type: string
                  roi_calculation:
                    type: object
                  sensitivity_analysis:
                    type: object
                  outputs:
                    type: object
                    properties:
                      executive_summary:
                        type: string
                      slide_deck:
                        type: object
                      risk_proposal:
                        type: string

  /api/v1/business-cases/{case_id}/export:
    post:
      summary: Export business case
      parameters:
        - name: case_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                format:
                  type: string
                  enum: [pdf, pptx, docx, json]
      responses:
        200:
          description: Exported file
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
```

### 5.3 Audit Trail Query API

```yaml
openapi: 3.0.0
info:
  title: Value Fabric Audit Trail API
  version: 1.0.0
  description: API for querying audit trails

paths:
  /api/v1/audit/events:
    get:
      summary: Query audit events
      parameters:
        - name: tenant_id
          in: query
          required: true
          schema:
            type: string
        - name: workflow_id
          in: query
          schema:
            type: string
        - name: workflow_instance_id
          in: query
          schema:
            type: string
        - name: agent_id
          in: query
          schema:
            type: string
        - name: user_id
          in: query
          schema:
            type: string
        - name: event_type
          in: query
          schema:
            type: string
        - name: severity
          in: query
          schema:
            type: string
        - name: start_time
          in: query
          schema:
            type: string
            format: date-time
        - name: end_time
          in: query
          schema:
            type: string
            format: date-time
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
      responses:
        200:
          description: Audit events
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_count:
                    type: integer
                  events:
                    type: array
                    items:
                      type: object
                      properties:
                        event_id:
                          type: string
                        event_type:
                          type: string
                        timestamp:
                          type: string
                          format: date-time
                        workflow_id:
                          type: string
                        agent_id:
                          type: string
                        user_id:
                          type: string
                        severity:
                          type: string
                        message:
                          type: string

  /api/v1/audit/export:
    post:
      summary: Export audit trail
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                filters:
                  type: object
                format:
                  type: string
                  enum: [json, csv, prov-o]
      responses:
        200:
          description: Exported audit trail
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
```

### 5.4 Provenance Retrieval API

```yaml
openapi: 3.0.0
info:
  title: Value Fabric Provenance API
  version: 1.0.0
  description: API for retrieving provenance information

paths:
  /api/v1/provenance/entities/{entity_id}:
    get:
      summary: Get entity provenance
      parameters:
        - name: entity_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Entity provenance
          content:
            application/json:
              schema:
                type: object
                properties:
                  entity_id:
                    type: string
                  entity_type:
                    type: string
                  created_by_activity:
                    type: string
                  derived_from:
                    type: array
                    items:
                      type: string
                  attributed_to:
                    type: array
                    items:
                      type: string
                  generation_timestamp:
                    type: string
                    format: date-time

  /api/v1/provenance/lineage/{entity_id}:
    get:
      summary: Get entity lineage
      parameters:
        - name: entity_id
          in: path
          required: true
          schema:
            type: string
        - name: direction
          in: query
          schema:
            type: string
            enum: [backward, forward, both]
            default: backward
        - name: max_depth
          in: query
          schema:
            type: integer
            default: 10
      responses:
        200:
          description: Entity lineage
          content:
            application/json:
              schema:
                type: object
                properties:
                  entity_id:
                    type: string
                  lineage_graph:
                    type: object
                  paths:
                    type: array
                    items:
                      type: object

  /api/v1/provenance/traces/{output_id}:
    get:
      summary: Get decision trace
      parameters:
        - name: output_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Decision trace
          content:
            application/json:
              schema:
                type: object
                properties:
                  trace_id:
                    type: string
                  output_id:
                    type: string
                  steps:
                    type: array
                    items:
                      type: object
                      properties:
                        step_number:
                          type: integer
                        step_type:
                          type: string
                        description:
                          type: string
                        inputs:
                          type: array
                          items:
                            type: string
                        outputs:
                          type: array
                          items:
                            type: string
                        agent_id:
                          type: string
                        llm_model:
                          type: string
                        confidence:
                          type: number
                        timestamp:
                          type: string
                          format: date-time
```

### 5.5 Decision Trace Export API

```yaml
openapi: 3.0.0
info:
  title: Value Fabric Decision Trace API
  version: 1.0.0
  description: API for exporting decision traces

paths:
  /api/v1/decision-traces/{trace_id}:
    get:
      summary: Get decision trace
      parameters:
        - name: trace_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Decision trace
          content:
            application/json:
              schema:
                type: object
                properties:
                  trace_id:
                    type: string
                  workflow_id:
                    type: string
                  output_type:
                    type: string
                  created_at:
                    type: string
                    format: date-time
                  completed_at:
                    type: string
                    format: date-time
                  steps:
                    type: array
                    items:
                      type: object
                  verification_hash:
                    type: string

  /api/v1/decision-traces/{trace_id}/export:
    post:
      summary: Export decision trace
      parameters:
        - name: trace_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                format:
                  type: string
                  enum: [json, prov-o, pdf]
                include_evidence:
                  type: boolean
                  default: true
      responses:
        200:
          description: Exported decision trace
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary

  /api/v1/decision-traces/validate:
    post:
      summary: Validate decision trace
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                trace_id:
                  type: string
                verification_hash:
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
                  checks:
                    type: array
                    items:
                      type: object
                      properties:
                        check:
                          type: string
                        passed:
                          type: boolean
                        message:
                          type: string
```

---

## Appendix: Data Models Summary

### Core Entity Relationships

```
Document -(contains)-> Segment -(source_of)-> PainPoint
                                      |
                                      v
PainPoint -(projects_to)-> ValueTreeNode -(requires)-> Capability
                                                  |
                                                  v
Capability -(implements)-> UseCase -(generates)-> ValueDriver
                                           |
                                           v
ValueDriver -(calculated_by)-> Formula -(produces)-> ROI
                                                          |
                                                          v
ROI -(synthesized_into)-> Narrative -(compiled_into)-> AccountPlan/BusinessCase
```

### Provenance Chain

```
Every Entity -(wasGeneratedBy)-> Activity -(wasAssociatedWith)-> Agent
       |
       v
(wasDerivedFrom) -> Source Entity
       |
       v
(wasAttributedTo) -> Responsible Agent
```

---

*Document Version: 1.0*
*Generated: Backend Logic Specifications for Value Fabric SaaS Platform*
