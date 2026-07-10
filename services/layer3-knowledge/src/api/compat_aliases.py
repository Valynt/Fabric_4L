"""Reusable helpers for legacy alias normalization and serialization.

These functions are intentionally model-agnostic so that GraphNode and GraphEdge
can share the same alias-handling logic while keeping their own Pydantic hooks,
computed fields, and OpenAPI schemas unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..services.compat_metrics import record_deprecated_field_usage
from ..services.compat_policy import include_legacy_graph_aliases


def normalize_legacy_aliases(
    data: Any,
    alias_map: Mapping[str, str],
    *,
    request_counter_name: str,
) -> Any:
    """Normalize legacy aliases into canonical fields for request payloads.

    Rules:
    - If the canonical field and alias are both present and differ, raise ValueError.
    - If the canonical field is absent but the alias is present, copy the alias value
      to the canonical field and record request-side deprecated field usage.
    """
    if not isinstance(data, dict):
        return data

    for alias, canonical in alias_map.items():
        if canonical in data and alias in data and data[canonical] != data[alias]:
            raise ValueError(
                f"Conflicting fields: '{canonical}' and deprecated '{alias}' must match"
            )
        if canonical not in data and alias in data:
            record_deprecated_field_usage(request_counter_name)
            data[canonical] = data[alias]

    return data


def serialize_with_aliases(
    data: dict[str, Any],
    alias_map: Mapping[str, str],
    api_version: str,
    *,
    response_counter_name: str,
) -> dict[str, Any]:
    """Conditionally keep or strip legacy alias fields from serialized output.

    If the deprecation policy still includes legacy aliases for the requested
    API version, record response-side usage and keep the alias keys. Otherwise
    remove the alias keys from the dumped dictionary.
    """
    if include_legacy_graph_aliases(api_version):
        for _ in alias_map:
            record_deprecated_field_usage(response_counter_name)
        return data

    for alias in alias_map:
        data.pop(alias, None)

    return data
