import pytest

from src.ingestion.neo4j.writers import (
    EntityBatchWriter,
    RelationshipBatchWriter,
)


class _FakeResult:
    async def single(self):
        return None


class _FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query, parameters=None):
        self.calls.append((query, parameters or {}))
        return _FakeResult()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeMutationGateway:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    async def write_nodes_batch(self, label, nodes):
        self.calls.append(("write_nodes_batch", label, nodes))
        return {"count": len(nodes)}

    async def write_relationships_batch(self, rel_type, triples):
        self.calls.append(("write_relationships_batch", rel_type, triples))
        return {"count": len(triples)}

    async def write_relationship(self, src_id, rel_type, tgt_id, properties=None):
        self.calls.append(("write_relationship", src_id, rel_type, tgt_id, properties))
        return {"status": "ok"}


class _FailingMutationGateway(_FakeMutationGateway):
    async def write_nodes_batch(self, label, nodes):
        raise RuntimeError("neo4j unavailable")

    async def write_relationships_batch(self, rel_type, triples):
        raise RuntimeError("neo4j unavailable")

    async def write_relationship(self, src_id, rel_type, tgt_id, properties=None):
        raise RuntimeError("neo4j unavailable")


def _failing_gateway_factory(**kwargs):
    return _FailingMutationGateway(**kwargs)


def _gateway_factory(captured):
    def _make(**kwargs):
        instance = _FakeMutationGateway(**kwargs)
        captured.append(instance)
        return instance

    return _make


@pytest.mark.asyncio
async def test_entity_writer_validates_and_writes():
    session = _FakeSession()
    created = []
    writer = EntityBatchWriter(mutation_gateway=_gateway_factory(created))
    count = await writer.write(
        session,
        "Capability",
        [{"id": "c1", "name": "Cap"}],
        "source-1",
        "job-1",
        "12345678-1234-1234-1234-123456789abc",
    )
    assert count == 1
    assert len(created) == 1
    assert created[0].calls[0][0] == "write_nodes_batch"
    assert created[0].calls[0][1] == "Capability"
    assert (
        created[0].calls[0][2][0]["tenant_id"] == "12345678-1234-1234-1234-123456789abc"
    )


@pytest.mark.asyncio
async def test_relationship_writer_groups_by_predicate():
    session = _FakeSession()
    created = []
    writer = RelationshipBatchWriter(mutation_gateway=_gateway_factory(created))
    count = await writer.write(
        session,
        {"enables": [{"source_id": "c1", "target_id": "u1", "predicate": "enables"}]},
        "source-1",
        "job-1",
        "12345678-1234-1234-1234-123456789abc",
    )
    assert count == 1
    assert len(created) == 1
    assert created[0].calls[0][0] == "write_relationships_batch"
    assert created[0].calls[0][1] == "enables"


@pytest.mark.asyncio
async def test_relationship_writer_native_uses_single_writes():
    session = _FakeSession()
    created = []
    writer = RelationshipBatchWriter(mutation_gateway=_gateway_factory(created))
    count = await writer.write_native(
        session,
        [{"source_id": "c1", "target_id": "u1", "predicate": "enables"}],
        "source-1",
        "job-1",
        "12345678-1234-1234-1234-123456789abc",
    )
    assert count == 1
    assert len(created) == 1
    assert created[0].calls[0][0] == "write_relationship"


@pytest.mark.asyncio
async def test_entity_writer_propagates_mutation_failure():
    writer = EntityBatchWriter(mutation_gateway=_failing_gateway_factory)

    with pytest.raises(RuntimeError, match="neo4j unavailable"):
        await writer.write(
            _FakeSession(),
            "Capability",
            [{"id": "c1", "name": "Cap"}],
            "source-1",
            "job-1",
            "12345678-1234-1234-1234-123456789abc",
        )


@pytest.mark.asyncio
async def test_relationship_writer_propagates_mutation_failure():
    writer = RelationshipBatchWriter(mutation_gateway=_failing_gateway_factory)

    with pytest.raises(RuntimeError, match="neo4j unavailable"):
        await writer.write(
            _FakeSession(),
            {
                "enables": [
                    {"source_id": "c1", "target_id": "u1", "predicate": "enables"}
                ]
            },
            "source-1",
            "job-1",
            "12345678-1234-1234-1234-123456789abc",
        )


@pytest.mark.asyncio
async def test_native_relationship_writer_propagates_mutation_failure():
    writer = RelationshipBatchWriter(mutation_gateway=_failing_gateway_factory)

    with pytest.raises(RuntimeError, match="neo4j unavailable"):
        await writer.write_native(
            _FakeSession(),
            [{"source_id": "c1", "target_id": "u1", "predicate": "enables"}],
            "source-1",
            "job-1",
            "12345678-1234-1234-1234-123456789abc",
        )
