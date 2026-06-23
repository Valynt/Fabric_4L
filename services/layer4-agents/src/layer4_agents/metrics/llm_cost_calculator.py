from __future__ import annotations

"""LLM cost calculator with configurable pricing table."""
import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

COST_PER_1K_TOKENS: dict[tuple[str, str], dict[str, float]] = {
    # OpenAI
    ("openai", "gpt-4o"): {"prompt": 0.005, "completion": 0.015},
    ("openai", "gpt-4o-mini"): {"prompt": 0.00015, "completion": 0.0006},
    # Anthropic
    ("anthropic", "claude-3-opus"): {"prompt": 0.015, "completion": 0.075},
    ("anthropic", "claude-3-sonnet"): {"prompt": 0.003, "completion": 0.015},
    ("anthropic", "claude-3-haiku"): {"prompt": 0.00025, "completion": 0.00125},
    # Together.ai — prices as of 2025-05 (USD per 1K tokens)
    ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): {"prompt": 0.00088, "completion": 0.00088},
    ("together", "meta-llama/Llama-3.1-8B-Instruct-Turbo"): {"prompt": 0.00018, "completion": 0.00018},
    ("together", "meta-llama/Llama-3.1-405B-Instruct-Turbo"): {"prompt": 0.0035, "completion": 0.0035},
    ("together", "mistralai/Mixtral-8x7B-Instruct-v0.1"): {"prompt": 0.0006, "completion": 0.0006},
    ("together", "mistralai/Mistral-7B-Instruct-v0.3"): {"prompt": 0.0002, "completion": 0.0002},
    ("together", "Qwen/Qwen2.5-72B-Instruct-Turbo"): {"prompt": 0.0012, "completion": 0.0012},
    ("together", "deepseek-ai/DeepSeek-R1"): {"prompt": 0.003, "completion": 0.007},
}


class LLMCostCalculator:
    """Calculate LLM inference cost in USD based on token usage."""

    def __init__(self) -> None:
        self._pricing: dict[tuple[str, str], dict[str, float]] = dict(COST_PER_1K_TOKENS)
        self._load_override()

    def _load_override(self) -> None:
        """Load optional pricing override from LLM_COST_TABLE_PATH env var."""
        path = os.getenv("LLM_COST_TABLE_PATH")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for key, rates in data.items():
                parts = key.split("/", 1)
                if len(parts) != 2:
                    continue
                provider, model = parts
                if isinstance(rates, dict) and "prompt" in rates and "completion" in rates:
                    self._pricing[(provider, model)] = {
                        "prompt": float(rates["prompt"]),
                        "completion": float(rates["completion"]),
                    }
            logger.info("Loaded LLM cost table override from %s", path)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Failed to load LLM cost table override from %s: %s", path, exc)

    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate total cost in USD for a given LLM call.

        Returns 0.0 and logs a warning if the model is not in the pricing table.
        """
        key = (provider, model)
        rates = self._pricing.get(key)
        if rates is None:
            logger.warning("Unknown model for cost calculation: %s/%s", provider, model)
            return 0.0

        prompt_cost = (prompt_tokens / 1000.0) * rates["prompt"]
        completion_cost = (completion_tokens / 1000.0) * rates["completion"]
        return round(prompt_cost + completion_cost, 6)
