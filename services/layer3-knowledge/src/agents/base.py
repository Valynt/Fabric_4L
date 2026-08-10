"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Base agent class for Value Fabric agent framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AgentResult:
    """Result from agent execution."""

    agent_id: str
    agent_type: str
    status: str  # success, partial, failed
    output: dict[str, Any]
    execution_time_ms: int
    timestamp: datetime
    provenance: dict[str, Any]
    errors: list[str]


class BaseAgent(ABC):
    """Base class for all Value Fabric agents."""

    def __init__(self, agent_type: str):
        """Initialize base agent.

        Args:
            agent_type: Type identifier for the agent
        """
        self.agent_id = f"{agent_type}-{uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.created_at = datetime.utcnow()

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute agent logic.

        Args:
            context: Execution context with inputs

        Returns:
            AgentResult with output and metadata
        """
        pass

    def _create_result(
        self,
        status: str,
        output: dict[str, Any],
        execution_time_ms: int,
        errors: list[str] | None = None,
    ) -> AgentResult:
        """Create standardized result object.

        Args:
            status: Execution status
            output: Result output data
            execution_time_ms: Execution duration
            errors: Optional error messages

        Returns:
            AgentResult instance
        """
        return AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=status,
            output=output,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow(),
            provenance={
                "agent_type": self.agent_type,
                "agent_id": self.agent_id,
                "created_at": self.created_at.isoformat(),
                "executed_at": datetime.utcnow().isoformat(),
            },
            errors=errors or [],
        )
