from __future__ import annotations

"""LLMIntentClassifier — OpenAI-based intent classification for ValuePilot.

Replaces brittle keyword matching with a lightweight structured LLM call.
Uses the GovernedLLMClient adapter infrastructure for provider-agnostic
completion, with fallback to direct AsyncOpenAI when no adapter is injected.

Output schema:
  {"intent": "...", "confidence": 0.0-1.0, "entities": {"account_name": "...", ...}}

Intents:
  value_analysis, competitive_intel, document_export, workflow_status,
  account_inquiry, promote_signal, validate_hypothesis, generate_business_case,
  general_question
"""


import logging
import os
from typing import TYPE_CHECKING, Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .llm_output_parser import parse_llm_json

if TYPE_CHECKING:
    from .governed_llm_client import GovernedLLMClient
    from .llm_adapter_interfaces import CompletionAdapter

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.1
MAX_TOKENS = 256
MODEL_TASK = "extraction"  # GovernedLLMClient model_task for intent classification

VALID_INTENTS = frozenset([
    "value_analysis",
    "competitive_intel",
    "document_export",
    "workflow_status",
    "account_inquiry",
    "promote_signal",
    "validate_hypothesis",
    "generate_business_case",
    "general_question",
])

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": list(VALID_INTENTS),
            "description": "Classified intent",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence score 0.0-1.0",
        },
        "entities": {
            "type": "object",
            "description": "Extracted entity mentions",
        },
    },
    "required": ["intent", "confidence", "entities"],
}

SYSTEM_PROMPT = """You are an intent classifier for ValuePilot, an AI co-pilot for B2B value selling.

Classify the user's message into exactly one intent from this list:
- value_analysis: ROI, payback, cost savings, value model, financial projections
- competitive_intel: competitors, battlecards, differentiation, versus
- document_export: export, PDF, slides, deck, proposal, document generation
- workflow_status: status, progress, running workflows, pipeline state
- account_inquiry: account details, company info, prospect research
- promote_signal: promote a pain signal to a hypothesis, create hypothesis from signal
- validate_hypothesis: validate, approve, reject a value hypothesis
- generate_business_case: create business case, value case, ROI case
- general_question: anything else, greetings, small talk, unclear requests

Return ONLY a JSON object with this exact schema (no markdown, no explanations):
{"intent": "...", "confidence": 0.0-1.0, "entities": {}}

The "entities" object should extract any mentioned IDs, names, or values.
Examples:
  {"intent": "promote_signal", "confidence": 0.92, "entities": {"signal_id": "sig-123"}}
  {"intent": "value_analysis", "confidence": 0.85, "entities": {}}
"""


class LLMIntentClassifierResult(TypedDictModel):
    intent: str
    confidence: float
    entities: dict[str, Any]


class LLMIntentClassifier:
    """Classify user intent using a lightweight LLM call via adapter infrastructure.

    Parameters
    ----------
    api_key:
        OpenAI API key (fallback when no adapter/client is injected).
    model:
        Model name for fallback direct-OpenAI mode.
    adapter:
        Optional ``CompletionAdapter`` for provider-agnostic completion.
        When provided, takes precedence over direct OpenAI calls.
    governed_client:
        Optional ``GovernedLLMClient`` for harness-aware structured calls.
        When provided, takes precedence over ``adapter``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        adapter: CompletionAdapter | None = None,
        governed_client: GovernedLLMClient | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._adapter = adapter
        self._governed_client = governed_client
        self._direct_client: Any | None = None

    def _get_direct_client(self) -> Any:
        """Lazy-load the direct OpenAI client (fallback mode only)."""
        if self._direct_client is None:
            from openai import AsyncOpenAI
            self._direct_client = AsyncOpenAI(api_key=self._api_key)
        return self._direct_client

    async def classify(self, message: str) -> dict[str, Any]:
        """Classify a user message into intent, confidence, and entities."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        try:
            if self._governed_client is not None:
                parsed, _meta = await self._governed_client.call_structured(
                    model_task=MODEL_TASK,
                    messages=messages,
                    schema=INTENT_SCHEMA,
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    call_id="intent_classifier",
                )
            elif self._adapter is not None:
                from .llm_adapter_interfaces import CompletionRequest, RetryPolicy
                result = await self._adapter.complete(
                    CompletionRequest(
                        model=self._model,
                        messages=messages,
                        temperature=DEFAULT_TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                        retry_policy=RetryPolicy(timeout_seconds=30, max_attempts=2),
                    ),
                )
                if hasattr(result, "content"):
                    raw = result.content
                else:
                    logger.warning("Adapter returned error-like result: %s", result)
                    return self._fallback(message)
                parsed = parse_llm_json(raw, call_site="llm_intent_classifier")
            else:
                parsed = await self._classify_via_direct_openai(messages)

            return self._validate_and_build(parsed)

        except Exception as e:
            logger.warning("LLM intent classification failed: %s", e)
            return self._fallback(message)

    async def _classify_via_direct_openai(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Fallback: direct OpenAI call when no adapter/client is injected."""
        if not self._api_key:
            logger.info("OPENAI_API_KEY not set — LLM intent classification unavailable")
            return {}

        client = self._get_direct_client()
        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return parse_llm_json(raw, call_site="llm_intent_classifier")

    def _validate_and_build(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate parsed intent classification result."""
        intent = str(parsed.get("intent", "general_question")).lower().strip()
        if intent not in VALID_INTENTS:
            intent = "general_question"

        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        entities = parsed.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        logger.info("LLM intent classified: %s (confidence=%.2f)", intent, confidence)
        return LLMIntentClassifierResult.model_validate({
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
        })

    def _fallback(self, message: str) -> dict[str, Any]:
        """Return a safe default when LLM is unavailable."""
        return LLMIntentClassifierResult.model_validate({
            "intent": "general_question",
            "confidence": 0.5,
            "entities": {},
        })
