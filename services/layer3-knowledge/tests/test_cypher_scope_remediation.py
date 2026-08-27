from __future__ import annotations

"""Regression tests for Layer 3 Cypher tenant-scope hardening."""


import pytest

from src.db.tenant_queries import get_entity_context
from src.retrieval.graph_rag import GraphRAGEngine


class _NoopSession:
    async def run(self, query, params):
        class _Result:
            async def single(self):
                return None

        self.query = query
        self.params = params
        return _Result()


@pytest.mark.asyncio
async def test_tenant_queries_reject_malicious_relationship_type() -> None:
    session = _NoopSession()
    with pytest.raises(ValueError, match="Invalid relationship type"):
        await get_entity_context(
            session,
            entity_id="entity-1",
            tenant_id="tenant-a",
            relationship_types=["enables']) MATCH (x) DETACH DELETE x //"],
        )


@pytest.mark.asyncio
async def test_tenant_queries_parameterize_relationship_filter() -> None:
    session = _NoopSession()
    await get_entity_context(
        session,
        entity_id="entity-1",
        tenant_id="tenant-a",
        relationship_types=["enables"],
    )

    assert "type(r) IN $relationship_types" in session.query
    assert session.params["relationship_types"] == ["enables"]


def test_graphrag_rejects_malicious_relationship_type() -> None:
    with pytest.raises(ValueError, match="Invalid relationship type"):
        from src.retrieval.graph_rag import _validate_relationship_types

        _validate_relationship_types(["enables']) MATCH (x) RETURN x //"])


def test_graphrag_rejects_invalid_entity_type() -> None:
    with pytest.raises(ValueError, match="Invalid entity_type"):
        from src.retrieval.graph_rag import _validate_entity_type

        _validate_entity_type("Entity`) MATCH (x) RETURN x //")


def test_graphrag_rejects_unbounded_hops() -> None:
    with pytest.raises(ValueError, match="hops must"):
        from src.retrieval.graph_rag import _validate_hops

        _validate_hops(99)


def test_graphrag_engine_instantiates_for_static_contract() -> None:
    assert GraphRAGEngine(driver=object())._driver is not None


class _EmptyAsyncResult:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _CaptureSession:
    def __init__(self):
        self.query = None
        self.params = None

    async def run(self, query, params):
        self.query = query
        self.params = params
        return _EmptyAsyncResult()


class _CaptureDriver:
    def __init__(self, session):
        self._session = session

    def session(self, **kwargs):
        class _Ctx:
            def __init__(self, s):
                self._s = s

            async def __aenter__(self):
                return self._s

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _Ctx(self._session)


@pytest.mark.asyncio
async def test_graphrag_expand_context_anchors_path_to_tenant_nodes() -> None:
    session = _CaptureSession()
    engine = GraphRAGEngine(driver=_CaptureDriver(session))

    await engine._expand_context(
        seed_entities=[{"id": "seed-1", "confidence": 0.9}],
        max_hops=2,
        min_confidence=0.1,
        tenant_id="tenant-a",
    )

    assert "ALL(node IN nodes(path) WHERE node.confidence >= $min_confidence AND node.tenant_id = $_tenant_id)" in session.query
    assert "ALL(rel IN relationships(path) WHERE rel.tenant_id = $_tenant_id)" in session.query
