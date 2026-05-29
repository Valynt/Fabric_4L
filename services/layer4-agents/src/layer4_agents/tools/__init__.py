from __future__ import annotations

"""Tools package for Layer 4 Agentic Workflow Engine.

This package contains 25+ tools organized into 8 categories:
- Knowledge (6): Graph query and semantic search tools
- Calculation (4): Formula evaluation and ROI calculation
- CRM (4): Salesforce/HubSpot integration
- Generation (4): Document and content generation
- Integration (4): Notifications and task management
- Utility (2): Validation and formatting
- Competitive (1): Competitive intelligence and alternative analysis
- Signals (5): Value Signal Layer (L2.5) retrieval and creation
"""


from .calculation_tools import (
    CalculateROITool,
    CompareBenchmarksTool,
    EvaluateFormulaTool,
    SensitivityAnalysisTool,
)
from .competitive_tools import AnalyzeCompetitionTool
from .crm_tools import (
    FetchInteractionHistoryTool,
    GetProspectDataTool,
    ScoreLeadTool,
    UpdateOpportunityTool,
)
from .document_export import DocumentExportTool, PDFGenerator
from .generation_tools import (
    AssembleDocumentTool,
    CreateChartTool,
    FormatTableTool,
    GenerateSectionTool,
)
from .integration_tools import (
    CreateTaskTool,
    ExportToCRMTool,
    ScheduleMeetingTool,
    SendNotificationTool,
)
from .knowledge_tools import (
    FindPathsTool,
    GetEntityTool,
    GetRelationshipsTool,
    QueryGraphTool,
    SemanticSearchTool,
    TraverseTreeTool,
)
from .registry import (
    BaseTool,
    TenantAwareTool,
    ToolError,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
    ToolValidationError,
    get_global_registry,
    tool,
)
from .signal_tools import (
    create_signal,
    get_account_signals,
    get_expansion_signals,
    get_renewal_risk_signals,
    get_signals_for_business_case,
)
from .utility_tools import FormatCurrencyTool, ValidateInputTool


def create_default_registry(config: dict | None = None) -> ToolRegistry:
    """Create a tool registry with all 25 tools pre-registered.

    Args:
        config: Optional configuration dictionary for tools

    Returns:
        ToolRegistry with all tools registered
    """
    registry = ToolRegistry()
    cfg = config or {}

    # Knowledge Tools (6)
    registry.register(QueryGraphTool(cfg))
    registry.register(SemanticSearchTool(cfg))
    registry.register(GetEntityTool(cfg))
    registry.register(GetRelationshipsTool(cfg))
    registry.register(TraverseTreeTool(cfg))
    registry.register(FindPathsTool(cfg))

    # Calculation Tools (4)
    registry.register(EvaluateFormulaTool(cfg))
    registry.register(CalculateROITool(cfg))
    registry.register(CompareBenchmarksTool(cfg))
    registry.register(SensitivityAnalysisTool(cfg))

    # CRM Tools (4)
    registry.register(GetProspectDataTool(cfg))
    registry.register(UpdateOpportunityTool(cfg))
    registry.register(FetchInteractionHistoryTool(cfg))
    registry.register(ScoreLeadTool(cfg))

    # Generation Tools (5)
    registry.register(GenerateSectionTool(cfg))
    registry.register(CreateChartTool(cfg))
    registry.register(FormatTableTool(cfg))
    registry.register(AssembleDocumentTool(cfg))
    registry.register(DocumentExportTool(cfg))

    # Integration Tools (4)
    registry.register(SendNotificationTool(cfg))
    registry.register(CreateTaskTool(cfg))
    registry.register(ScheduleMeetingTool(cfg))
    registry.register(ExportToCRMTool(cfg))

    # Utility Tools (2)
    registry.register(ValidateInputTool(cfg))
    registry.register(FormatCurrencyTool(cfg))

    # Competitive Intelligence Tools (1)
    registry.register(AnalyzeCompetitionTool(cfg))

    # Signal tools are async functions, not BaseTool subclasses —
    # they are called directly by workflow nodes, not via the registry.

    return registry


__all__ = [
    # Registry
    "BaseTool",
    "TenantAwareTool",
    "ToolError",
    "ToolNotFoundError",
    "ToolResult",
    "ToolValidationError",
    "ToolRegistry",
    "get_global_registry",
    "tool",
    "create_default_registry",
    # Knowledge
    "QueryGraphTool",
    "SemanticSearchTool",
    "GetEntityTool",
    "GetRelationshipsTool",
    "TraverseTreeTool",
    "FindPathsTool",
    # Calculation
    "EvaluateFormulaTool",
    "CalculateROITool",
    "CompareBenchmarksTool",
    "SensitivityAnalysisTool",
    # CRM
    "GetProspectDataTool",
    "UpdateOpportunityTool",
    "FetchInteractionHistoryTool",
    "ScoreLeadTool",
    # Generation
    "GenerateSectionTool",
    "CreateChartTool",
    "FormatTableTool",
    "AssembleDocumentTool",
    "DocumentExportTool",
    "PDFGenerator",
    # Integration
    "SendNotificationTool",
    "CreateTaskTool",
    "ScheduleMeetingTool",
    "ExportToCRMTool",
    # Utility
    "ValidateInputTool",
    "FormatCurrencyTool",
    # Competitive Intelligence
    "AnalyzeCompetitionTool",
    # Value Signal Layer (L2.5)
    "get_account_signals",
    "create_signal",
    "get_signals_for_business_case",
    "get_renewal_risk_signals",
    "get_expansion_signals",
]
