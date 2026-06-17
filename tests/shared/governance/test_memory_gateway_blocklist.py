from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from value_fabric.shared.governance.memory_gateway import MemoryGateway


def _make_engine() -> MagicMock:
    engine = MagicMock()
    engine.query = AsyncMock(return_value={
        "query": "test",
        "entities": [
            {"id": "e1", "name": "Good", "source_id": "source-good"},
            {"id": "e2", "name": "Bad", "source_id": "source-bad"},
            {"id": "e3", "name": "NoSource"},
        ],
        "relationships": [
            {"source": "e1", "target": "e2", "type": "LINKS"},
            {"source": "e1", "target": "e3", "type": "LINKS"},
        ],
        "context_graph": {},
        "traversal_path": [],
        "confidence_score": 0.9,
        "sources": ["source-good", "source-bad"],
    })
    return engine


def _make_engine_with_provenance_source() -> MagicMock:
    engine = MagicMock()
    engine.query = AsyncMock(return_value={
        "query": "test",
        "entities": [
            {"id": "e1", "name": "Good", "source_id": "source-good"},
            {"id": "e2", "name": "BadProvenance", "provenance_source": "source-bad"},
            {"id": "e3", "name": "NoSource"},
        ],
        "relationships": [
            {"source": "e1", "target": "e2", "type": "LINKS"},
            {"source": "e1", "target": "e3", "type": "LINKS"},
        ],
        "context_graph": {},
        "traversal_path": [],
        "confidence_score": 0.9,
        "sources": ["source-good", "source-bad"],
    })
    return engine


@pytest.mark.asyncio
async def test_blocklist_filters_blocked_entities() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=["source-bad"],
    )
    result = await gw.query("test")

    entity_ids = {e["id"] for e in result["entities"]}
    assert "e1" in entity_ids
    assert "e2" not in entity_ids
    assert "e3" in entity_ids


@pytest.mark.asyncio
async def test_blocklist_filters_relationships_to_blocked_entities() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=["source-bad"],
    )
    result = await gw.query("test")

    rels = result["relationships"]
    assert len(rels) == 1
    assert rels[0]["target"] == "e3"


@pytest.mark.asyncio
async def test_per_call_blocklist_overrides_constructor() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=["source-bad"],
    )
    result = await gw.query("test", source_blocklist=[])
    assert len(result["entities"]) == 3



@pytest.mark.asyncio
async def test_per_call_none_blocklist_falls_back_to_constructor() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=["source-bad"],
    )
    result = await gw.query("test", source_blocklist=None)

    entity_ids = {e["id"] for e in result["entities"]}
    assert "e2" not in entity_ids
    assert len(result["entities"]) == 2


@pytest.mark.asyncio
async def test_entity_with_only_provenance_source_is_blocked() -> None:
    engine = _make_engine_with_provenance_source()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=["source-bad"],
    )
    result = await gw.query("test")

    entity_ids = {e["id"] for e in result["entities"]}
    assert "e2" not in entity_ids
    assert "e1" in entity_ids
    assert "e3" in entity_ids


@pytest.mark.asyncio
async def test_empty_constructor_blocklist_allows_all_entities() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
        source_blocklist=[],
    )
    result = await gw.query("test")

    assert len(result["entities"]) == 3


@pytest.mark.asyncio
async def test_provenance_present_on_result() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
    )
    result = await gw.query("test")

    assert "_provenance" in result
    assert result["_provenance"]["tenant_id"] == "t-1"
    assert "content_hash" in result["_provenance"]


@pytest.mark.asyncio
async def test_access_log_populated_after_query() -> None:
    engine = _make_engine()
    gw = MemoryGateway(
        retrieval_engine=engine,
        tenant_id="t-1",
    )
    assert gw.access_log == []

    await gw.query("test")

    assert len(gw.access_log) == 1
    assert gw.access_log[0]["query"] == "test"
    assert "content_hash" in gw.access_log[0]
