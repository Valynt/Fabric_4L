from __future__ import annotations

"""CostRecord model for LLM usage tracking.

Captures token consumption and calculated cost for a single inference call.
"""


from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CostRecord:
    """Immutable record of LLM inference cost.

    Fields:
        model: Model identifier, e.g. "gpt-4o"
        provider: Provider name, e.g. "openai"
        input_tokens: Number of prompt tokens consumed
        output_tokens: Number of completion tokens consumed
        cost_usd: Calculated cost in US dollars
        tenant_id: Tenant UUID string for cost attribution
        request_id: Optional correlation ID for tracing
        timestamp: UTC datetime when the record was created
        metadata: Additional context (e.g. workflow_type, tool_name)
    """

    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tenant_id: str
    request_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed."""
        return self.input_tokens + self.output_tokens

    def to_prometheus_labels(self) -> dict[str, str]:
        """Return labels suitable for Prometheus metrics."""
        return {
            "provider": self.provider,
            "model": self.model,
            "tenant_tier": self.tenant_id[:2] if self.tenant_id else "unknown",
        }
