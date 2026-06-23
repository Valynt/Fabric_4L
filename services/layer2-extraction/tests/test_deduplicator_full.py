"""Comprehensive tests for EntityDeduplicator covering all methods."""
from __future__ import annotations

import math

from layer2_extraction.extraction.deduplicator import EntityDeduplicator
from layer2_extraction.models.ontology import (
    Capability,
    Feature,
    Persona,
    RoleType,
    UseCase,
    ValueCategory,
    ValueDriver,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cap(id: str, name: str = "Cap Name", confidence: float = 0.8, **kw) -> Capability:
    return Capability(id=id, name=name, description="A capability description", confidence=confidence, **kw)


def _uc(id: str, name: str = "Use Case Name", confidence: float = 0.8, **kw) -> UseCase:
    return UseCase(id=id, name=name, description="A use case description", confidence=confidence, **kw)


def _persona(id: str, title: str = "Product Manager", confidence: float = 0.8, **kw) -> Persona:
    return Persona(id=id, title=title, role_type=RoleType.CHAMPION, department="Product", confidence=confidence, **kw)


def _vd(id: str, name: str = "Value Driver Name", confidence: float = 0.8, **kw) -> ValueDriver:
    return ValueDriver(
        id=id, name=name, description="A value driver description",
        category=ValueCategory.REVENUE, confidence=confidence, **kw
    )


def _feat(id: str, name: str = "Feature Name", confidence: float = 0.8, **kw) -> Feature:
    return Feature(id=id, name=name, description="A feature description", confidence=confidence, **kw)


class _CapWithEmbedding:
    """Minimal entity-like object that carries an embedding for deduplicator tests.

    OntologyEntity uses extra='forbid', so we can't attach arbitrary fields.
    The deduplicator only needs: id, name, confidence, source_refs, embedding.
    """

    def __init__(self, id: str, embedding: list[float], confidence: float = 0.8) -> None:
        self.id = id
        self.name = "Cap Name"
        self.description = "A capability description"
        self.confidence = confidence
        self.source_refs: list[str] = []
        self.embedding = embedding

    def model_copy(self, *, deep: bool = False) -> "_CapWithEmbedding":
        import copy
        return copy.deepcopy(self) if deep else copy.copy(self)


def _cap_with_embedding(id: str, embedding: list[float], confidence: float = 0.8) -> _CapWithEmbedding:
    return _CapWithEmbedding(id=id, embedding=embedding, confidence=confidence)


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        sim = EntityDeduplicator._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert abs(sim - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        sim = EntityDeduplicator._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim) < 1e-9

    def test_opposite_vectors(self):
        sim = EntityDeduplicator._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert abs(sim - (-1.0)) < 1e-9

    def test_zero_vector_returns_zero(self):
        sim = EntityDeduplicator._cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert sim == 0.0

    def test_both_zero_vectors(self):
        sim = EntityDeduplicator._cosine_similarity([0.0, 0.0], [0.0, 0.0])
        assert sim == 0.0

    def test_partial_similarity(self):
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        expected = 1.0 / math.sqrt(2)
        assert abs(EntityDeduplicator._cosine_similarity(a, b) - expected) < 1e-9


# ---------------------------------------------------------------------------
# compute_similarity_matrix
# ---------------------------------------------------------------------------

class TestComputeSimilarityMatrix:
    def test_no_embeddings_returns_identity_like(self):
        d = EntityDeduplicator()
        caps = [_cap("c1"), _cap("c2")]
        matrix = d.compute_similarity_matrix(caps)
        assert matrix[0][0] == 1.0
        assert matrix[1][1] == 1.0
        assert matrix[0][1] == 0.0

    def test_identical_embeddings_returns_1(self):
        d = EntityDeduplicator()
        c1 = _cap_with_embedding("c1", [1.0, 0.0, 0.0])
        c2 = _cap_with_embedding("c2", [1.0, 0.0, 0.0])
        matrix = d.compute_similarity_matrix([c1, c2])
        assert abs(matrix[0][1] - 1.0) < 1e-6

    def test_orthogonal_embeddings_returns_0(self):
        d = EntityDeduplicator()
        c1 = _cap_with_embedding("c1", [1.0, 0.0])
        c2 = _cap_with_embedding("c2", [0.0, 1.0])
        matrix = d.compute_similarity_matrix([c1, c2])
        assert abs(matrix[0][1]) < 1e-6

    def test_single_entity(self):
        d = EntityDeduplicator()
        c1 = _cap_with_embedding("c1", [1.0, 0.0])
        matrix = d.compute_similarity_matrix([c1])
        assert abs(matrix[0][0] - 1.0) < 1e-6

    def test_missing_embedding_padded_with_zeros(self):
        d = EntityDeduplicator()
        c1 = _cap_with_embedding("c1", [1.0, 0.0])
        c2 = _cap("c2")  # no embedding -> zero vector
        matrix = d.compute_similarity_matrix([c1, c2])
        assert abs(matrix[0][1]) < 1e-6


# ---------------------------------------------------------------------------
# cluster / _find_clusters
# ---------------------------------------------------------------------------

class TestCluster:
    def test_all_similar_forms_one_cluster(self):
        d = EntityDeduplicator(similarity_threshold=0.5)
        matrix = [[1.0, 0.9], [0.9, 1.0]]
        clusters = d.cluster(matrix)
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1]

    def test_dissimilar_forms_two_clusters(self):
        d = EntityDeduplicator(similarity_threshold=0.9)
        matrix = [[1.0, 0.1], [0.1, 1.0]]
        clusters = d.cluster(matrix)
        assert len(clusters) == 2

    def test_empty_matrix(self):
        d = EntityDeduplicator()
        clusters = d.cluster([])
        assert clusters == []

    def test_three_entities_chain(self):
        # 0-1 similar, 1-2 similar -> all in one cluster via BFS
        d = EntityDeduplicator(similarity_threshold=0.8)
        matrix = [
            [1.0, 0.9, 0.3],
            [0.9, 1.0, 0.9],
            [0.3, 0.9, 1.0],
        ]
        clusters = d.cluster(matrix)
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1, 2]


# ---------------------------------------------------------------------------
# _select_canonical
# ---------------------------------------------------------------------------

class TestSelectCanonical:
    def test_selects_highest_confidence(self):
        d = EntityDeduplicator()
        c1 = _cap("c1", confidence=0.5)
        c2 = _cap("c2", confidence=0.9)
        assert d._select_canonical([c1, c2]).id == "c2"

    def test_selects_most_source_refs_first(self):
        d = EntityDeduplicator()
        c1 = _cap("c1", confidence=0.9, source_refs=["a", "b", "c"])
        c2 = _cap("c2", confidence=0.9, source_refs=["x"])
        assert d._select_canonical([c1, c2]).id == "c1"


# ---------------------------------------------------------------------------
# _entity_to_text
# ---------------------------------------------------------------------------

class TestEntityToText:
    def test_capability_with_features(self):
        d = EntityDeduplicator()
        c = _cap("c1", name="Analytics Engine")
        c.technical_features = ["streaming", "real-time"]
        text = d._entity_to_text(c)
        assert "Analytics Engine" in text
        assert "streaming" in text

    def test_capability_no_features(self):
        d = EntityDeduplicator()
        c = _cap("c1", name="Analytics Engine")
        text = d._entity_to_text(c)
        assert "Analytics Engine" in text

    def test_usecase_with_industry(self):
        d = EntityDeduplicator()
        uc = _uc("u1", name="Fraud Detection")
        uc.industry_context = ["banking"]
        text = d._entity_to_text(uc)
        assert "Fraud Detection" in text
        assert "banking" in text

    def test_persona_with_department_and_pain_points(self):
        d = EntityDeduplicator()
        p = _persona("p1", title="CTO")
        p.department = "Engineering"
        p.pain_points = ["slow deploys"]
        text = d._entity_to_text(p)
        assert "CTO" in text
        assert "Engineering" in text
        assert "slow deploys" in text

    def test_value_driver_with_metrics(self):
        d = EntityDeduplicator()
        vd = _vd("v1", name="Cost Savings")
        vd.metrics = ["10% reduction"]
        text = d._entity_to_text(vd)
        assert "Cost Savings" in text

    def test_feature_with_spec_and_status(self):
        d = EntityDeduplicator()
        f = _feat("f1", name="Export Feature")
        f.implementation_status = "ga"
        f.technical_spec = "CSV/JSON export"
        text = d._entity_to_text(f)
        assert "Export Feature" in text
        assert "ga" in text

    def test_unknown_entity_returns_empty(self):
        d = EntityDeduplicator()

        class _Unknown:
            pass

        assert d._entity_to_text(_Unknown()) == ""


# ---------------------------------------------------------------------------
# _merge_into_canonical (type-specific merges)
# ---------------------------------------------------------------------------

class TestMergeCapabilityFields:
    def test_merges_technical_features(self):
        d = EntityDeduplicator()
        c1 = _cap("c1", source_refs=["r1"])
        c1.technical_features = ["streaming"]
        c2 = _cap("c2", source_refs=["r2"])
        c2.technical_features = ["batch", "streaming"]
        canonical = c1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [c1, c2])
        assert "streaming" in canonical.technical_features
        assert "batch" in canonical.technical_features

    def test_deduplicates_features(self):
        d = EntityDeduplicator()
        c1 = _cap("c1")
        c1.technical_features = ["a", "b"]
        c2 = _cap("c2")
        c2.technical_features = ["b", "c"]
        canonical = c1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [c1, c2])
        assert canonical.technical_features.count("b") == 1

    def test_takes_max_confidence(self):
        d = EntityDeduplicator()
        c1 = _cap("c1", confidence=0.5)
        c2 = _cap("c2", confidence=0.9)
        canonical = c1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [c1, c2])
        assert canonical.confidence == 0.9

    def test_unions_source_refs(self):
        d = EntityDeduplicator()
        c1 = _cap("c1", source_refs=["ref-a"])
        c2 = _cap("c2", source_refs=["ref-b"])
        canonical = c1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [c1, c2])
        assert "ref-a" in canonical.source_refs
        assert "ref-b" in canonical.source_refs


class TestMergeUseCaseFields:
    def test_merges_industry_context(self):
        d = EntityDeduplicator()
        u1 = _uc("u1")
        u1.industry_context = ["banking"]
        u2 = _uc("u2")
        u2.industry_context = ["insurance"]
        canonical = u1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [u1, u2])
        assert "banking" in canonical.industry_context
        assert "insurance" in canonical.industry_context

    def test_merges_kpis(self):
        d = EntityDeduplicator()
        u1 = _uc("u1")
        u1.kpis = ["reduce fraud by 20%"]
        u2 = _uc("u2")
        u2.kpis = ["save 5h/week"]
        canonical = u1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [u1, u2])
        assert "reduce fraud by 20%" in canonical.kpis
        assert "save 5h/week" in canonical.kpis


class TestMergePersonaFields:
    def test_merges_pain_points(self):
        d = EntityDeduplicator()
        p1 = _persona("p1")
        p1.pain_points = ["slow reports"]
        p2 = _persona("p2")
        p2.pain_points = ["manual work"]
        canonical = p1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [p1, p2])
        assert "slow reports" in canonical.pain_points
        assert "manual work" in canonical.pain_points

    def test_deduplicates_pain_points(self):
        d = EntityDeduplicator()
        p1 = _persona("p1")
        p1.pain_points = ["slow reports"]
        p2 = _persona("p2")
        p2.pain_points = ["slow reports", "manual work"]
        canonical = p1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [p1, p2])
        assert canonical.pain_points.count("slow reports") == 1


class TestMergeValueDriverFields:
    def test_merges_metrics(self):
        d = EntityDeduplicator()
        v1 = _vd("v1")
        v1.metrics = ["10% cost reduction"]
        v2 = _vd("v2")
        v2.metrics = ["5x ROI"]
        canonical = v1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [v1, v2])
        assert "10% cost reduction" in canonical.metrics
        assert "5x ROI" in canonical.metrics


class TestMergeFeatureFields:
    def test_keeps_longest_technical_spec(self):
        d = EntityDeduplicator()
        f1 = _feat("f1")
        f1.technical_spec = "short"
        f2 = _feat("f2")
        f2.technical_spec = "much longer technical specification"
        canonical = f1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [f1, f2])
        assert canonical.technical_spec == "much longer technical specification"

    def test_keeps_most_advanced_status_ga(self):
        d = EntityDeduplicator()
        f1 = _feat("f1")
        f1.implementation_status = "planned"
        f2 = _feat("f2")
        f2.implementation_status = "ga"
        canonical = f1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [f1, f2])
        assert canonical.implementation_status == "ga"

    def test_beta_beats_planned(self):
        d = EntityDeduplicator()
        f1 = _feat("f1")
        f1.implementation_status = "planned"
        f2 = _feat("f2")
        f2.implementation_status = "beta"
        canonical = f1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [f1, f2])
        assert canonical.implementation_status == "beta"

    def test_no_spec_not_overwritten(self):
        d = EntityDeduplicator()
        f1 = _feat("f1")
        f1.technical_spec = "existing spec"
        f2 = _feat("f2")
        f2.technical_spec = None
        canonical = f1.model_copy(deep=True)
        d._merge_into_canonical(canonical, [f1, f2])
        assert canonical.technical_spec == "existing spec"


# ---------------------------------------------------------------------------
# deduplicate (end-to-end)
# ---------------------------------------------------------------------------

class TestDeduplicate:
    def test_empty_list(self):
        d = EntityDeduplicator()
        assert d.deduplicate([]) == []

    def test_single_entity_unchanged(self):
        d = EntityDeduplicator()
        c = _cap("c1", name="Analytics Engine")
        result = d.deduplicate([c])
        assert len(result) == 1
        assert result[0].name == "Analytics Engine"

    def test_dissimilar_entities_preserved(self):
        d = EntityDeduplicator(similarity_threshold=0.99)
        c1 = _cap_with_embedding("c1", [1.0, 0.0, 0.0], confidence=0.8)
        c2 = _cap_with_embedding("c2", [0.0, 1.0, 0.0], confidence=0.8)
        result = d.deduplicate([c1, c2])
        assert len(result) == 2

    def test_identical_embeddings_merged(self):
        d = EntityDeduplicator(similarity_threshold=0.85)
        c1 = _cap_with_embedding("c1", [1.0, 0.0], confidence=0.7)
        c2 = _cap_with_embedding("c2", [1.0, 0.0], confidence=0.9)
        result = d.deduplicate([c1, c2])
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_source_refs_unioned_on_merge(self):
        d = EntityDeduplicator(similarity_threshold=0.85)
        c1 = _cap_with_embedding("c1", [1.0, 0.0], confidence=0.8)
        c1.source_refs = ["ref-a"]
        c2 = _cap_with_embedding("c2", [1.0, 0.0], confidence=0.8)
        c2.source_refs = ["ref-b"]
        result = d.deduplicate([c1, c2])
        assert len(result) == 1
        assert "ref-a" in result[0].source_refs
        assert "ref-b" in result[0].source_refs

    def test_no_embeddings_all_separate_clusters(self):
        # Without embeddings, similarity matrix is identity-like (off-diagonal = 0)
        # so each entity forms its own cluster
        d = EntityDeduplicator(similarity_threshold=0.85)
        caps = [_cap(f"c{i}") for i in range(3)]
        result = d.deduplicate(caps)
        assert len(result) == 3
