"""LLM-based entity extraction using OpenAI Structured Outputs.

Stage 2 and 3 of the extraction pipeline: Extract entities and relationships
using native structured LLM outputs with Pydantic model validation for
compile-time type safety and automatic schema enforcement.
"""

import math
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from layer2_extraction.shared.llm_output_parser import parse_llm_json

# Type variable for generic extraction
T = TypeVar("T", bound=BaseModel)

# System prompt used across all entity extraction operations
SYSTEM_PROMPT = "You are an enterprise ontology extractor. Be precise and conservative."

from layer2_extraction.models import (
    Capability,
    Feature,
    Persona,
    Relationship,
    UseCase,
    ValueDriver,
    ValueMetric,
)
from layer2_extraction.models.extraction_response import (
    CapabilityExtractionResponse,
    FeatureExtractionResponse,
    PersonaExtractionResponse,
    RelationshipExtractionResponse,
    UseCaseExtractionResponse,
    ValueDriverExtractionResponse,
    ValueMetricExtractionResponse,
)
from layer2_extraction.models.version_manifest import VersionManifest
from layer2_extraction.shared.llm_client import CostRecord, LLMClient

from .prompt_loader import render_entity_prompt, render_relationship_prompt


class LLMExtractionError(Exception):
    """Raised when LLM extraction fails or returns invalid data."""

    pass


def _logprob_confidence_from_response(response: Any) -> float | None:
    choices = getattr(response, "choices", None)
    if not choices:
        return None

    first_choice = choices[0]
    logprobs = getattr(first_choice, "logprobs", None)
    content = getattr(logprobs, "content", None) if logprobs else None
    if not content:
        return None

    values = [getattr(token, "logprob", None) for token in content]
    valid_logprobs = [v for v in values if v is not None]
    if not valid_logprobs:
        return None

    avg_logprob = sum(valid_logprobs) / len(valid_logprobs)
    return max(0.0, min(1.0, math.exp(avg_logprob)))


def _effective_confidence(item_confidence: float, logprob_confidence: float | None) -> float:
    item = max(0.0, min(1.0, item_confidence))
    if logprob_confidence is None:
        return item

    token_conf = max(0.0, min(1.0, logprob_confidence))
    return max(0.0, min(1.0, (0.7 * item) + (0.3 * token_conf)))


def _parse_tool_arguments(response: Any, method_name: str) -> dict[str, Any]:
    try:
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError("No tool calls returned")
        return parse_llm_json(
            tool_calls[0].function.arguments,
            call_site=f"llm_extractor.{method_name}",
        )
    except Exception as exc:
        raise LLMExtractionError(f"{method_name}: invalid function-call payload: {exc}") from exc


def _strict_array_tool(
    function_name: str,
    description: str,
    array_field_name: str,
    item_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": function_name,
                "description": description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        array_field_name: {
                            "type": "array",
                            "items": item_schema,
                        }
                    },
                    "required": [array_field_name],
                    "additionalProperties": False,
                },
            },
        }
    ]


class EntityExtractor:
    """Extract entities from text using OpenAI Function Calling.

    Uses temperature 0.0 for deterministic extraction with strict
    schema validation via Pydantic models.
    """

    # Schema definitions for OpenAI function calling
    CAPABILITY_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Capability name"},
            "description": {"type": "string", "description": "Detailed description"},
            "technical_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific technical features",
            },
            "api_endpoints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "API endpoints if applicable",
            },
            "integrations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Supported integrations",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence 0.0-1.0",
            },
        },
        "required": ["name", "description", "confidence"],
        "additionalProperties": False,
    }

    USECASE_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Use case name"},
            "description": {"type": "string", "description": "Detailed description"},
            "industry_context": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Applicable industries",
            },
            "workflow_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered workflow steps",
            },
            "kpis": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key performance indicators",
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["name", "description", "confidence"],
        "additionalProperties": False,
    }

    PERSONA_SCHEMA = {
        "type": "object",
        "properties": {
            "role_type": {
                "type": "string",
                "enum": ["economic_buyer", "champion", "operational_user", "technical_buyer", "stakeholder"],
                "description": "Role in buying process (buying-process function)",
            },
            "seniority_level": {
                "type": "string",
                "enum": ["executive_sponsor", "c_suite", "vp", "director", "manager", "individual_contributor", "unknown"],
                "description": "Organizational seniority level (default: unknown if not clear)",
            },
            "title": {"type": "string", "description": "Job title"},
            "department": {"type": "string", "description": "Department/organization"},
            "pain_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Problems this persona faces",
            },
            "success_metrics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "How they measure success",
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["role_type", "title", "department", "confidence"],
        "additionalProperties": False,
    }

    VALUEDRIVER_SCHEMA = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "capital_efficiency",
                    "cost_reduction",
                    "risk_mitigation",
                    "revenue_enhancement",
                    # Legacy values (mapped to new categories)
                    "revenue",
                    "cost",
                    "risk",
                    "capital",
                ],
                "description": "Type of value driver. Use granular categories (capital_efficiency, cost_reduction, risk_mitigation, revenue_enhancement) when clear.",
            },
            "name": {"type": "string", "description": "Value driver name"},
            "description": {"type": "string", "description": "Detailed description"},
            "metrics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific metrics",
            },
            "formula_string": {
                "type": "string",
                "description": "Mathematical formula for calculation (optional)",
            },
            "unit": {"type": "string", "description": "Unit of measurement"},
            "time_to_value": {"type": "string", "description": "Expected time to realize value"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["category", "name", "description", "unit", "confidence"],
        "additionalProperties": False,
    }

    FEATURE_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Feature name"},
            "description": {"type": "string", "description": "Detailed description"},
            "parent_capability_id": {
                "type": "string",
                "description": "UUID of parent capability (if mentioned)",
            },
            "technical_spec": {
                "type": "string",
                "description": "Technical specification details (optional)",
            },
            "implementation_status": {
                "type": "string",
                "enum": ["planned", "beta", "ga", "deprecated"],
                "description": "Current implementation status",
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["name", "description", "confidence"],
        "additionalProperties": False,
    }

    VALUEMETRIC_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Metric name (e.g. 'Days Sales Outstanding', 'Inventory Turns')",
            },
            "description": {
                "type": "string",
                "description": "Detailed description of what this metric measures and how it is calculated",
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (days, USD, %, FTEs, hours, etc.)",
            },
            "direction": {
                "type": "string",
                "enum": ["higher_is_better", "lower_is_better", "target_value"],
                "description": "Direction in which the metric improves: lower_is_better (e.g. DSO, churn rate), higher_is_better (e.g. NPS, throughput)",
            },
            "baseline_value": {
                "type": "number",
                "description": "Typical pre-solution baseline value (optional)",
            },
            "target_value": {
                "type": "number",
                "description": "Expected or stated post-solution value (optional)",
            },
            "benchmark_source": {
                "type": "string",
                "description": "Source of benchmark data (e.g. 'Gartner 2024', 'industry average') (optional)",
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["name", "description", "unit", "confidence"],
        "additionalProperties": False,
    }

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", timeout: float = 60.0):
        """Initialize extractor with OpenAI client.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (gpt-4o, gpt-4o-mini, etc.)
            timeout: Timeout for API calls in seconds (default: 60.0)
        """
        self.client = LLMClient(
            provider="openai",
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=3,
            cost_tracking_enabled=True,
        )
        self.model = self.client.model

    def get_cost_records(self) -> list[CostRecord]:
        """Return per-call cost records for this extractor."""
        return self.client.get_cost_records()

    def get_total_cost(self) -> float:
        """Return cumulative cost in USD for this extractor."""
        return self.client.get_total_cost()

    async def _extract_entities_generic(
        self,
        entity_type: str,
        text: str,
        source_url: str,
        extraction_job_id: str,
        confidence_threshold: float,
        response_model: type[BaseModel],
        entity_attr: str,
        endpoint: str,
        version_manifest: VersionManifest | None = None,
    ) -> list[T]:
        """Generic entity extraction with structured outputs.

        Args:
            entity_type: Type of entity being extracted (for prompt rendering)
            text: Text chunk to extract from
            source_url: Source URL for provenance
            extraction_job_id: Job ID for tracking
            confidence_threshold: Minimum confidence to include
            response_model: Pydantic model for response validation
            entity_attr: Attribute name on response containing entities list
            endpoint: API endpoint name for logging

        Returns:
            List of extracted entities meeting confidence threshold
        """
        prompt = render_entity_prompt(
            entity_type=entity_type,
            text=text,
            confidence_threshold=confidence_threshold,
        )

        try:
            response, _ = await self.client.chat_completion_structured(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                extraction_job_id=extraction_job_id,
                endpoint=endpoint,
                response_format=response_model,
                temperature=0.0,
            )

            entities: list[T] = []
            entities_list: list[T] = getattr(response, entity_attr, [])
            for entity in entities_list:
                if entity.confidence >= confidence_threshold:
                    entity.extraction_job_id = extraction_job_id
                    if hasattr(entity, "source_refs"):
                        entity.source_refs = [source_url]
                    if hasattr(entity, "version_manifest"):
                        entity.version_manifest = version_manifest
                    entities.append(entity)

            return entities

        except ValidationError as e:
            raise LLMExtractionError(
                f"Failed to extract {entity_type}s - schema validation error: {e}"
            ) from e
        except Exception as e:
            raise LLMExtractionError(f"Failed to extract {entity_type}s: {e}") from e

    async def extract_entities(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float = 0.8,
        version_manifest: VersionManifest | None = None,
    ) -> dict[str, list[BaseModel]]:
        """Extract all entity types from text.

        Args:
            text: Text chunk to extract from
            source_url: Source URL for provenance
            extraction_job_id: Job ID for tracking
            confidence_threshold: Minimum confidence to include

        Returns:
            Dict with keys: capabilities, use_cases, personas, value_drivers,
            value_metrics, features
        """
        results: dict[str, list[BaseModel]] = {
            "capabilities": [],
            "use_cases": [],
            "personas": [],
            "value_drivers": [],
            "value_metrics": [],
            "features": [],
        }

        # Extract each entity type
        results["capabilities"] = await self._extract_capabilities(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )
        results["use_cases"] = await self._extract_use_cases(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )
        results["personas"] = await self._extract_personas(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )
        results["value_drivers"] = await self._extract_value_drivers(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )
        results["value_metrics"] = await self._extract_value_metrics(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )
        results["features"] = await self._extract_features(
            text, source_url, extraction_job_id, confidence_threshold
            , version_manifest
        )

        return results

    async def _extract_capabilities(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[Capability]:
        """Extract capabilities from text using structured outputs."""
        return await self._extract_entities_generic(
            "capability", text, source_url, extraction_job_id, confidence_threshold,
            CapabilityExtractionResponse, "capabilities", "extract_capabilities", version_manifest
        )

    async def _extract_use_cases(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[UseCase]:
        """Extract use cases from text using structured outputs."""
        return await self._extract_entities_generic(
            "usecase", text, source_url, extraction_job_id, confidence_threshold,
            UseCaseExtractionResponse, "use_cases", "extract_use_cases", version_manifest
        )

    async def _extract_personas(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[Persona]:
        """Extract personas from text using structured outputs."""
        return await self._extract_entities_generic(
            "persona", text, source_url, extraction_job_id, confidence_threshold,
            PersonaExtractionResponse, "personas", "extract_personas", version_manifest
        )

    async def _extract_value_drivers(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[ValueDriver]:
        """Extract value drivers from text using structured outputs."""
        return await self._extract_entities_generic(
            "valuedriver", text, source_url, extraction_job_id, confidence_threshold,
            ValueDriverExtractionResponse, "value_drivers", "extract_value_drivers", version_manifest
        )

    async def _extract_features(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[Feature]:
        """Extract features from text using structured outputs."""
        return await self._extract_entities_generic(
            "feature", text, source_url, extraction_job_id, confidence_threshold,
            FeatureExtractionResponse, "features", "extract_features", version_manifest
        )

    async def _extract_value_metrics(
        self, text: str, source_url: str, extraction_job_id: str, confidence_threshold: float,
        version_manifest: VersionManifest | None = None,
    ) -> list[ValueMetric]:
        """Extract value metrics (KPIs) from text using structured outputs."""
        return await self._extract_entities_generic(
            "valuemetric", text, source_url, extraction_job_id, confidence_threshold,
            ValueMetricExtractionResponse, "value_metrics", "extract_value_metrics", version_manifest
        )


class RelationshipExtractor:
    """Extract relationships between entities using LLM."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", timeout: float = 60.0):
        self.client = LLMClient(
            provider="openai",
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=3,
            cost_tracking_enabled=True,
        )
        self.model = self.client.model

    def get_cost_records(self) -> list[CostRecord]:
        """Return per-call cost records for this extractor."""
        return self.client.get_cost_records()

    def get_total_cost(self) -> float:
        """Return cumulative cost in USD for this extractor."""
        return self.client.get_total_cost()

    async def extract_relationships(
        self,
        text: str,
        entities: dict[str, list[BaseModel]],
        source_url: str,
        extraction_job_id: str,
        confidence_threshold: float = 0.75,
        version_manifest: VersionManifest | None = None,
    ) -> list[Relationship]:
        """Extract relationships between identified entities using structured outputs.

        Uses OpenAI's structured output API with Pydantic model validation
        for type-safe relationship extraction.

        Args:
            text: Original text
            entities: Dict of entity lists from entity extraction
            source_url: Source URL
            extraction_job_id: Job ID
            confidence_threshold: Minimum confidence

        Returns:
            List of relationships with evidence
        """
        total_entities = sum(len(entity_items) for entity_items in entities.values())
        if total_entities < 2:
            return []

        prompt = render_relationship_prompt(text=text, entities=entities)

        try:
            response, _ = await self.client.chat_completion_structured(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enterprise ontology extractor. Be conservative - only extract relationships with explicit evidence.",
                    },
                    {"role": "user", "content": prompt},
                ],
                extraction_job_id=extraction_job_id,
                endpoint="extract_relationships",
                response_format=RelationshipExtractionResponse,
                temperature=0.0,
            )

            relationships = []
            for rel in response.relationships:
                if rel.confidence >= confidence_threshold:
                    # Add provenance metadata
                    rel.source_url = source_url
                    rel.extraction_job_id = extraction_job_id
                    rel.version_manifest = version_manifest
                    relationships.append(rel)

            return relationships

        except ValidationError as e:
            raise LLMExtractionError(f"Failed to extract relationships - schema validation error: {e}")
        except Exception as e:
            raise LLMExtractionError(f"Failed to extract relationships: {e}")
