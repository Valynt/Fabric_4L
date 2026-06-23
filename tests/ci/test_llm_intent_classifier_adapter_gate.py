from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAYER4_SRC = ROOT / "services/layer4-agents/src"
CLASSIFIER_PATH = LAYER4_SRC / "layer4_agents/services/llm_intent_classifier.py"

if str(LAYER4_SRC) not in sys.path:
    sys.path.insert(0, str(LAYER4_SRC))


def test_llm_intent_classifier_does_not_import_provider_sdk_directly() -> None:
    source = CLASSIFIER_PATH.read_text(encoding="utf-8")

    assert "AsyncOpenAI" not in source
    assert "from openai" not in source
    assert "import openai" not in source


@pytest.mark.asyncio
async def test_llm_intent_classifier_uses_injected_completion_adapter() -> None:
    from layer4_agents.services.llm_adapter_interfaces import CompletionResult
    from layer4_agents.services.llm_intent_classifier import LLMIntentClassifier

    class FakeAdapter:
        def __init__(self) -> None:
            self.requests = []

        async def complete(self, request):
            self.requests.append(request)
            return CompletionResult(
                content='{"intent": "value_analysis", "confidence": 0.84, "entities": {"account_name": "Acme"}}'
            )

    adapter = FakeAdapter()
    result = await LLMIntentClassifier(adapter=adapter).classify("Run ROI for Acme")

    assert result.model_dump() == {
        "intent": "value_analysis",
        "confidence": 0.84,
        "entities": {"account_name": "Acme"},
    }
    assert adapter.requests
