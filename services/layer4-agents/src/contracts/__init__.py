from __future__ import annotations

"""
Canonical Artifact Contracts — Phase 3 of the Ontology Contract Migration.

These Pydantic models define the typed boundaries between agents in the
Value Fabric pipeline. Every agent MUST accept and produce these artifacts.

Agent ownership:
  ContextArtifact    ← owned by ContextExtractionAgent
  ValueModelArtifact ← owned by ValueModelAgent
  IntegrityArtifact  ← owned by IntegrityAgent
  NarrativeArtifact  ← owned by NarrativeAgent

Import from here:
    from value_fabric.layer4.contracts import (
        EntityRef, ContextArtifact, ValueModelArtifact,
        IntegrityArtifact, NarrativeArtifact,
    )
"""


from .artifacts import (
    # Constants
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    Assumption,
    AssumptionAuditEntry,
    CapabilityValueChain,
    ConfidenceScore,
    # Artifact 1
    ContextArtifact,
    CustomerProfile,
    # Core schema
    EntityRef,
    EvidenceAssessment,
    ExecutiveSummary,
    ExtractionSource,
    FinancialModel,
    GateResult,
    # Artifact 3
    IntegrityArtifact,
    # Artifact 4
    NarrativeArtifact,
    PainPoint,
    ProvenanceRecord,
    RealizationMilestone,
    ScenarioAnalysis,
    Stakeholder,
    StakeholderVersion,
    ValueDriverEntry,
    # Artifact 2
    ValueModelArtifact,
    VariableRegistryEntry,
)

__all__ = [
    # Constants
    "CONFIDENCE_HIGH_THRESHOLD",
    "CONFIDENCE_MEDIUM_THRESHOLD",
    # Core schema
    "EntityRef",
    "ConfidenceScore",
    "ProvenanceRecord",
    "ContextArtifact",
    "CustomerProfile",
    "Stakeholder",
    "PainPoint",
    "ExtractionSource",
    "ValueModelArtifact",
    "CapabilityValueChain",
    "ValueDriverEntry",
    "FinancialModel",
    "ScenarioAnalysis",
    "Assumption",
    "VariableRegistryEntry",
    "IntegrityArtifact",
    "AssumptionAuditEntry",
    "EvidenceAssessment",
    "GateResult",
    "NarrativeArtifact",
    "ExecutiveSummary",
    "StakeholderVersion",
    "RealizationMilestone",
]
