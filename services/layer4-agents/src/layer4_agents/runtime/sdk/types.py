"""SDK-facing lightweight types for the Agent Runtime client surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["AgentSpec"]


@dataclass(frozen=True)
class AgentSpec:
    """Static description of a runtime agent.

    ``tools`` is declarative intent — the named tools must already be
    registered on the runtime the agent is bound to.
    """

    name: str
    workflow_type: str
    description: str = ""
    tools: tuple[str, ...] = ()
    default_tenant_id: str | None = None
    default_priority: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
