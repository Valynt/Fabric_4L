from __future__ import annotations

"""Agent taxonomy and implementations for Layer 4.

Canonical 9-agent roster:
- ContextExtractionAgent — customer context, stakeholders, pain points
- ValueModelAgent — value trees, gap analysis, ROI calculations
- IntegrityAgent — claim validation, formula verification
- NarrativeAgent — executive summaries, proposals, slide decks
- CompetitiveIntelAgent — competitive landscape, win/loss analysis
- SignalDetectionAgent — operational signal monitoring
- CRMSyncAgent — CRM read/write (future)
- ConversationAgent — user-facing ValuePilot copilot
- OrchestrationController — workflow scheduling

Backward-compatible aliases for deprecated names are re-exported
from taxonomy.py.  See DEPRECATION_MAP.md for migration timeline.
"""


from .base import AgentCapability, AgentState, BaseAgent
from .signal_detection import SignalDetectionAgent
from .taxonomy import (
    # Canonical types
    AgentType,
    CompetitiveIntelAgent,
    ContextExtractionAgent,
    ConversationAgent,
    # Backward-compatible aliases (deprecated)
    DocumentIngestionAgent,
    FinancialExtractionAgent,
    IntegrityAgent,
    NarrativeAgent,
    NarrativeSynthesisAgent,
    OrchestrationController,
    ProvenanceTrackingAgent,
    ROICalculationAgent,
    ValueModelAgent,
    ValueTreeProjectionAgent,
    WhitespaceAnalysisAgent,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentState",
    "AgentCapability",
    # Taxonomy enum
    "AgentType",
    # Canonical agents
    "ContextExtractionAgent",
    "ValueModelAgent",
    "IntegrityAgent",
    "NarrativeAgent",
    "CompetitiveIntelAgent",
    "SignalDetectionAgent",
    "ConversationAgent",
    "OrchestrationController",
    # Deprecated aliases (backward compatibility)
    "DocumentIngestionAgent",
    "FinancialExtractionAgent",
    "ValueTreeProjectionAgent",
    "WhitespaceAnalysisAgent",
    "ROICalculationAgent",
    "NarrativeSynthesisAgent",
    "ProvenanceTrackingAgent",
]
