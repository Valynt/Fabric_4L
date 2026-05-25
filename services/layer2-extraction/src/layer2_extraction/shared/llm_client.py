"""Shared LLM client for Layer 2 extraction services."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic providers."""

    def __init__(
        self,
        provider: str | LLMProvider = LLMProvider.OPENAI,
        api_key: str | None = None,
        model: str = "gpt-4o",
        timeout: float = 60.0,
        max_retries: int = 3,
        cost_tracking_enabled: bool = False,
    ) -> None:
        if isinstance(provider, str):
            try:
                self.provider = LLMProvider(provider)
            except ValueError as exc:
                raise ValueError(f"'{provider}' is not a valid LLMProvider") from exc
        else:
            self.provider = provider

        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.cost_tracking_enabled = cost_tracking_enabled
        self._cost_records: list[CostRecord] = []

        if self.provider == LLMProvider.OPENAI:
            key = api_key or os.environ.get("OPENAI_API_KEY", "")
            if not key:
                raise ValueError("OpenAI API key required")
            self._api_key = key
            self._client: Any = None
        elif self.provider == LLMProvider.ANTHROPIC:
            key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                raise ValueError("Anthropic API key required")
            self._api_key = key
            self._client = None
        else:
            self._client = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self.provider == LLMProvider.OPENAI:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self._api_key)
        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                self._client = None
        return self._client

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send a completion request and return the text response."""
        client = self._get_client()
        if client is None:
            raise ValueError(f"Unsupported provider: {self.provider}")
        if self.provider == LLMProvider.OPENAI:
            resp = await client.chat.completions.create(
                model=kwargs.get("model", "gpt-4o"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.0),
            )
            return resp.choices[0].message.content or ""
        elif self.provider == LLMProvider.ANTHROPIC:
            if self._client is None:
                raise RuntimeError("Anthropic client not available")
            resp = await self._client.messages.create(
                model=kwargs.get("model", "claude-3-sonnet-20240229"),
                max_tokens=kwargs.get("max_tokens", 1024),
                messages=messages,
                temperature=kwargs.get("temperature", 0.0),
            )
            return resp.content[0].text if resp.content else ""
        raise ValueError(f"Unsupported provider: {self.provider}")


class CostRecord:
    """Placeholder cost tracking record for LLM API calls.

    Required for type hints in llm_extractor.py OpenAPI schema generation.
    Full cost accounting implementation is tracked in the Layer 2 backlog.
    """

    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, cost_usd: float = 0.0) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
