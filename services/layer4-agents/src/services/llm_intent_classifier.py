from __future__ import annotations

"""LLMIntentClassifier — OpenAI-based intent classification for ValuePilot.

Replaces brittle keyword matching with a lightweight structured LLM call.
Uses gpt-4o-mini for speed and cost efficiency.

Output schema:
  {"intent": "...", "confidence": 0.0-1.0, "entities": {"account_name": "...", ...}}

Intents:
  value_analysis, competitive_intel, document_export, workflow_status,
  account_inquiry, promote_signal, validate_hypothesis, generate_business_case,
  general_question
"""


import logging
import os
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .llm_output_parser import parse_llm_json

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.1
MAX_TOKENS = 256

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
    """Classify user intent using a lightweight OpenAI LLM call."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def classify(self, message: str) -> dict[str, Any]:
        """Classify a user message into intent, confidence, and entities."""
        if not self._api_key:
            logger.info("OPENAI_API_KEY not set — LLM intent classification unavailable")
            return self._fallback(message)

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"
            parsed = parse_llm_json(raw, call_site="llm_intent_classifier")

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

        except Exception as e:
            logger.warning("LLM intent classification failed: %s", e)
            return self._fallback(message)

    def _fallback(self, message: str) -> dict[str, Any]:
        """Return a safe default when LLM is unavailable."""
        return LLMIntentClassifierResult.model_validate({
            "intent": "general_question",
            "confidence": 0.5,
            "entities": {},
        })
