from __future__ import annotations

"""LLM cost metrics facade.

Provides a clean interface to record CostRecord objects as Prometheus metrics.
Actual metric objects live in prometheus_metrics.py to avoid duplication.
"""


from ..models.cost_record import CostRecord
from .prometheus_metrics import get_metrics


def record_cost(record: CostRecord) -> None:
    """Emit a CostRecord to Prometheus metrics.

    Args:
        record: Populated CostRecord from an LLM call.
    """
    metrics = get_metrics()
    if metrics is None:
        return
    metrics.record_llm_cost(
        provider=record.provider,
        model=record.model,
        tenant_id=record.tenant_id,
        cost=record.cost_usd,
        prompt_tokens=record.input_tokens,
        completion_tokens=record.output_tokens,
        status=record.metadata.get("status", "success"),
    )
