from types import SimpleNamespace

import pytest

from src.ingestion.neo4j.embeddings import EmbeddingGenerator


class _FakeModel:
    def __init__(self, raises=False):
        self.raises = raises

    def encode(self, text, normalize_embeddings=True):
        if self.raises:
            raise RuntimeError("model failure")
        result = type("Result", (), {"tolist": lambda self: [0.1, 0.2, 0.3]})
        return result()


def test_build_text_prefers_name_and_description():
    entity = {"id": "x", "name": "Name", "description": "Desc"}
    assert EmbeddingGenerator.build_text(entity) == "Name\nDesc"


def test_build_text_falls_back_to_id():
    entity = {"id": "fallback-id"}
    assert EmbeddingGenerator.build_text(entity) == "fallback-id"


def test_generate_returns_embedding_for_empty_text():
    gen = EmbeddingGenerator(settings=SimpleNamespace())
    gen._model = _FakeModel()
    assert gen.generate("") == [0.1, 0.2, 0.3]


def test_attach_skips_non_vector_types():
    gen = EmbeddingGenerator(settings=SimpleNamespace())
    assert gen.attach("Industry", [{"id": "i1"}]) == [{"id": "i1"}]


def test_attach_uses_existing_embedding():
    gen = EmbeddingGenerator(settings=SimpleNamespace())
    gen._model = _FakeModel()
    result = gen.attach("Capability", [{"id": "c1", "embedding": [0.9, 0.8]}])
    assert result[0]["embedding"] == [0.9, 0.8]


def test_attach_generates_embedding_for_vector_entity():
    gen = EmbeddingGenerator(settings=SimpleNamespace())
    gen._model = _FakeModel()
    result = gen.attach("Capability", [{"id": "c1", "name": "Name"}])
    assert result[0]["embedding"] == [0.1, 0.2, 0.3]
    assert result[0]["embedding_text"] == "Name"
