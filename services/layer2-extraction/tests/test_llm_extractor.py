import json
import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from layer2_extraction.extraction.llm_extractor import (
    EntityExtractor,
    LLMExtractionError,
    RelationshipExtractor,
    _effective_confidence,
    _logprob_confidence_from_response,
    _strict_array_tool,
)
from layer2_extraction.models.extraction_response import (
    CapabilityExtractionResponse,
    RelationshipExtractionResponse,
)
from layer2_extraction.models.ontology import Capability
from layer2_extraction.models.relationships import PredicateType, Relationship


def _response_with_logprobs(logprobs: list[float]):
    content = [SimpleNamespace(logprob=v) for v in logprobs]
    return SimpleNamespace(
        choices=[SimpleNamespace(logprobs=SimpleNamespace(content=content))]
    )


def _response_with_tool_args(payload: dict):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(arguments=json.dumps(payload))
                        )
                    ]
                )
            )
        ]
    )


def test_logprob_confidence_from_response_calculates_expected_value():
    response = _response_with_logprobs([-0.2, -0.4])
    expected = math.exp((-0.2 + -0.4) / 2)
    actual = _logprob_confidence_from_response(response)
    assert actual == pytest.approx(expected)


def test_logprob_confidence_from_response_returns_none_without_logprobs():
    response = SimpleNamespace(choices=[SimpleNamespace(logprobs=None)])
    assert _logprob_confidence_from_response(response) is None


def test_effective_confidence_blends_item_and_token_confidence():
    actual = _effective_confidence(0.8, 0.5)
    assert actual == pytest.approx((0.7 * 0.8) + (0.3 * 0.5))


def test_effective_confidence_clamps_out_of_range_values():
    assert _effective_confidence(2.0, None) == 1.0
    assert _effective_confidence(-1.0, 0.5) >= 0.0



def test_strict_array_tool_enforces_strict_schema_shape():
    tools = _strict_array_tool(
        function_name="extract_capabilities",
        description="Extract capabilities",
        array_field_name="capabilities",
        item_schema={"type": "object"},
    )

    function = tools[0]["function"]
    parameters = function["parameters"]
    assert function["strict"] is True
    assert parameters["required"] == ["capabilities"]
    assert parameters["additionalProperties"] is False


def test_entity_schema_constants_are_strict():
    assert EntityExtractor.USECASE_SCHEMA["additionalProperties"] is False
    assert EntityExtractor.FEATURE_SCHEMA["additionalProperties"] is False


# =============================================================================
# Structured Output Tests
# =============================================================================


@pytest.mark.asyncio
async def test_entity_extractor_uses_structured_output():
    """Verify EntityExtractor uses new structured output method."""
    extractor = EntityExtractor(api_key="test-key")

    # Mock the structured completion method
    mock_capability = Capability(
        name="Test Capability",
        description="A test capability for extraction",
        confidence=0.95,
    )
    mock_response = CapabilityExtractionResponse(capabilities=[mock_capability])

    with patch.object(
        extractor.client,
        "chat_completion_structured",
        return_value=(mock_response, None),
    ) as mock_structured:
        result = await extractor._extract_capabilities(
            "test text", "http://test.com", "job-123", 0.8
        )

        # Verify structured output method was called
        mock_structured.assert_called_once()
        call_kwargs = mock_structured.call_args.kwargs
        assert call_kwargs["response_format"] == CapabilityExtractionResponse
        assert call_kwargs["endpoint"] == "extract_capabilities"

        # Verify result
        assert len(result) == 1
        assert result[0].name == "Test Capability"
        assert result[0].confidence == 0.95
        assert result[0].extraction_job_id == "job-123"


@pytest.mark.asyncio
async def test_entity_extractor_filters_by_confidence_threshold():
    """Verify entities below confidence threshold are filtered."""
    extractor = EntityExtractor(api_key="test-key")

    # Create capabilities with varying confidence and source_refs
    high_conf = Capability(
        name="High Conf", description="High confidence capability", confidence=0.9, source_refs=["http://test.com"]
    )
    low_conf = Capability(
        name="Low Conf", description="Low confidence capability", confidence=0.5, source_refs=["http://test.com"]
    )
    mock_response = CapabilityExtractionResponse(capabilities=[high_conf, low_conf])

    with patch.object(
        extractor.client, "chat_completion_structured", return_value=(mock_response, None)
    ):
        result = await extractor._extract_capabilities(
            "test text", "http://test.com", "job-123", confidence_threshold=0.8
        )

        # Only high confidence should remain
        assert len(result) == 1
        assert result[0].name == "High Conf"


@pytest.mark.asyncio
async def test_entity_extractor_handles_validation_error():
    """Verify ValidationError is converted to LLMExtractionError."""
    extractor = EntityExtractor(api_key="test-key")

    with patch.object(
        extractor.client,
        "chat_completion_structured",
        side_effect=ValidationError.from_exception_data(
            "CapabilityExtractionResponse", [{"type": "missing", "loc": ("capabilities",), "msg": "Field required"}]
        ),
    ):
        with pytest.raises(LLMExtractionError) as exc_info:
            await extractor._extract_capabilities("test", "http://test.com", "job-123", 0.8)

        assert "schema validation error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_relationship_extractor_uses_structured_output():
    """Verify RelationshipExtractor uses structured output method."""
    from uuid import uuid4

    extractor = RelationshipExtractor(api_key="test-key")

    # Create mock relationship with valid UUIDs
    source_id = str(uuid4())
    target_id = str(uuid4())
    mock_rel = Relationship(
        source_id=source_id,
        target_id=target_id,
        raw_predicate="enables",
        canonical_predicate=PredicateType.ENABLES,
        evidence_text="Test evidence",
        confidence=0.9,
        source_url="http://test.com",
    )
    mock_response = RelationshipExtractionResponse(relationships=[mock_rel])

    with patch.object(
        extractor.client,
        "chat_completion_structured",
        return_value=(mock_response, None),
    ) as mock_structured:
        entities = {"capabilities": [SimpleNamespace(id=source_id), SimpleNamespace(id=target_id)]}
        result = await extractor.extract_relationships(
            "test text", entities, "http://test.com", "job-123", 0.8
        )

        # Verify structured output method was called
        mock_structured.assert_called_once()
        assert len(result) == 1
        assert result[0].source_id == source_id
        assert result[0].extraction_job_id == "job-123"


@pytest.mark.asyncio
async def test_relationship_extractor_returns_empty_for_single_entity():
    """Verify relationship extraction returns empty when < 2 entities."""
    extractor = RelationshipExtractor(api_key="test-key")

    entities = {"capabilities": [SimpleNamespace(id="entity-1")]}
    result = await extractor.extract_relationships(
        "test text", entities, "http://test.com", "job-123", 0.8
    )

    assert result == []


def test_extraction_response_model_strict_validation():
    """Verify extraction response models enforce strict validation."""
    # Verify extra=forbid is set
    assert CapabilityExtractionResponse.model_config.get("extra") == "forbid"

    # Test that extra fields are rejected
    with pytest.raises(ValidationError):
        CapabilityExtractionResponse(capabilities=[], unknown_field="test")
