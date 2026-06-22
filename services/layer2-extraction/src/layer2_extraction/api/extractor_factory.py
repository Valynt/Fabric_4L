"""Extractor initialization helpers for the Layer 2 API."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

OPENAI_KEY_PLACEHOLDERS = frozenset(
    {
        "",
        "your-openai-api-key",
        "sk-placeholder",
        "sk-test",
        "replace-me",
        "your_openai_api_key",
        "openai_api_key",
        "none",
        "null",
    }
)


def validated_openai_key(
    *,
    is_strict_runtime: Callable[[], bool],
    logger: Any | None = None,
) -> str | None:
    """Return OPENAI_API_KEY, failing closed for missing or placeholder strict values."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.lower() in OPENAI_KEY_PLACEHOLDERS:
        if is_strict_runtime():
            raise RuntimeError(
                "OPENAI_API_KEY is missing or set to a placeholder value. "
                "A valid key is required in strict Layer 2 environments."
            )
        return None
    if not key.startswith("sk-"):
        if is_strict_runtime():
            raise RuntimeError(
                "OPENAI_API_KEY does not start with 'sk-' — likely a misconfigured placeholder. "
                "Refusing to start in strict environment."
            )
        if logger is not None:
            logger.warning("OPENAI_API_KEY does not start with 'sk-'; key may be invalid")
    return key


class LazyExtractorFactory:
    """Lazy cache for entity and relationship extractors."""

    def __init__(
        self,
        *,
        entity_extractor_cls: type,
        relationship_extractor_cls: type,
        key_provider: Callable[[], str | None],
        model_provider: Callable[[], str],
    ) -> None:
        self._entity_extractor_cls = entity_extractor_cls
        self._relationship_extractor_cls = relationship_extractor_cls
        self._key_provider = key_provider
        self._model_provider = model_provider
        self._entity_extractor: Any | None = None
        self._relationship_extractor: Any | None = None

    def get_entity_extractor(self) -> Any:
        if self._entity_extractor is None:
            self._entity_extractor = self._entity_extractor_cls(
                api_key=self._key_provider(),
                model=self._model_provider(),
            )
        return self._entity_extractor

    def get_relationship_extractor(self) -> Any:
        if self._relationship_extractor is None:
            self._relationship_extractor = self._relationship_extractor_cls(
                api_key=self._key_provider(),
                model=self._model_provider(),
            )
        return self._relationship_extractor

    def reset(self) -> None:
        self._entity_extractor = None
        self._relationship_extractor = None
