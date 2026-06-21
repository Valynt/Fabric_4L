from __future__ import annotations

"""Service interfaces for Phase 2 Architecture Extensions.

Provides clean extension points for:
- Layer 6 Benchmark Service integration
- Value Pack Domain composition
- Formula Governance lifecycle
- Variable Registry resolution
"""


from .benchmark_client import (
    BenchmarkDataset,
    ComparisonRequest,
    ComparisonResult,
    IBenchmarkClient,
    RangeValidationRequest,
    RangeValidationResult,
)
from .context_clients import ContextFinancialExtractionPort, ContextIngestionPort
from .formula_governance import (
    ActivationRequest,
    DeprecationRequest,
    FormulaDependency,
    FormulaGovernance,
    FormulaStatus,
    FormulaVersion,
    GovernanceTransitionResult,
    IFormulaApprovalWorkflow,
    IFormulaGovernanceService,
)
from .signal_clients import SignalExtractionPort, SignalKnowledgePort
from .signal_review import SignalReviewPort
from .value_pack_service import (
    BenchmarkRef,
    FormulaRef,
    IValuePackService,
    PackExecutionRequest,
    PackExecutionResult,
    PackStatus,
    ValueDriverRef,
    ValuePack,
)
from .variable_registry import (
    IGroundTruthVariableBridge,
    IVariableRegistry,
    ResolutionContext,
    Variable,
    VariableDataType,
    VariableSearchCriteria,
    VariableSourceBinding,
    VariableSourceType,
    VariableValidationRule,
    VariableValue,
)

__all__ = [
    # Benchmark Client
    "IBenchmarkClient",
    "BenchmarkDataset",
    "ComparisonRequest",
    "ComparisonResult",
    "RangeValidationRequest",
    "RangeValidationResult",
    "ContextFinancialExtractionPort",
    "ContextIngestionPort",
    "SignalExtractionPort",
    "SignalKnowledgePort",
    "SignalReviewPort",
    # Value Pack Service
    "IValuePackService",
    "ValuePack",
    "ValueDriverRef",
    "FormulaRef",
    "BenchmarkRef",
    "PackExecutionRequest",
    "PackExecutionResult",
    "PackStatus",
    # Formula Governance
    "IFormulaGovernanceService",
    "IFormulaApprovalWorkflow",
    "FormulaGovernance",
    "FormulaVersion",
    "FormulaDependency",
    "FormulaStatus",
    "ActivationRequest",
    "DeprecationRequest",
    "GovernanceTransitionResult",
    # Variable Registry
    "IVariableRegistry",
    "IGroundTruthVariableBridge",
    "Variable",
    "VariableValue",
    "VariableSourceBinding",
    "VariableValidationRule",
    "VariableSearchCriteria",
    "ResolutionContext",
    "VariableSourceType",
    "VariableDataType",
]
