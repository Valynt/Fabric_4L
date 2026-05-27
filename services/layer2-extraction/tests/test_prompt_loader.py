"""Tests for prompt_loader module."""

from types import SimpleNamespace

import pytest

from layer2_extraction.extraction.prompt_loader import (
    ENTITY_PROMPT_TEMPLATE_VERSION,
    RELATIONSHIP_PROMPT_TEMPLATE_VERSION,
    render_entity_prompt,
    render_relationship_prompt,
)


def test_render_entity_prompt_includes_entity_type():
    """Verify entity type is included in the prompt."""
    prompt = render_entity_prompt("capability", "test text", 0.8)
    assert "capability" in prompt.content.lower()


def test_render_entity_prompt_includes_source_text():
    """Verify source text is included in the prompt."""
    prompt = render_entity_prompt("capability", "test source content", 0.8)
    assert "test source content" in prompt.content


def test_render_entity_prompt_includes_confidence_threshold():
    """Verify confidence threshold is included in the prompt."""
    prompt = render_entity_prompt("capability", "test text", 0.85)
    assert "0.85" in prompt.content


def test_render_entity_prompt_formatting():
    """Verify prompt has expected structure."""
    prompt = render_entity_prompt("persona", "sample text", 0.9)
    assert "Extract personas" in prompt.content
    assert "Source Content:" in prompt.content
    assert "Confidence Threshold:" in prompt.content


def test_render_relationship_prompt_includes_entity_context():
    """Verify entity context is included in the prompt."""
    entities = {
        "capabilities": [SimpleNamespace(name="Analytics"), SimpleNamespace(name="Reporting")],
        "personas": [SimpleNamespace(name="Data Scientist")],
    }
    prompt = render_relationship_prompt("test text", entities)
    assert "capabilities:" in prompt.content.lower()
    assert "Analytics" in prompt.content
    assert "personas:" in prompt.content.lower()
    assert "Data Scientist" in prompt.content


def test_render_relationship_prompt_handles_empty_entities():
    """Verify prompt handles empty entity dictionary."""
    prompt = render_relationship_prompt("test text", {})
    assert "No entities provided" in prompt.content


def test_render_relationship_prompt_includes_source_text():
    """Verify source text is included in the prompt."""
    entities = {"capabilities": [SimpleNamespace(name="Test")]}
    prompt = render_relationship_prompt("sample content", entities)
    assert "sample content" in prompt.content


def test_render_relationship_prompt_limits_entity_display():
    """Verify only first 10 entities are displayed per type."""
    entities = {
        "capabilities": [SimpleNamespace(name=f"Cap{i}") for i in range(15)],
    }
    prompt = render_relationship_prompt("test text", entities)
    # Should have some entities but not all 15
    assert "Cap0" in prompt.content
    assert "Cap9" in prompt.content
    assert "Cap14" not in prompt.content


def test_render_relationship_prompt_formatting():
    """Verify prompt has expected structure."""
    entities = {"capabilities": [SimpleNamespace(name="Test")]}
    prompt = render_relationship_prompt("test text", entities)
    assert "Extract relationships" in prompt.content
    assert "Entities:" in prompt.content
    assert "Source Content:" in prompt.content


def test_prompt_template_version_constants_stable():
    assert ENTITY_PROMPT_TEMPLATE_VERSION == "entity_extraction_v1"
    assert RELATIONSHIP_PROMPT_TEMPLATE_VERSION == "relationship_extraction_v1"
