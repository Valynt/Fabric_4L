from __future__ import annotations

"""Stable error types for embedding provider failures."""



class EmbeddingProviderUnavailableError(RuntimeError):
    """Raised when an embedding provider call fails or is unavailable."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        failure_cause: str,
        retry_after_seconds: int = 30,
        retry_hint: str = "retryable",
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.failure_cause = failure_cause
        self.retry_after_seconds = retry_after_seconds
        self.retry_hint = retry_hint

