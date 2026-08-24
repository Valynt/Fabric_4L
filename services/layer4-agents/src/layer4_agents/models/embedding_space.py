"""Declarative specification for an embedding vector space."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingSpace(BaseModel):
    """Declarative specification for an embedding vector space.

    Enforces that vector dimensions, distance metrics, and underlying
    models/providers are explicitly declared and resolved rather than
    inferred from arbitrary model strings.
    """

    name: str = Field(..., description="Unique name/identifier of the embedding space")
    provider: str = Field(..., description="Approved LLM/Embedding provider (e.g., 'together', 'openai')")
    model: str = Field(..., description="Model identifier used for computing embeddings")
    dimension: int = Field(..., gt=0, description="Embedding vector dimensionality")
    distance_metric: Literal["cosine", "euclidean", "dot_product"] = Field(
        default="cosine",
        description="Distance/similarity metric for the vector space",
    )
    description: str | None = Field(default=None, description="Human-readable description")

    model_config = ConfigDict(frozen=True)


STANDARD_EMBEDDING_SPACES: dict[str, EmbeddingSpace] = {
    "together_m2_bert": EmbeddingSpace(
        name="together_m2_bert",
        provider="together",
        model="togethercomputer/m2-bert-80M-8k-retrieval",
        dimension=768,
        distance_metric="cosine",
        description="Together.ai M2-BERT 80M retrieval embedding (768d)",
    ),
    "openai_text_3_small": EmbeddingSpace(
        name="openai_text_3_small",
        provider="openai",
        model="text-embedding-3-small",
        dimension=1536,
        distance_metric="cosine",
        description="OpenAI text-embedding-3-small (1536d)",
    ),
    "openai_text_3_large": EmbeddingSpace(
        name="openai_text_3_large",
        provider="openai",
        model="text-embedding-3-large",
        dimension=3072,
        distance_metric="cosine",
        description="OpenAI text-embedding-3-large (3072d)",
    ),
}


def resolve_embedding_space(
    provider: str | None = None,
    space_name: str | None = None,
    fallback_provider: str = "together",
) -> EmbeddingSpace:
    """Resolve the appropriate EmbeddingSpace.

    If space_name is given and known, return that space.
    If provider is 'anthropic' (which does not provide native embeddings),
    binds to fallback_provider ('together' or 'openai') to prevent runtime failure.
    """
    if space_name and space_name in STANDARD_EMBEDDING_SPACES:
        return STANDARD_EMBEDDING_SPACES[space_name]

    active_provider = (
        provider
        or os.getenv("LAYER4_LLM_PROVIDER")
        or fallback_provider
    ).lower()

    if active_provider == "anthropic":
        # Anthropic has no native embedding API; bind to fallback provider
        active_provider = fallback_provider.lower()
        if active_provider == "anthropic":
            active_provider = "together"

    if active_provider == "openai":
        return STANDARD_EMBEDDING_SPACES["openai_text_3_small"]
    elif active_provider == "together":
        return STANDARD_EMBEDDING_SPACES["together_m2_bert"]
    else:
        # Default to together_m2_bert for safety
        return STANDARD_EMBEDDING_SPACES["together_m2_bert"]
