"""Unit tests for GovernedLLMClient stabilization and extracted helpers.

Validates:
1. Error classification normalization.
2. Prompt token estimation invariants and fallbacks.
3. Call cost calculation delegation.
4. Structured JSON message formatting.
5. GovernedLLMClient lifecycle, timeout classification, and budget error handling.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from layer4_agents.services.governed_llm_client import (
    classify_llm_error,
    estimate_prompt_tokens_from_messages,
    calculate_llm_call_cost,
    format_structured_llm_messages,
    GovernedLLMClient,
    _CostCapExceeded,
)


def test_classify_llm_error_matrix():
    """Verify error classification returns standardized category codes."""
    assert classify_llm_error(Exception("Connection timeout after 30s")) == "TIMEOUT"
    assert classify_llm_error(Exception("ReadTimeout occurred")) == "TIMEOUT"
    assert classify_llm_error(Exception("Rate limit reached for model")) == "RATE_LIMIT"
    assert classify_llm_error(Exception("Error 401: Invalid API Key")) == "AUTH"
    assert classify_llm_error(Exception("Unauthorized access to provider")) == "AUTH"
    assert classify_llm_error(Exception("Internal server error 500")) == "PROVIDER"
    assert classify_llm_error(Exception("Unknown connection reset")) == "PROVIDER"


def test_estimate_prompt_tokens_from_messages():
    """Verify prompt tokens are estimated accurately with safety bounds."""
    messages = [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "Hello world! This is a test prompt."},
    ]
    # Total chars = 23 + 35 = 58 chars -> 58 // 4 = 14 tokens
    est = estimate_prompt_tokens_from_messages(messages, fallback_tokens=100)
    assert est == 14

    # Empty content should return minimum 1
    assert estimate_prompt_tokens_from_messages([{"role": "user", "content": ""}], fallback_tokens=100) == 1

    # None messages should fall back to budget
    assert estimate_prompt_tokens_from_messages(None, fallback_tokens=500) == 500


def test_calculate_llm_call_cost():
    """Verify call cost calculation handles missing and active calculators."""
    assert calculate_llm_call_cost(None, "openai", "gpt-4o", 100, 50) == 0.0

    mock_calc = MagicMock()
    mock_calc.calculate_cost.return_value = 0.0025

    cost = calculate_llm_call_cost(mock_calc, "openai", "gpt-4o", 100, 50)
    assert cost == 0.0025
    mock_calc.calculate_cost.assert_called_once_with("openai", "gpt-4o", 100, 50)


def test_format_structured_llm_messages():
    """Verify schema hint is formatted and attached to the user message."""
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
    
    # When ending in user message:
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Generate summary"},
    ]
    formatted = format_structured_llm_messages(messages, schema)
    assert len(formatted) == 2
    assert formatted[0]["content"] == "System prompt"
    assert "Generate summary" in formatted[1]["content"]
    assert "Respond with valid JSON only" in formatted[1]["content"]
    assert '"summary"' in formatted[1]["content"]

    # When ending in assistant or system message:
    messages_no_user = [
        {"role": "system", "content": "System prompt"},
    ]
    formatted_no_user = format_structured_llm_messages(messages_no_user, schema)
    assert len(formatted_no_user) == 2
    assert formatted_no_user[1]["role"] == "user"
    assert "Respond with valid JSON only" in formatted_no_user[1]["content"]


@pytest.mark.asyncio
async def test_governed_llm_client_cost_budget_check():
    """Verify client rejects calls that exceed budget before invoking provider."""
    mock_run = MagicMock()
    mock_run.trace_id = "trace-1"
    mock_run.id = "run-1"
    mock_run.tenant_id = "tenant-test"
    mock_run.workflow_type = "test_flow"

    mock_provider = MagicMock()
    client = GovernedLLMClient(provider=mock_provider, provider_name="openai", run=mock_run)
    client._config = {"llm": {"provider": "openai", "models": {"openai": {"test_task": "gpt-4o"}}}}
    client._max_cost_per_call_usd = 0.05
    # Set a mock cost calculator and high estimated cost
    mock_calc = MagicMock()
    mock_calc.calculate_cost.return_value = 10.0  # High cost
    client._cost_calc = mock_calc

    with pytest.raises(_CostCapExceeded):
        await client.call(
            model_task="test_task",
            messages=[{"role": "user", "content": "Test prompt"}],
        )
