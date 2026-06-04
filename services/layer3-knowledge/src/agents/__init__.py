"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Backend agents for Value Fabric knowledge graph operations.

This module implements the agent framework defined in the backend logic spec:
- ValueTreeProjectionAgent: Value tree traversal and projection
- WhitespaceAnalysisAgent: Gap identification and maturity assessment
- ROICalculationAgent: Formula execution and sensitivity analysis
- NarrativeSynthesisAgent: Template-based report generation
- ProvenanceTrackingAgent: PROV-O lineage tracking
"""

from .narrative_synthesis import NarrativeSynthesisAgent
from .provenance_tracking import ProvenanceTrackingAgent
from .roi_calculation import ROICalculationAgent
from .scenario_engine import (
    SavedScenario,
    ScenarioEngine,
    ScenarioResult,
    VariableAdjustment,
    scenario_engine,
)
from .value_tree_projection import ValueTreeProjectionAgent
from .whitespace_analysis import WhitespaceAnalysisAgent

__all__ = [
    "ValueTreeProjectionAgent",
    "WhitespaceAnalysisAgent",
    "ROICalculationAgent",
    "NarrativeSynthesisAgent",
    "ProvenanceTrackingAgent",
    "scenario_engine",
    "VariableAdjustment",
    "ScenarioResult",
    "SavedScenario",
    "ScenarioEngine",
]
