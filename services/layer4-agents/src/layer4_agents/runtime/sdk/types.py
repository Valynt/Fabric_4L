"""SDK-facing lightweight types for the Agent Runtime client surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = ["AgentSpec"]


@dataclass(frozen=True)
class AgentSpec:
    """Static description of a runtime agent.

    ``tools`` is declarative intent — the named tools must already be
    registered on the runtime the agent is bound to.

    ``metadata`` is stored as a read-only mapping: the dict passed by
    the caller is copied at construction, so later caller-side
    mutations never leak into the spec and the ``frozen`` guarantee
    holds for this field too.
    """

    name: str
    workflow_type: str
    description: str = ""
    tools: tuple[str, ...] = ()
    default_tenant_id: str | None = None
    default_priority: int = 3
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "metadata", MappingProxyType(dict(self.metadata))
        )
