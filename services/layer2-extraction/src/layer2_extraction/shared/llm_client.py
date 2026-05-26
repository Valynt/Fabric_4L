"""Shared LLM client for Layer 2 extraction services."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
        job_id: str = "",
        tenant_id: str = "",
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
        self._job_id = job_id
        self._tenant_id = tenant_id

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
        """Send a completion request and return the text response with cost tracking."""
        client = self._get_client()
        if client is None:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        if self.provider == LLMProvider.OPENAI:
            resp = await client.chat.completions.create(
                model=kwargs.get("model", "gpt-4o"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.0),
            )
            
            # Track cost if enabled
            if self.cost_tracking_enabled:
                prompt_tokens = resp.usage.prompt_tokens if resp.usage else 0
                completion_tokens = resp.usage.completion_tokens if resp.usage else 0
                total_tokens = resp.usage.total_tokens if resp.usage else 0
                cost_usd = self._calculate_openai_cost(resp.model, prompt_tokens, completion_tokens)
                
                record = CostRecord(
                    job_id=self._job_id,
                    tenant_id=self._tenant_id,
                    model=resp.model,
                    provider="openai",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    call_type=kwargs.get("call_type", "extraction"),
                )
                self._cost_records.append(record)
            
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
            
            # Track cost if enabled
            if self.cost_tracking_enabled:
                prompt_tokens = resp.usage.input_tokens if resp.usage else 0
                completion_tokens = resp.usage.output_tokens if resp.usage else 0
                total_tokens = prompt_tokens + completion_tokens
                cost_usd = self._calculate_anthropic_cost(resp.model, prompt_tokens, completion_tokens)
                
                record = CostRecord(
                    job_id=self._job_id,
                    tenant_id=self._tenant_id,
                    model=resp.model,
                    provider="anthropic",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    call_type=kwargs.get("call_type", "extraction"),
                )
                self._cost_records.append(record)
            
            return resp.content[0].text if resp.content else ""
        raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _calculate_openai_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate OpenAI API cost in USD.
        
        Pricing as of 2024 (subject to change):
        - gpt-4o: $5/1M input, $15/1M output
        - gpt-4-turbo: $10/1M input, $30/1M output
        - gpt-3.5-turbo: $0.5/1M input, $1.5/1M output
        """
        model_lower = model.lower()
        
        if "gpt-4o" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 5.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
        elif "gpt-4-turbo" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 10.0
            output_cost = (completion_tokens / 1_000_000) * 30.0
        elif "gpt-3.5" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 0.5
            output_cost = (completion_tokens / 1_000_000) * 1.5
        else:
            # Default to gpt-4o pricing
            input_cost = (prompt_tokens / 1_000_000) * 5.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
        
        return input_cost + output_cost
    
    def _calculate_anthropic_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate Anthropic API cost in USD.
        
        Pricing as of 2024 (subject to change):
        - claude-3-opus: $15/1M input, $75/1M output
        - claude-3-sonnet: $3/1M input, $15/1M output
        - claude-3-haiku: $0.25/1M input, $1.25/1M output
        """
        model_lower = model.lower()
        
        if "opus" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 15.0
            output_cost = (completion_tokens / 1_000_000) * 75.0
        elif "sonnet" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 3.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
        elif "haiku" in model_lower:
            input_cost = (prompt_tokens / 1_000_000) * 0.25
            output_cost = (completion_tokens / 1_000_000) * 1.25
        else:
            # Default to sonnet pricing
            input_cost = (prompt_tokens / 1_000_000) * 3.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
        
        return input_cost + output_cost
    
    def get_cost_records(self) -> list[CostRecord]:
        """Return per-call cost records for this client."""
        return self._cost_records.copy()
    
    def get_total_cost(self) -> float:
        """Return cumulative cost in USD for this client."""
        return sum(record.cost_usd for record in self._cost_records)
    
    def get_total_tokens(self) -> int:
        """Return cumulative token count for this client."""
        return sum(record.total_tokens for record in self._cost_records)
    
    def clear_cost_records(self) -> None:
        """Clear accumulated cost records."""
        self._cost_records.clear()


@dataclass
class CostRecord:
    """Production-grade cost tracking record for LLM API calls.
    
    Tracks token usage and costs per extraction job for accurate billing
    and cost analysis.
    """
    
    job_id: str
    tenant_id: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    call_type: str = "extraction"  # extraction, validation, etc.
    
    @property
    def cost_per_1k_tokens(self) -> float:
        """Calculate cost per 1,000 tokens."""
        if self.total_tokens == 0:
            return 0.0
        return (self.cost_usd / self.total_tokens) * 1000
