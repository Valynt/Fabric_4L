from __future__ import annotations

"""Layer 4 core adapter interfaces for provider-agnostic LLM orchestration."""


from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class ErrorCategory(str, Enum):
    """Normalized error classes shared by all provider adapters."""

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    AUTH = "auth"
    INVALID_REQUEST = "invalid_request"
    PROVIDER = "provider"


@dataclass(frozen=True)
class RetryPolicy:
    """Retry and timeout behavior requested by orchestrators."""

    timeout_seconds: float
    max_attempts: int = 1


@dataclass(frozen=True)
class AdapterError:
    """Shared error envelope consumed by Layer 4 orchestration."""

    category: ErrorCategory
    message: str
    retryable: bool
    provider_code: str | None = None


class ProviderNotImplementedError(RuntimeError):
    """Raised when a configured LLM provider has no adapter implementation.

    Distinct from NotImplementedError (which signals an abstract method) and
    from AdapterError (which is a data envelope, not an exception). Callers
    that catch this can surface a clear configuration error rather than a
    generic 500.

    Usage::

        raise ProviderNotImplementedError("anthropic")
    """

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(
            f"LLM provider {provider_name!r} is not implemented. "
            "Set LAYER4_LLM_PROVIDER to 'openai' or 'together'."
        )


@dataclass(frozen=True)
class ToolCall:
    """Provider-agnostic tool-call record."""

    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class CompletionRequest:
    """Provider-agnostic completion request."""

    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.3
    max_tokens: int | None = None
    retry_policy: RetryPolicy | None = None


@dataclass(frozen=True)
class CompletionResult:
    """Provider-agnostic completion result."""

    content: str
    tool_calls: tuple[ToolCall, ...] = ()


class CompletionAdapter(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResult | AdapterError:
        """Return a completion result or normalized error envelope."""


class ToolCallingAdapter(Protocol):
    async def complete_with_tools(
        self,
        request: CompletionRequest,
        tools: list[dict[str, Any]],
    ) -> CompletionResult | AdapterError:
        """Return provider-agnostic tool-calling output or normalized error."""


class StructuredOutputAdapter(Protocol):
    async def extract_structured(
        self,
        request: CompletionRequest,
        *,
        schema: dict[str, Any],
    ) -> dict[str, Any] | AdapterError:
        """Return validated structured output or normalized error."""

