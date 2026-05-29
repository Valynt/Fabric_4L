from __future__ import annotations

"""Variable Registry interface for Layer 4 Agents + Layer 5 Ground Truth.

Centralized variable definitions with source binding and provenance.
Internal service interface first; API where needed for external binding.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class VariableSourceType(str, Enum):
    """Source of variable value."""

    USER_INPUT = "user_input"
    CRM_FIELD = "crm_field"
    ERP_FIELD = "erp_field"
    BENCHMARK_LOOKUP = "benchmark_lookup"
    FORMULA_CALCULATION = "formula_calculation"
    DATABASE_QUERY = "database_query"
    API_CALL = "api_call"
    GROUND_TRUTH = "ground_truth"  # Layer 5 validated claim


class VariableDataType(str, Enum):
    """Variable data type."""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    ENUM = "enum"
    JSON = "json"


@dataclass
class VariableSourceBinding:
    """Source binding configuration for variable."""

    source_type: VariableSourceType
    source_location: str  # e.g., "Salesforce.Account.AnnualRevenue"
    extraction_query: str | None = None  # For DB/API sources
    transformation: str | None = None  # Simple transform expression
    fallback_value: Any | None = None
    is_required: bool = True


@dataclass
class VariableValidationRule:
    """Validation rule for variable value."""

    rule_type: str  # "range", "regex", "enum", "custom"
    parameters: dict[str, Any]  # Rule-specific params
    error_message: str


@dataclass
class Variable:
    """Variable definition in the registry."""

    variable_id: str
    name: str
    description: str
    data_type: VariableDataType

    # Source binding
    source_binding: VariableSourceBinding | None = None

    # Validation
    validation_rules: list[VariableValidationRule] = field(default_factory=list)

    # Context
    industry: str | None = None
    applicable_formulas: list[str] = field(default_factory=list)  # Formula IDs
    applicable_packs: list[str] = field(default_factory=list)  # Pack IDs

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    version: str = "1.0.0"
    is_active: bool = True


@dataclass
class VariableValue:
    """Resolved variable value with provenance."""

    variable_id: str
    value: Any
    data_type: VariableDataType
    source_type: VariableSourceType
    source_location: str | None

    # Provenance
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    validated_at: datetime | None = None
    ground_truth_id: str | None = None  # L5 TruthObject reference
    confidence: float = 1.0  # 0.0-1.0

    # Context
    workspace_id: str | None = None
    entity_id: str | None = None  # e.g., Account ID in CRM


@dataclass
class VariableSearchCriteria:
    """Search criteria for variable lookup."""

    industry: str | None = None
    pack_id: str | None = None
    formula_id: str | None = None
    data_type: VariableDataType | None = None
    source_type: VariableSourceType | None = None
    is_active: bool | None = True


@dataclass
class ResolutionContext:
    """Context for variable resolution."""

    workspace_id: str
    entity_id: str | None = None  # CRM entity context
    user_id: str | None = None
    pack_id: str | None = None
    industry: str | None = None


class IVariableRegistry(ABC):
    """Abstract interface for Variable Registry.

    Internal service interface for variable resolution.
    Schemas in KG, validated values as TruthObjects in L5.
    """

    @abstractmethod
    async def register_variable(self, variable: Variable) -> Variable:
        """Register new variable definition."""
        pass

    @abstractmethod
    async def get_variable(self, variable_id: str) -> Variable | None:
        """Retrieve variable definition."""
        pass

    @abstractmethod
    async def update_variable(
        self,
        variable_id: str,
        updates: dict[str, Any],
    ) -> Variable:
        """Update variable definition."""
        pass

    @abstractmethod
    async def search_variables(
        self,
        criteria: VariableSearchCriteria,
    ) -> list[Variable]:
        """Search variables by context."""
        pass

    @abstractmethod
    async def resolve_variable(
        self,
        variable_id: str,
        context: ResolutionContext,
    ) -> VariableValue:
        """Resolve variable value from source."""
        pass

    @abstractmethod
    async def resolve_variables_batch(
        self,
        variable_ids: list[str],
        context: ResolutionContext,
    ) -> dict[str, VariableValue]:
        """Resolve multiple variables efficiently."""
        pass

    @abstractmethod
    async def validate_value(
        self,
        variable_id: str,
        value: Any,
    ) -> tuple[bool, str | None]:
        """Validate value against variable rules."""
        pass


class IGroundTruthVariableBridge(ABC):
    """Bridge interface for Variable Registry ↔ Layer 5 Ground Truth.

    Links variable values to validated TruthObjects for audit trail.
    """

    @abstractmethod
    async def submit_for_validation(
        self,
        variable_value: VariableValue,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        """Submit variable value to Ground Truth for validation.

        Returns TruthObject ID for tracking.
        """
        pass

    @abstractmethod
    async def get_validated_value(
        self,
        variable_id: str,
        entity_id: str,
    ) -> VariableValue | None:
        """Retrieve latest validated value from Ground Truth."""
        pass

    @abstractmethod
    async def sync_variable_to_truth(
        self,
        variable: Variable,
    ) -> bool:
        """Sync variable definition to Ground Truth for claim type registration."""
        pass
