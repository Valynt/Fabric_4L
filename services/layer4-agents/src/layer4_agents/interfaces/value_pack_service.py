from __future__ import annotations

"""Value Pack service interface for Layer 4 Agents.

Internal service interface for Value Pack composition and lifecycle.
Tightly coupled domain seam — uses code-level interfaces.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PackStatus(str, Enum):
    """Value Pack lifecycle status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ValueDriverRef:
    """Reference to a Value Driver within a pack."""

    driver_id: str
    name: str
    category: str
    weight: float = 1.0  # For aggregation


@dataclass
class FormulaRef:
    """Reference to a Formula within a pack."""

    formula_id: str
    name: str
    version: str
    variables: list[str]  # Required variable names


@dataclass
class BenchmarkRef:
    """Reference to a Benchmark dataset within a pack."""

    dataset_id: str
    metric: str
    industry: str


@dataclass
class ValuePack:
    """Value Pack domain model.

    Combines ontology slice, value drivers, formulas, benchmarks,
    and workflow templates for a specific industry/segment.
    """

    pack_id: str
    name: str
    description: str
    industry: str
    segment: str | None
    status: PackStatus
    version: str

    # Composition
    value_drivers: list[ValueDriverRef] = field(default_factory=list)
    formulas: list[FormulaRef] = field(default_factory=list)
    benchmarks: list[BenchmarkRef] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    created_by: str | None = None

    # Runtime
    is_loaded: bool = False
    workspace_id: str | None = None


@dataclass
class PackExecutionRequest:
    """Request to execute a Value Pack workflow."""

    pack_id: str
    workspace_id: str
    variables: dict[str, Any]  # Variable bindings
    user_id: str | None = None


@dataclass
class PackExecutionResult:
    """Result of Value Pack execution."""

    execution_id: str
    pack_id: str
    status: str  # success, partial, failed
    outputs: dict[str, Any]  # Formula results, benchmarks, etc.
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class IValuePackService(ABC):
    """Abstract interface for Value Pack service.

    Internal service interface for pack composition and execution.
    Implementation is in-process (not HTTP) due to tight coupling
    with formula evaluation and workflow orchestration.
    """

    @abstractmethod
    async def list_packs(
        self,
        tenant_id: str,
        industry: str | None = None,
        status: PackStatus | None = None,
    ) -> list[ValuePack]:
        """List available Value Packs."""
        pass

    @abstractmethod
    async def get_pack(self, pack_id: str, tenant_id: str) -> ValuePack | None:
        """Retrieve Value Pack by ID."""
        pass

    @abstractmethod
    async def load_pack_into_workspace(
        self,
        pack_id: str,
        workspace_id: str,
        tenant_id: str,
    ) -> ValuePack:
        """Load pack into workspace for customization/execution."""
        pass

    @abstractmethod
    async def execute_pack(
        self,
        request: PackExecutionRequest,
        tenant_id: str,
    ) -> PackExecutionResult:
        """Execute pack workflow with provided variables."""
        pass

    @abstractmethod
    async def customize_pack(
        self,
        pack_id: str,
        workspace_id: str,
        tenant_id: str,
        modifications: dict[str, Any],
    ) -> ValuePack:
        """Fork and customize pack for account-specific needs."""
        pass

    @abstractmethod
    async def save_pack(
        self,
        pack: ValuePack,
        tenant_id: str,
    ) -> ValuePack:
        """Save pack (create new version or update draft)."""
        pass
