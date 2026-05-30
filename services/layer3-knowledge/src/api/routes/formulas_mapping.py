from __future__ import annotations

"""Pure formula mapping and serialization helpers."""

from typing import Any

VariableMetadata = Any

_VARIABLE_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Efficiency": [
        "automation",
        "efficiency",
        "error_rate",
        "error",
        "reduction",
        "improvement",
        "productivity",
    ],
    "Operational": [
        "volume",
        "transaction",
        "process",
        "manual",
        "hours",
        "time_period",
        "period",
        "cycle",
        "throughput",
    ],
    "Financial": [
        "cost",
        "revenue",
        "savings",
        "rate",
        "discount",
        "price",
        "budget",
        "investment",
        "roi",
        "npv",
        "payback",
        "benefit",
    ],
    "Quality": [
        "accuracy",
        "quality",
        "defect",
        "compliance",
        "satisfaction",
        "score",
        "rating",
    ],
}


def infer_variable_category(variable_name: str) -> str:
    """Infer a category for a variable from its name using keyword patterns."""
    lower = variable_name.lower()
    for category, keywords in _VARIABLE_CATEGORY_PATTERNS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "Financial"


def filter_variables_by_category(
    variables: list[VariableMetadata], category: str
) -> list[VariableMetadata]:
    """Return variables whose category matches *category* case-insensitively."""
    target = category.strip().lower()
    return [
        v
        for v in variables
        if (v.category or infer_variable_category(v.name)).lower() == target
    ]
