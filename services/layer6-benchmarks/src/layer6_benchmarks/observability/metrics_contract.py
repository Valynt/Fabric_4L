from __future__ import annotations

"""Layer 6 metrics contract loader.

The JSON contract under ``contracts/observability/layer6-metrics.json`` is the
single source of truth for metric names, labels, and cardinality limits.
"""


import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class MetricSpec:
    name: str
    metric_type: str
    required: bool
    description: str
    labels: tuple[str, ...]
    max_cardinality: dict[str, int]


CONTRACT_PATH = Path(__file__).resolve().parents[5] / "contracts" / "observability" / "layer6-metrics.json"


@lru_cache(maxsize=1)
def load_metric_specs() -> tuple[MetricSpec, ...]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return tuple(
        MetricSpec(
            name=metric["name"],
            metric_type=metric["type"],
            required=bool(metric.get("required", False)),
            description=metric["description"],
            labels=tuple(metric["labels"]),
            max_cardinality=dict(metric["max_cardinality"]),
        )
        for metric in payload["metrics"]
    )


def metric_spec_map() -> dict[str, MetricSpec]:
    return {spec.name: spec for spec in load_metric_specs()}


def metric_names() -> set[str]:
    return {spec.name for spec in load_metric_specs()}
