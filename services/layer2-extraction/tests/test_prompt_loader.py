"""Tests for prompt_loader module."""

from types import SimpleNamespace

import pytest

from layer2_extraction.extraction.prompt_loader import (
    render_entity_prompt,
    render_relationship_prompt,
)


def test_render_entity_prompt_includes_entity_type():
    """Verify entity type is included in the prompt."""
    prompt = render_entity_prompt("capability", "test text", 0.8)
    assert "capability" in prompt.lower()


def test_render_entity_prompt_includes_source_text():
    """Verify source text is included in the prompt."""
    prompt = render_entity_prompt("capability", "test source content", 0.8)
    assert "test source content" in prompt


def test_render_entity_prompt_includes_confidence_threshold():
    """Verify confidence threshold is included in the prompt."""
    prompt = render_entity_prompt("capability", "test text", 0.85)
    assert "0.85" in prompt


def test_render_entity_prompt_formatting():
    """Verify prompt has expected structure."""
    prompt = render_entity_prompt("persona", "sample text", 0.9)
    assert "Extract personas" in prompt
    assert "Source Content:" in prompt
    assert "Confidence Threshold:" in prompt


def test_render_relationship_prompt_includes_entity_context():
    """Verify entity context is included in the prompt."""
    entities = {
        "capabilities": [SimpleNamespace(name="Analytics"), SimpleNamespace(name="Reporting")],
        "personas": [SimpleNamespace(name="Data Scientist")],
    }
    prompt = render_relationship_prompt("test text", entities)
    assert "capabilities:" in prompt.lower()
    assert "Analytics" in prompt
    assert "personas:" in prompt.lower()
    assert "Data Scientist" in prompt


def test_render_relationship_prompt_handles_empty_entities():
    """Verify prompt handles empty entity dictionary."""
    prompt = render_relationship_prompt("test text", {})
    assert "No entities provided" in prompt


def test_render_relationship_prompt_includes_source_text():
    """Verify source text is included in the prompt."""
    entities = {"capabilities": [SimpleNamespace(name="Test")]}
    prompt = render_relationship_prompt("sample content", entities)
    assert "sample content" in prompt


def test_render_relationship_prompt_limits_entity_display():
    """Verify only first 10 entities are displayed per type."""
    entities = {
        "capabilities": [SimpleNamespace(name=f"Cap{i}") for i in range(15)],
    }
    prompt = render_relationship_prompt("test text", entities)
    # Should have some entities but not all 15
    assert "Cap0" in prompt
    assert "Cap9" in prompt
    assert "Cap14" not in prompt


def test_render_relationship_prompt_formatting():
    """Verify prompt has expected structure."""
    entities = {"capabilities": [SimpleNamespace(name="Test")]}
    prompt = render_relationship_prompt("test text", entities)
    assert "Extract relationships" in prompt
    assert "Entities:" in prompt
    assert "Source Content:" in prompt
