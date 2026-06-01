"""Entity deduplicator for Layer 2 extraction."""

from __future__ import annotations

import math
from typing import Any

from layer2_extraction.models.ontology import (
    Capability,
    Feature,
    OntologyEntity,
    Persona,
    UseCase,
    ValueDriver,
)


class EntityDeduplicator:
    """Deduplicate entities using embedding similarity and clustering."""

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        self.threshold = similarity_threshold
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _compute_similarity_matrix(self, embeddings: Any) -> Any:
        """Compute pairwise cosine similarity matrix for embeddings (numpy array)."""
        import numpy as np

        embeddings = np.array(embeddings)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = embeddings / norms
        sim = np.dot(normalized, normalized.T)
        # Clamp to [-1, 1] to avoid floating-point drift
        return np.clip(sim, -1.0, 1.0)

    def compute_similarity_matrix(
        self, entities: list[OntologyEntity]
    ) -> list[list[float]]:
        """Compute pairwise cosine similarity matrix for entity embeddings."""
        import numpy as np

        # Collect embeddings; missing embeddings become zero vectors
        embeddings = []
        dim = 0
        for e in entities:
            emb = getattr(e, "embedding", None) or []
            if emb:
                dim = len(emb)
            embeddings.append(emb)

        # If no embeddings at all, return identity-like fallback
        if dim == 0:
            n = len(entities)
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        # Pad missing embeddings with zeros so we can use vectorized numpy ops
        padded = []
        for emb in embeddings:
            if emb:
                padded.append(emb)
            else:
                padded.append([0.0] * dim)

        sim = self._compute_similarity_matrix(np.array(padded, dtype=np.float64))
        return sim.tolist()

    def _find_clusters(self, similarity_matrix: Any) -> list[list[int]]:
        """Cluster entity indices based on similarity matrix using BFS."""
        import numpy as np

        matrix = np.array(similarity_matrix)
        if matrix.size == 0:
            return []
        n = matrix.shape[0]
        adj = matrix >= self.threshold
        visited = np.zeros(n, dtype=bool)
        clusters: list[list[int]] = []

        for i in range(n):
            if visited[i]:
                continue
            cluster: list[int] = []
            queue = [i]
            visited[i] = True
            while queue:
                curr = queue.pop(0)
                cluster.append(curr)
                neighbors = np.where(~visited & adj[curr])[0]
                if neighbors.size:
                    visited[neighbors] = True
                    queue.extend(neighbors.tolist())
            clusters.append(cluster)
        return clusters

    def cluster(self, similarity_matrix: list[list[float]]) -> list[list[int]]:
        """Cluster entity indices based on similarity matrix using BFS."""
        return self._find_clusters(similarity_matrix)

    def _select_canonical(self, entities: list[OntologyEntity]) -> OntologyEntity:
        """Select the canonical entity from a cluster (most source refs, then highest confidence)."""

        def score(e: OntologyEntity) -> tuple[int, float]:
            refs = len(getattr(e, "source_refs", []) or [])
            return (refs, e.confidence)

        return max(entities, key=lambda e: score(e))

    def _entity_to_text(self, entity: Any) -> str:
        """Convert an entity to a text representation for embedding."""
        if isinstance(entity, Capability):
            parts = [entity.name]
            if entity.technical_features:
                parts.extend(entity.technical_features)
            return " ".join(parts)
        elif isinstance(entity, UseCase):
            parts = [entity.name]
            if entity.industry_context:
                parts.extend(entity.industry_context)
            return " ".join(parts)
        elif isinstance(entity, Persona):
            parts = [entity.title]
            if entity.department:
                parts.append(entity.department)
            if entity.pain_points:
                parts.extend(entity.pain_points)
            return " ".join(parts)
        elif isinstance(entity, ValueDriver):
            parts = [entity.name]
            if entity.category:
                parts.append(str(entity.category.value))
            if entity.metrics:
                parts.extend(entity.metrics)
            return " ".join(parts)
        elif isinstance(entity, Feature):
            parts = [entity.name]
            if entity.implementation_status:
                parts.append(entity.implementation_status)
            if entity.technical_spec:
                parts.append(entity.technical_spec)
            return " ".join(parts)
        return ""

    def _merge_into_canonical(
        self, canonical: OntologyEntity, entities: list[OntologyEntity]
    ) -> None:
        """Merge a list of entities into the canonical entity in place."""
        # Keep highest confidence
        canonical.confidence = max(e.confidence for e in entities)
        # Union source refs
        all_refs: list[str] = []
        for e in entities:
            all_refs.extend(e.source_refs)
        canonical.source_refs = list(dict.fromkeys(all_refs))

        # Delegate to type-specific merge helpers
        if isinstance(canonical, Capability):
            self._merge_capability_fields(canonical, entities)
        elif isinstance(canonical, UseCase):
            self._merge_usecase_fields(canonical, entities)
        elif isinstance(canonical, Persona):
            self._merge_persona_fields(canonical, entities)
        elif isinstance(canonical, ValueDriver):
            self._merge_valuedriver_fields(canonical, entities)
        elif isinstance(canonical, Feature):
            self._merge_feature_fields(canonical, entities)

    def _merge_capability_fields(
        self, canonical: Capability, entities: list[OntologyEntity]
    ) -> None:
        all_features: list[str] = []
        all_integrations: list[str] = []
        for e in entities:
            if isinstance(e, Capability):
                all_features.extend(e.technical_features)
                all_integrations.extend(getattr(e, "integrations", []) or [])
        canonical.technical_features = list(dict.fromkeys(all_features))
        canonical.integrations = list(dict.fromkeys(all_integrations))

    def _merge_usecase_fields(
        self, canonical: UseCase, entities: list[OntologyEntity]
    ) -> None:
        all_industries: list[str] = []
        all_kpis: list[str] = []
        all_steps: list[str] = []
        for e in entities:
            if isinstance(e, UseCase):
                all_industries.extend(e.industry_context)
                all_kpis.extend(getattr(e, "kpis", []) or [])
                steps = getattr(e, "workflow_steps", []) or []
                for s in steps:
                    if s not in all_steps:
                        all_steps.append(s)
        canonical.industry_context = list(dict.fromkeys(all_industries))
        canonical.kpis = list(dict.fromkeys(all_kpis))
        canonical.workflow_steps = all_steps

    def _merge_persona_fields(
        self, canonical: Persona, entities: list[OntologyEntity]
    ) -> None:
        all_pain_points: list[str] = []
        for e in entities:
            if isinstance(e, Persona):
                all_pain_points.extend(e.pain_points)
        canonical.pain_points = list(dict.fromkeys(all_pain_points))

    def _merge_valuedriver_fields(
        self, canonical: ValueDriver, entities: list[OntologyEntity]
    ) -> None:
        all_metrics: list[str] = []
        for e in entities:
            if isinstance(e, ValueDriver):
                all_metrics.extend(e.metrics)
        canonical.metrics = list(dict.fromkeys(all_metrics))

    def _merge_feature_fields(
        self, canonical: Feature, entities: list[OntologyEntity]
    ) -> None:
        # Keep longest technical_spec
        longest_spec = ""
        for e in entities:
            if isinstance(e, Feature):
                spec = getattr(e, "technical_spec", None) or ""
                if len(spec) > len(longest_spec):
                    longest_spec = spec
        if longest_spec:
            canonical.technical_spec = longest_spec

        # Keep most advanced status: ga > beta > planned
        status_order = {"ga": 3, "beta": 2, "planned": 1}
        best_status = canonical.implementation_status
        best_rank = status_order.get(best_status, 0)
        for e in entities:
            if isinstance(e, Feature):
                rank = status_order.get(e.implementation_status, 0)
                if rank > best_rank:
                    best_rank = rank
                    best_status = e.implementation_status
        canonical.implementation_status = best_status

    def _merge_entities(self, entities: list[OntologyEntity]) -> OntologyEntity:
        """Merge a cluster of entities into a single canonical entity."""
        canonical = self._select_canonical(entities)
        merged = canonical.model_copy(deep=True)
        self._merge_into_canonical(merged, entities)
        return merged

    def deduplicate(self, entities: list[OntologyEntity]) -> list[OntologyEntity]:
        """Deduplicate a list of entities."""
        if not entities:
            return []
        sim_matrix = self.compute_similarity_matrix(entities)
        clusters = self.cluster(sim_matrix)
        result: list[OntologyEntity] = []
        for cluster in clusters:
            cluster_entities = [entities[i] for i in cluster]
            merged = self._merge_entities(cluster_entities)
            result.append(merged)
        return result


async def deduplicate_entities(
    entities: dict[str, list[Any]],
    *,
    api_key: str | None,
    similarity_threshold: float,
    relationships: list[Any],
    enable_coreference: bool,
) -> dict[str, list[Any]]:
    """Deduplicate entities across all types.

    Returns a dict mapping entity type to deduplicated list.
    """
    deduplicator = EntityDeduplicator(
        similarity_threshold=similarity_threshold,
    )
    result: dict[str, list[Any]] = {}
    for entity_type, entity_list in entities.items():
        if entity_list:
            result[entity_type] = deduplicator.deduplicate(entity_list)
        else:
            result[entity_type] = []
    return result
