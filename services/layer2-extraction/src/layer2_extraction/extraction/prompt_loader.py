"""Prompt rendering functions for L2 extraction LLM interactions.

This module provides:
1. Entity extraction prompt rendering with type-specific guidance
2. Relationship extraction prompt rendering with entity context
3. Prompt version tracking via the prompt registry
"""

from dataclasses import dataclass
from typing import Any

from layer2_extraction.extraction.prompt_registry import register_prompt_template

ENTITY_PROMPT_TEMPLATE_VERSION = "entity_extraction_v1"
RELATIONSHIP_PROMPT_TEMPLATE_VERSION = "relationship_extraction_v1"

@dataclass
class RenderedPrompt:
    """A rendered prompt with its version metadata."""
    
    content: str
    version_id: str
    template_name: str


def render_entity_prompt(entity_type: str, text: str, confidence_threshold: float) -> RenderedPrompt:
    """Render extraction prompt for a specific entity type with version tracking.

    Args:
        entity_type: Type of entity to extract (e.g., "capability", "persona", "usecase")
        text: Preprocessed source content with delimiters
        confidence_threshold: Minimum confidence threshold (0.0-1.0)

    Returns:
        RenderedPrompt with content and version metadata
    """
    template_name = f"entity_extraction_{entity_type}"
    template_content = f"""Extract {entity_type}s from the following source text.

Source Content:
{text}

Confidence Threshold: {confidence_threshold:.2f}

Extract only {entity_type}s that meet or exceed the confidence threshold.
Be precise and conservative - if information is ambiguous or missing, do not extract it.
"""
    
    version_id = register_prompt_template(
        template_name=template_name,
        template_content=template_content,
        description=f"Entity extraction prompt for {entity_type}",
        parameters={"entity_type": entity_type, "confidence_threshold": confidence_threshold},
    )
    
    return RenderedPrompt(
        content=template_content,
        version_id=version_id,
        template_name=template_name,
    )


def render_relationship_prompt(text: str, entities: dict[str, list[Any]]) -> RenderedPrompt:
    """Render relationship extraction prompt with entity context and version tracking.

    Args:
        text: Preprocessed source content with delimiters
        entities: Dictionary of entity lists by type (e.g., {"capabilities": [...], "personas": [...]})

    Returns:
        RenderedPrompt with content and version metadata
    """
    # Build entity context summary
    entity_context_parts = []
    for entity_type, entity_list in entities.items():
        if entity_list:
            entity_names = [getattr(e, "name", str(e)) for e in entity_list[:10]]  # Limit to first 10
            entity_context_parts.append(f"{entity_type}: {', '.join(entity_names)}")

    entity_context = "\n".join(entity_context_parts) if entity_context_parts else "No entities provided"

    template_name = "relationship_extraction"
    template_content = f"""Extract relationships between the following entities from the source text.

Entities:
{entity_context}

Source Content:
{text}

Extract only relationships with explicit evidence in the text.
Be conservative - do not infer relationships that are not clearly stated.
"""
    
    version_id = register_prompt_template(
        template_name=template_name,
        template_content=template_content,
        description="Relationship extraction prompt with entity context",
        parameters={"entity_types": list(entities.keys())},
    )
    
    return RenderedPrompt(
        content=template_content,
        version_id=version_id,
        template_name=template_name,
    )


__all__ = [
    "ENTITY_PROMPT_TEMPLATE_VERSION",
    "RELATIONSHIP_PROMPT_TEMPLATE_VERSION",
    "RenderedPrompt",
    "render_entity_prompt",
    "render_relationship_prompt",
]
