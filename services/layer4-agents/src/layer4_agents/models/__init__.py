from __future__ import annotations

"""Models package for Layer 4 Agentic Workflow Engine."""


from .account import (
    Account,
    AccountSyncStatus,
    CRMProvider,
    EmbeddedContact,
    EmbeddedOpportunity,
    SyncStatus,
)
from .agent_state import (
    AgentState,
    BaseAgentState,
    BusinessCaseAgentState,
    BusinessCaseInputData,
    BusinessCaseSection,
    GapAnalysis,
    OrchestratorAgentState,
    ROIAgentState,
    ROIInputData,
    ROIResult,
    TenantMissingError,
    WhitespaceAgentState,
    WhitespaceInputData,
    WorkflowStatus,
    WorkflowType,
)
from .billing import (
    BillingCustomer,
    BillingSubscription,
    BillingWebhookEvent,
    PlanId,
    SubscriptionStatus,
)
from .business_case_record import BusinessCaseRecord
from .company_knowledge import (
    AuthorityWeight,
    CompanyKnowledgeProfile,
    CrawlStatus,
    ICPProfile,
    ICPSourceType,
    KnowledgeSource,
    PageType,
    ProfileStatus,
    ReviewStatus,
    SourceType,
    ValueExtractionRecord,
)
from .crm_sync_job import CRMSyncJob, CRMSyncJobStatus
from .embedding_space import (
    STANDARD_EMBEDDING_SPACES,
    EmbeddingSpace,
    resolve_embedding_space,
)
from .integration import (
    Integration,
    IntegrationStatus,
)
from .pain_signal import (
    ErrorCategory,
    EvidenceMatch,
    EvidenceType,
    ImpactUnit,
    PainSignal,
    PainSignalCreate,
    PainSignalUpdate,
    SignalCategory,
    TrendDirection,
)
from .reasoning_trace import ReasoningTrace, ToolCallTrace, validate_reasoning_trace
from .run_envelope import RunEnvelope
from .saved_scenario import SavedBusinessCaseScenario
from .tool_schemas import (
    AssembleDocumentInput,
    AssembleDocumentOutput,
    CalculateROIInput,
    CalculateROIOutput,
    CompareBenchmarksInput,
    CompareBenchmarksOutput,
    # Calculation tools
    EvaluateFormulaInput,
    EvaluateFormulaOutput,
    ExportDocumentInput,
    ExportDocumentOutput,
    # Generation tools
    GenerateSectionInput,
    GenerateSectionOutput,
    GetEntityInput,
    GetEntityOutput,
    # CRM tools
    GetProspectDataInput,
    GetProspectDataOutput,
    # Knowledge tools
    QueryGraphInput,
    QueryGraphOutput,
    SemanticSearchInput,
    SemanticSearchOutput,
    # Integration tools
    SendNotificationInput,
    SendNotificationOutput,
    ToolCategory,
    ToolSchema,
    UpdateOpportunityInput,
    UpdateOpportunityOutput,
    # Utility tools
    ValidateInputInput,
    ValidateInputOutput,
)
from .workflow_config import (
    BUSINESS_CASE_WORKFLOW_CONFIG,
    ROI_WORKFLOW_CONFIG,
    WHITESPACE_WORKFLOW_CONFIG,
    EdgeConfig,
    EdgeType,
    NodeConfig,
    NodeType,
    WorkflowConfig,
)
from .workspace_tab_data import WorkspaceTabData

__all__ = [
    # Account Models
    "Account",
    "AccountSyncStatus",
    "CRMProvider",
    "EmbeddedContact",
    "EmbeddedOpportunity",
    "SyncStatus",
    # Integration Models
    "Integration",
    "IntegrationStatus",
    "CRMSyncJob",
    "CRMSyncJobStatus",
    # Billing Models
    "BillingCustomer",
    "BillingSubscription",
    "BillingWebhookEvent",
    "PlanId",
    "SubscriptionStatus",
    "BusinessCaseRecord",
    "SavedBusinessCaseScenario",
    # Agent State
    "AgentState",
    "BaseAgentState",
    "TenantMissingError",
    "WorkflowStatus",
    "WorkflowType",
    "ROIAgentState",
    "ROIInputData",
    "ROIResult",
    "WhitespaceAgentState",
    "WhitespaceInputData",
    "GapAnalysis",
    "BusinessCaseAgentState",
    "BusinessCaseInputData",
    "BusinessCaseSection",
    "OrchestratorAgentState",
    # Reasoning Trace & Run Envelope
    "ReasoningTrace",
    "ToolCallTrace",
    "RunEnvelope",
    "validate_reasoning_trace",
    # Workflow Config
    "WorkflowConfig",
    "NodeConfig",
    "EdgeConfig",
    "NodeType",
    "EdgeType",
    "ROI_WORKFLOW_CONFIG",
    "WHITESPACE_WORKFLOW_CONFIG",
    "BUSINESS_CASE_WORKFLOW_CONFIG",
    # Tool Schemas
    "ToolCategory",
    "ToolSchema",
    "QueryGraphInput",
    "QueryGraphOutput",
    "SemanticSearchInput",
    "SemanticSearchOutput",
    "GetEntityInput",
    "GetEntityOutput",
    "EvaluateFormulaInput",
    "EvaluateFormulaOutput",
    "CalculateROIInput",
    "CalculateROIOutput",
    "CompareBenchmarksInput",
    "CompareBenchmarksOutput",
    "GetProspectDataInput",
    "GetProspectDataOutput",
    "UpdateOpportunityInput",
    "UpdateOpportunityOutput",
    "GenerateSectionInput",
    "GenerateSectionOutput",
    "AssembleDocumentInput",
    "AssembleDocumentOutput",
    "ExportDocumentInput",
    "ExportDocumentOutput",
    "SendNotificationInput",
    "SendNotificationOutput",
    "ValidateInputInput",
    "ValidateInputOutput",
    # Pain Signal Models
    "PainSignal",
    "PainSignalCreate",
    "PainSignalUpdate",
    "EvidenceMatch",
    "EvidenceType",
    "ImpactUnit",
    "SignalCategory",
    "TrendDirection",
    "ErrorCategory",
    # Company Knowledge Models
    "CompanyKnowledgeProfile",
    "KnowledgeSource",
    "ValueExtractionRecord",
    "ICPProfile",
    "ProfileStatus",
    "SourceType",
    "CrawlStatus",
    "AuthorityWeight",
    "PageType",
    "ReviewStatus",
    "ICPSourceType",
    "WorkspaceTabData",
    # Embedding Space Models
    "EmbeddingSpace",
    "STANDARD_EMBEDDING_SPACES",
    "resolve_embedding_space",
]
