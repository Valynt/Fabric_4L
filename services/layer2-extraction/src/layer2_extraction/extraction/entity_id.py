"""Deterministic entity ID generation for Layer 2 extraction.

Provides stable, reproducible identifiers for extracted entities based on
tenant, source, and canonical entity signature. Identical inputs produce
identical IDs across idempotent re-runs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def _normalize_text(text: str | None) -> str:
    """Normalize text for stable signature generation."""
    if text is None:
        return ""
    # Lowercase, strip whitespace, collapse internal spaces
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _build_entity_signature(entity_type: str, entity: Any) -> str:
    """Build a canonical signature string from an entity's identity-defining fields.

    The signature includes only fields that define *what* the entity is,
    not extraction metadata (confidence, timestamps, IDs).
    """
    parts: list[str] = [entity_type]

    # Capability: name + description + technical_features
    if entity_type == "capability":
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))
        features = sorted(set(_normalize_text(f) for f in (getattr(entity, "technical_features", None) or [])))
        parts.extend(features)

    # UseCase: name + description + industry_context
    elif entity_type == "usecase":
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))
        industries = sorted(set(_normalize_text(i) for i in (getattr(entity, "industry_context", None) or [])))
        parts.extend(industries)

    # Persona: role_type + title + department
    elif entity_type == "persona":
        role = getattr(entity, "role_type", None)
        parts.append(str(role.value if hasattr(role, "value") else role))
        parts.append(_normalize_text(getattr(entity, "title", None)))
        parts.append(_normalize_text(getattr(entity, "department", None)))

    # ValueDriver: category + name + description + unit
    elif entity_type == "valuedriver":
        category = getattr(entity, "category", None)
        parts.append(str(category.value if hasattr(category, "value") else category))
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))
        parts.append(_normalize_text(getattr(entity, "unit", None)))

    # Feature: name + description
    elif entity_type == "feature":
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))

    # ValueMetric: name + description + unit + direction
    elif entity_type == "valuemetric":
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))
        parts.append(_normalize_text(getattr(entity, "unit", None)))
        direction = getattr(entity, "direction", None)
        parts.append(str(direction.value if hasattr(direction, "value") else direction))

    else:
        # Fallback: use name + description if available
        parts.append(_normalize_text(getattr(entity, "name", None)))
        parts.append(_normalize_text(getattr(entity, "description", None)))

    return "|".join(parts)


def compute_deterministic_id(
    tenant_id: str,
    source_hash: str,
    entity_type: str,
    entity: Any,
    extraction_version: str = "v1",
    *,
    source_url: str | None = None,
) -> str:
    """Compute a deterministic, stable ID for an extracted entity.

    Args:
        tenant_id: The tenant owning this entity.
        source_hash: Stable hash of source content/identifier.
        entity_type: Type of entity (capability, usecase, persona, etc.).
        entity: The entity object with identity-defining fields.
        extraction_version: Version of the extraction pipeline/config.

    Returns:
        A stable 64-character hex string derived from the inputs.
    """
    effective_source_hash = source_hash or _normalize_text(source_url)
    signature = _build_entity_signature(entity_type, entity)
    payload = f"{tenant_id}|{effective_source_hash}|{entity_type}|{signature}|{extraction_version}"
    return str(uuid5(NAMESPACE_URL, payload))


def compute_source_hash(source_value: str) -> str:
    """Compute a normalized SHA-256 hash for source identifier/content."""
    normalized = _normalize_text(source_value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
