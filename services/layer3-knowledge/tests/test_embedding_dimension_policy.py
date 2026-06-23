from types import SimpleNamespace

import pytest

from src.config.embedding_dimension import EmbeddingDimensionMismatchError, validate_embedding_dimension
from src.retrieval.vector_store import Neo4jVectorStore, VectorStoreError

pytestmark = pytest.mark.vector


class _FakeModel:
    def __init__(self, dim: int):
        self._dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim


def test_non_384_embedding_dimension_is_supported():
    validate_embedding_dimension(
        configured_dimension=1536,
        model=_FakeModel(1536),
        model_name="text-embedding-3-small",
    )


def test_mismatched_vector_length_rejected_with_stable_error_shape():
    store = Neo4jVectorStore(settings=SimpleNamespace(embedding_dimension=1536))
    with pytest.raises(VectorStoreError, match=r"VECTOR_DIMENSION_MISMATCH: expected=1536 actual=3"):
        store._validate_vector_length([0.1, 0.2, 0.3])


def test_adapter_config_mismatch_fails_deterministically():
    with pytest.raises(EmbeddingDimensionMismatchError, match="configured=1536, adapter=384"):
        validate_embedding_dimension(
            configured_dimension=1536,
            model=_FakeModel(384),
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
