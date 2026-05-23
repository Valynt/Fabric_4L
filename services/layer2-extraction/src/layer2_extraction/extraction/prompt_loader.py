"""Prompt rendering functions for L2 extraction LLM interactions.

This module provides:
1. Entity extraction prompt rendering with type-specific guidance
2. Relationship extraction prompt rendering with entity context
"""

from typing import Any


def render_entity_prompt(entity_type: str, text: str, confidence_threshold: float) -> str:
    """Render extraction prompt for a specific entity type.

    Args:
        entity_type: Type of entity to extract (e.g., "capability", "persona", "usecase")
        text: Preprocessed source content with delimiters
        confidence_threshold: Minimum confidence threshold (0.0-1.0)

    Returns:
        Formatted prompt string for LLM consumption
    """
    prompt = f"""Extract {entity_type}s from the following source text.

Source Content:
{text}

Confidence Threshold: {confidence_threshold:.2f}

Extract only {entity_type}s that meet or exceed the confidence threshold.
Be precise and conservative - if information is ambiguous or missing, do not extract it.
"""
    return prompt


def render_relationship_prompt(text: str, entities: dict[str, list[Any]]) -> str:
    """Render relationship extraction prompt with entity context.

    Args:
        text: Preprocessed source content with delimiters
        entities: Dictionary of entity lists by type (e.g., {"capabilities": [...], "personas": [...]})

    Returns:
        Formatted prompt string for LLM consumption
    """
    # Build entity context summary
    entity_context_parts = []
    for entity_type, entity_list in entities.items():
        if entity_list:
            entity_names = [getattr(e, "name", str(e)) for e in entity_list[:10]]  # Limit to first 10
            entity_context_parts.append(f"{entity_type}: {', '.join(entity_names)}")

    entity_context = "\n".join(entity_context_parts) if entity_context_parts else "No entities provided"

    prompt = f"""Extract relationships between the following entities from the source text.

Entities:
{entity_context}

Source Content:
{text}

Extract only relationships with explicit evidence in the text.
Be conservative - do not infer relationships that are not clearly stated.
"""
    return prompt
