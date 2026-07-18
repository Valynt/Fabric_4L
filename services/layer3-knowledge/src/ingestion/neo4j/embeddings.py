from __future__ import annotations

import logging
from typing import Any

from ...config import Settings, get_settings
from ...services.embedding_errors import EmbeddingProviderUnavailableError
from .constants import VECTOR_ENTITY_TYPES
from .protocols import EmbeddingModel

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Lazy-loads the embedding model and generates vectors for entities."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._model: EmbeddingModel | None = None

    def _get_model(self) -> EmbeddingModel:
        """Lazily load sentence-transformers model for ingestion embeddings."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = getattr(
                    self.settings,
                    "embedding_model",
                    "sentence-transformers/all-MiniLM-L6-v2",
                )
                self._model = SentenceTransformer(model_name)
                logger.info("Loaded ingestion embedding model: %s", model_name)
            except Exception:
                logger.warning(
                    "sentence-transformers not available, embeddings disabled"
                )
                self._model = None

        if self._model is None:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider unavailable",
                provider="sentence-transformers",
                failure_cause="model_unavailable",
                retry_after_seconds=30,
                retry_hint="install_or_restore_provider",
            )

        return self._model

    @staticmethod
    def build_text(entity: dict[str, Any]) -> str:
        """Build deterministic embedding text from core entity fields."""
        text_parts = []
        for key in ("name", "description", "summary", "title"):
            value = entity.get(key)
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())
        if not text_parts:
            text_parts.append(str(entity.get("id", "")))
        return "\n".join(text_parts)[:4000]

    def generate(self, text: str) -> list[float] | None:
        """Generate embedding vector using local sentence-transformers model."""
        model = self._get_model()
        try:
            return model.encode(text, normalize_embeddings=True).tolist()
        except Exception as exc:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider unavailable",
                provider="sentence-transformers",
                failure_cause=exc.__class__.__name__,
                retry_after_seconds=30,
                retry_hint="retry_with_backoff",
            ) from exc

    def attach(
        self, entity_type: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Attach embeddings to retrieval entity records before persistence."""
        if entity_type not in VECTOR_ENTITY_TYPES or not entities:
            return entities

        prepared: list[dict[str, Any]] = []
        for entity in entities:
            entity_copy = dict(entity)
            existing_embedding = entity_copy.get("embedding")
            if isinstance(existing_embedding, list) and existing_embedding:
                prepared.append(entity_copy)
                continue

            text = self.build_text(entity_copy)
            embedding = self.generate(text)
            if embedding is not None:
                entity_copy["embedding"] = embedding
                entity_copy["embedding_text"] = text[:2000]
            prepared.append(entity_copy)

        return prepared
