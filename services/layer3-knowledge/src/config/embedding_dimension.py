from __future__ import annotations

"""Embedding dimension policy and validation helpers for Layer 3."""


from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingDimensionMismatchError(ValueError):
    """Raised when configured and adapter embedding dimensions disagree."""

    configured_dimension: int
    adapter_dimension: int
    model_name: str

    def __str__(self) -> str:
        return (
            "Embedding dimension mismatch: "
            f"configured={self.configured_dimension}, "
            f"adapter={self.adapter_dimension}, model={self.model_name}"
        )


def infer_adapter_dimension(model: object) -> int | None:
    """Infer embedding dimension from a sentence-transformers model instance."""
    dim_getter = getattr(model, "get_sentence_embedding_dimension", None)
    if callable(dim_getter):
        try:
            value = dim_getter()
        except Exception:
            return None
        if isinstance(value, int) and value > 0:
            return value
    return None


def validate_embedding_dimension(configured_dimension: int, model: object, model_name: str) -> None:
    """Fail fast when configured dimension disagrees with active model dimension."""
    adapter_dimension = infer_adapter_dimension(model)
    if adapter_dimension is None:
        return
    if adapter_dimension != configured_dimension:
        raise EmbeddingDimensionMismatchError(
            configured_dimension=configured_dimension,
            adapter_dimension=adapter_dimension,
            model_name=model_name,
        )
