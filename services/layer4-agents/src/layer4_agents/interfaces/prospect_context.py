from __future__ import annotations

"""Ports for prospect context aggregation."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ProspectContextSources:
    """Raw cross-layer data used to build the prospect context response."""

    profile_data: dict[str, Any] | None = None
    role_value: str | None = None
    truth_items: list[dict[str, Any]] = field(default_factory=list)


class ProspectContextPort(Protocol):
    """Cross-layer prospect context aggregation required by the prospects route."""

    async def load_context_sources(
        self,
        *,
        prospect_id: str,
        tenant_id: str,
    ) -> ProspectContextSources:
        """Load source data for prospect context assembly."""
