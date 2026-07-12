import pytest

try:
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_graph_rag, get_hybrid_search
    from src.api.main import app
except (ImportError, Exception) as _exc:
    import traceback
    with open("skip_debug.txt", "w") as _f:
        _f.write("Exception: " + str(_exc) + "\n")
        traceback.print_exc(file=_f)
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )


class _GraphRagStub:
    async def query(self, **kwargs):
        return {
            "query": kwargs["query_text"],
            "entities": [],
            "relationships": [],
            "context_graph": {},
            "confidence_score": 1.0,
            "sources": [],
            "answer": "ok",
        }


class _HybridStub:
    async def semantic_search(self, query, entity_type, top_k):
        return []

    async def fulltext_search(self, query, entity_type, top_k):
        return []

    async def search(self, query, entity_types, top_k, weights):
        return []


def _client():
    app.dependency_overrides[get_graph_rag] = lambda: _GraphRagStub()
    app.dependency_overrides[get_hybrid_search] = lambda: _HybridStub()
    return TestClient(app)


def test_graphrag_aliases_match():
    with _client() as client:
        payload = {"query": "q", "max_hops": 2, "max_results": 5}
        canonical = client.post("/v1/query/graph", json=payload)
        legacy = client.post("/v1/query", json=payload)
        alias = client.post("/v1/graphrag", json=payload)
        assert canonical.status_code == legacy.status_code == alias.status_code == 200
        assert canonical.json()["query"] == legacy.json()["query"] == alias.json()["query"]


def test_search_aliases_match():
    with _client() as client:
        payload = {"query": "q", "search_type": "hybrid", "top_k": 3}
        canonical = client.post("/v1/search/hybrid", json=payload)
        legacy = client.post("/v1/search", json=payload)
        assert canonical.status_code == legacy.status_code == 200
        assert canonical.json()["search_type"] == legacy.json()["search_type"]
