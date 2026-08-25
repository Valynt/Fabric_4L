from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from layer4_agents.models.tool_schemas import (
    FindPathsInput,
    GetEntityInput,
    GetRelationshipsInput,
    QueryGraphInput,
    SemanticSearchInput,
    TraverseTreeInput,
)
from layer4_agents.shared.domain.context import TenantContextError
from layer4_agents.tools.knowledge_tools import (
    ConfigurationError,
    FindPathsTool,
    GetEntityTool,
    GetRelationshipsTool,
    QueryGraphTool,
    SemanticSearchTool,
    TraverseTreeTool,
)

TENANT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class Context:
    tenant_id = TENANT_ID
    user_id = "user"

    def assert_valid(self):
        return None


class Result:
    def __init__(self, records=(), *, single=None):
        self.records = list(records)
        self.single_record = single

    async def data(self):
        return self.records

    async def single(self):
        return self.single_record

    def __aiter__(self):
        self.iterator = iter(self.records)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class Session:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def run(self, query, parameters):
        self.calls.append((query, parameters))
        outcome = self.results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class Driver:
    def __init__(self, results):
        self.session_instance = Session(results)

    def session(self, **_kwargs):
        return self.session_instance


@pytest.fixture(autouse=True)
def tenant(monkeypatch):
    monkeypatch.setattr(
        "layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context",
        lambda: Context(),
    )


def tool_config():
    return {"neo4j_password": "password", "neo4j_uri": "bolt://neo4j", "database": "db"}


def test_query_graph_tenant_injection_and_read_only_guards() -> None:
    tool = QueryGraphTool(tool_config())
    query, alias = tool._inject_tenant_filter("MATCH (account:Account) RETURN account", TENANT_ID)
    assert alias == "account" and "account.tenant_id = $tenant_id" in query
    query, _ = tool._inject_tenant_filter(
        "OPTIONAL MATCH path = (n:Account) WHERE n.active RETURN n", TENANT_ID
    )
    assert "WHERE n.tenant_id = $tenant_id AND" in query
    with pytest.raises(ValueError, match="unable to parse"):
        tool._inject_tenant_filter("RETURN 1", TENANT_ID)
    assert "Write operations" in tool._validate_read_only("MATCH (n) DELETE n")
    assert tool._validate_read_only("MATCH (n) RETURN n") is None
    assert tool._ensure_tenant_parameters({"tenant_id": "spoof", "x": 1}, TENANT_ID) == {
        "tenant_id": str(TENANT_ID),
        "x": 1,
    }


@pytest.mark.asyncio
async def test_query_graph_success_validation_error_failure_and_cancellation(monkeypatch) -> None:
    tool = QueryGraphTool(tool_config())
    tool._driver = Driver([Result([{"name": "Acme"}])])
    result = await tool.execute(QueryGraphInput(cypher_query="MATCH (n) RETURN n", parameters={}))
    assert result.row_count == 1 and result.columns == ["name"]
    assert tool._driver.session_instance.calls[0][1]["tenant_id"] == str(TENANT_ID)
    assert (await tool.execute(QueryGraphInput(cypher_query="CREATE (n)", parameters={}))).error
    assert (await tool.execute(QueryGraphInput(cypher_query="RETURN 1", parameters={}))).error

    tool._driver = Driver([RuntimeError("offline")])
    assert (
        await tool.execute(QueryGraphInput(cypher_query="MATCH (n) RETURN n", parameters={}))
    ).error == "QUERY_EXECUTION_ERROR"
    tool._driver = Driver([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(QueryGraphInput(cypher_query="MATCH (n) RETURN n", parameters={}))

    def missing():
        raise TenantContextError("missing")

    monkeypatch.setattr(
        "layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context", missing
    )
    assert (
        "Tenant context required"
        in (
            await tool.execute(QueryGraphInput(cypher_query="MATCH (n) RETURN n", parameters={}))
        ).error
    )


def test_neo4j_tools_require_password(monkeypatch) -> None:
    monkeypatch.setattr(
        "layer4_agents.tools.knowledge_tools.get_settings",
        lambda: SimpleNamespace(neo4j_password=None),
    )
    for cls in (
        QueryGraphTool,
        GetEntityTool,
        GetRelationshipsTool,
        TraverseTreeTool,
        FindPathsTool,
    ):
        with pytest.raises(ConfigurationError, match="password is required"):
            cls({})


def test_query_driver_is_lazy_and_cached(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        "layer4_agents.tools.knowledge_tools.AsyncGraphDatabase.driver",
        lambda *args, **kwargs: sentinel,
    )
    tool = QueryGraphTool(tool_config())
    assert tool._get_driver() is sentinel and tool._get_driver() is sentinel


@pytest.mark.asyncio
async def test_semantic_search_tenant_filter_threshold_and_missing_key(monkeypatch) -> None:
    matches = [
        SimpleNamespace(
            id="one", score=0.91, metadata={"entity_type": "Account", "text": "A" * 300}
        ),
        SimpleNamespace(id="two", score=0.2, metadata={}),
    ]

    class Index:
        def query(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(matches=matches)

    tool = SemanticSearchTool({"pinecone_api_key": "key", "llm_provider": "together"})
    index = Index()
    tool._index = index
    tool._pinecone_client = object()

    async def embedding(_text):
        return [0.1, 0.2]

    tool._get_embedding = embedding
    result = await tool.execute(
        SemanticSearchInput(
            query="Acme", entity_types=["Account"], top_k=5, similarity_threshold=0.8
        )
    )
    assert result.total_matches == 1
    assert index.kwargs["filter"] == {
        "tenant_id": str(TENANT_ID),
        "entity_type": {"$in": ["Account"]},
    }
    assert len(result.results[0]["description"]) == 200

    missing = SemanticSearchTool({})
    missing._get_embedding = embedding
    assert "Pinecone API key" in (await missing.execute(SemanticSearchInput(query="Acme"))).error


@pytest.mark.asyncio
async def test_semantic_embedding_provider_error_and_cancellation(monkeypatch) -> None:
    provider = SimpleNamespace(
        embed=lambda **_kwargs: asyncio.sleep(0, result=SimpleNamespace(embeddings=[[0.3]]))
    )
    monkeypatch.setattr(
        "layer4_agents.tools.knowledge_tools.get_llm_provider", lambda _config: provider
    )
    tool = SemanticSearchTool({"pinecone_api_key": "key"})
    assert await tool._get_embedding("text") == [0.3]

    async def fail(_text):
        raise RuntimeError("offline")

    tool._get_embedding = fail
    result = await tool.execute(SemanticSearchInput(query="Acme"))
    assert result.total_matches == 0

    async def cancel(_text):
        raise asyncio.CancelledError

    tool._get_embedding = cancel
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(SemanticSearchInput(query="Acme"))


@pytest.mark.asyncio
async def test_get_entity_success_missing_relationships_and_failure() -> None:
    entity = {"id": "entity", "name": "Acme"}
    rel = {
        "predicate": "ENABLES",
        "target_id": "target",
        "target_name": "Target",
        "target_labels": ["UseCase"],
    }
    tool = GetEntityTool(tool_config())
    tool._driver = Driver([Result(single={"n": entity, "labels": ["Account"]}), Result([rel])])
    result = await tool.execute(GetEntityInput(entity_id="entity", include_relationships=True))
    assert result.found and result.entity["entity_type"] == "Account"
    assert result.relationships[0]["target_type"] == "UseCase"

    # Prove tenant isolation invariant for relationship query
    query, params = tool._driver.session_instance.calls[1]
    assert "tenant_id: $tenant_id" in query
    assert query.count("tenant_id: $tenant_id") >= 2
    assert params["tenant_id"] == str(TENANT_ID)

    tool._driver = Driver([Result(single=None)])
    assert not (await tool.execute(GetEntityInput(entity_id="missing"))).found
    tool._driver = Driver([RuntimeError("offline")])
    assert not (await tool.execute(GetEntityInput(entity_id="entity"))).found


@pytest.mark.parametrize("predicate", ["ENABLES", None])
@pytest.mark.asyncio
async def test_get_relationships_filter_limit_and_error(predicate) -> None:
    records = [
        {
            "source_id": "a",
            "predicate": "ENABLES",
            "target_id": "b",
            "target_name": "B",
            "confidence": None,
        },
        {
            "source_id": "a",
            "predicate": "USES",
            "target_id": "c",
            "target_name": "C",
            "confidence": 0.9,
        },
    ]
    tool = GetRelationshipsTool(tool_config())
    tool._driver = Driver([Result(records)])
    result = await tool.execute(GetRelationshipsInput(entity_id="a", predicate=predicate, limit=1))
    assert result.total_count == 2 and len(result.relationships) == 1
    assert result.relationships[0]["confidence"] == 0.8
    tool._driver = Driver([RuntimeError("offline")])
    assert (await tool.execute(GetRelationshipsInput(entity_id="a"))).total_count == 0


@pytest.mark.parametrize("predicate", ["!!!", "A-B"])
@pytest.mark.asyncio
async def test_get_relationships_rejects_invalid_predicate(predicate: str) -> None:
    tool = GetRelationshipsTool(tool_config())
    tool._driver = Driver([])

    result = await tool.execute(GetRelationshipsInput(entity_id="a", predicate=predicate))

    assert result.error == "INVALID_PREDICATE"
    assert result.relationships == []
    assert tool._driver.session_instance.calls == []


@pytest.mark.asyncio
async def test_traverse_tree_uses_path_pattern_and_discovers_unique_nodes() -> None:
    records = [
        {"path_nodes": [{"id": "a"}, {"id": "b"}]},
        {"path_nodes": [{"id": "a"}, {"id": "c"}]},
        {"path_nodes": []},
    ]
    tool = TraverseTreeTool(tool_config())
    tool._driver = Driver([Result(records)])
    result = await tool.execute(
        TraverseTreeInput(start_entity_id="a", path_pattern="(A)-[:ENABLES]->(B)", max_depth=4)
    )
    assert result.nodes_discovered == 3
    query, params = tool._driver.session_instance.calls[0]
    assert "ENABLES*1..4" in query and params["limit"] == 50
    tool._driver = Driver([RuntimeError("offline")])
    assert (await tool.execute(TraverseTreeInput(start_entity_id="a", path_pattern=""))).paths == []


@pytest.mark.asyncio
async def test_find_paths_uses_max_length_and_shortest_result() -> None:
    tool = FindPathsTool(tool_config())
    tool._driver = Driver(
        [
            Result(
                [
                    {
                        "path_nodes": [{"id": "a"}, {"id": "b"}],
                        "rel_types": ["ENABLES"],
                        "path_length": 3,
                    },
                    {
                        "path_nodes": [{"id": "a"}, {"id": "c"}],
                        "rel_types": ["USES"],
                        "path_length": 2,
                    },
                ]
            )
        ]
    )
    result = await tool.execute(FindPathsInput(source_id="a", target_id="b", max_length=7))
    assert result.shortest_path_length == 2
    query, params = tool._driver.session_instance.calls[0]
    assert "*1..7" in query and params["limit"] == 50
    tool._driver = Driver([RuntimeError("offline")])
    assert (await tool.execute(FindPathsInput(source_id="a", target_id="b"))).paths == []


@pytest.mark.parametrize(
    ("tool_cls", "input_data"),
    [
        (GetEntityTool, GetEntityInput(entity_id="a")),
        (GetRelationshipsTool, GetRelationshipsInput(entity_id="a")),
        (TraverseTreeTool, TraverseTreeInput(start_entity_id="a", path_pattern="")),
        (FindPathsTool, FindPathsInput(source_id="a", target_id="b")),
    ],
)
@pytest.mark.asyncio
async def test_graph_tools_propagate_cancellation(tool_cls, input_data) -> None:
    tool = tool_cls(tool_config())
    tool._driver = Driver([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(input_data)
