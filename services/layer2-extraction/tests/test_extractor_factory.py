from __future__ import annotations

import pytest

from layer2_extraction.api.extractor_factory import LazyExtractorFactory, validated_openai_key


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, message: str) -> None:
        self.messages.append(message)


class _Extractor:
    instances: list[_Extractor] = []

    def __init__(self, *, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.instances.append(self)


@pytest.mark.parametrize("value", ["", "sk-placeholder", "replace-me", "NONE"])
def test_validated_openai_key_rejects_missing_or_placeholder_in_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", value)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is missing or set to a placeholder"):
        validated_openai_key(is_strict_runtime=lambda: True)


def test_validated_openai_key_allows_missing_key_in_non_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert validated_openai_key(is_strict_runtime=lambda: False) is None


def test_validated_openai_key_rejects_non_openai_shape_in_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "not-an-openai-key")

    with pytest.raises(RuntimeError, match="does not start with 'sk-'"):
        validated_openai_key(is_strict_runtime=lambda: True)


def test_validated_openai_key_warns_for_non_openai_shape_in_non_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "not-an-openai-key")
    logger = _Logger()

    assert validated_openai_key(is_strict_runtime=lambda: False, logger=logger) == "not-an-openai-key"
    assert logger.messages == ["OPENAI_API_KEY does not start with 'sk-'; key may be invalid"]


def test_lazy_extractor_factory_caches_entity_and_relationship_extractors() -> None:
    _Extractor.instances = []
    factory = LazyExtractorFactory(
        entity_extractor_cls=_Extractor,
        relationship_extractor_cls=_Extractor,
        key_provider=lambda: "sk-real",
        model_provider=lambda: "model-a",
    )

    entity = factory.get_entity_extractor()
    relationship = factory.get_relationship_extractor()

    assert factory.get_entity_extractor() is entity
    assert factory.get_relationship_extractor() is relationship
    assert [instance.model for instance in _Extractor.instances] == ["model-a", "model-a"]


def test_lazy_extractor_factory_reset_recreates_extractors() -> None:
    _Extractor.instances = []
    factory = LazyExtractorFactory(
        entity_extractor_cls=_Extractor,
        relationship_extractor_cls=_Extractor,
        key_provider=lambda: "sk-real",
        model_provider=lambda: "model-a",
    )

    first = factory.get_entity_extractor()
    factory.reset()
    second = factory.get_entity_extractor()

    assert second is not first
