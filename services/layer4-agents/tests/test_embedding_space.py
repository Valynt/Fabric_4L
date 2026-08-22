from __future__ import annotations

import pytest

from layer4_agents.models.embedding_space import (
    STANDARD_EMBEDDING_SPACES,
    EmbeddingSpace,
    resolve_embedding_space,
)
from layer4_agents.tools.knowledge_tools import SemanticSearchTool


def test_standard_embedding_spaces_declared() -> None:
    assert "together_m2_bert" in STANDARD_EMBEDDING_SPACES
    assert "openai_text_3_small" in STANDARD_EMBEDDING_SPACES
    assert "openai_text_3_large" in STANDARD_EMBEDDING_SPACES

    together = STANDARD_EMBEDDING_SPACES["together_m2_bert"]
    assert together.dimension == 768
    assert together.provider == "together"
    assert together.distance_metric == "cosine"

    openai = STANDARD_EMBEDDING_SPACES["openai_text_3_small"]
    assert openai.dimension == 1536
    assert openai.provider == "openai"


def test_resolve_embedding_space_by_name() -> None:
    space = resolve_embedding_space(space_name="openai_text_3_large")
    assert space.name == "openai_text_3_large"
    assert space.dimension == 3072


def test_resolve_embedding_space_by_provider() -> None:
    together_space = resolve_embedding_space(provider="together")
    assert together_space.provider == "together"
    assert together_space.model == "togethercomputer/m2-bert-80M-8k-retrieval"

    openai_space = resolve_embedding_space(provider="openai")
    assert openai_space.provider == "openai"
    assert openai_space.model == "text-embedding-3-small"


def test_resolve_embedding_space_anthropic_fallback() -> None:
    # Anthropic has no native embeddings; it must safely resolve to an approved fallback provider
    fallback_space = resolve_embedding_space(provider="anthropic", fallback_provider="together")
    assert fallback_space.provider == "together"
    assert fallback_space.dimension == 768

    openai_fallback = resolve_embedding_space(provider="anthropic", fallback_provider="openai")
    assert openai_fallback.provider == "openai"
    assert openai_fallback.dimension == 1536


def test_semantic_search_tool_resolves_embedding_space() -> None:
    tool_together = SemanticSearchTool({"llm_provider": "together"})
    assert tool_together.embedding_space.provider == "together"
    assert tool_together.embedding_model == "togethercomputer/m2-bert-80M-8k-retrieval"

    tool_anthropic = SemanticSearchTool({"llm_provider": "anthropic"})
    # Must fallback to approved together embedding
    assert tool_anthropic.embedding_space.provider == "together"
    assert tool_anthropic.embedding_model == "togethercomputer/m2-bert-80M-8k-retrieval"

    tool_explicit = SemanticSearchTool({"embedding_space": "openai_text_3_large"})
    assert tool_explicit.embedding_space.name == "openai_text_3_large"
    assert tool_explicit.embedding_model == "text-embedding-3-large"
