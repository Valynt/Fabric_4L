"""Cross-store consistency integration tests for canonical event replay.

These tests exercise the failure modes called out by the database production
readiness gate without requiring live Postgres, Neo4j, vector, or object-store
services. They model the production invariant directly: PostgreSQL/outbox events
are canonical, while graph/vector/object/embedding state is derived and must be
replayable idempotently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from value_fabric.shared.projections.consistency import (
    CanonicalEvent,
    CrossStoreProjectionRebuilder,
    DerivedProjectionObservation,
    InMemoryProjectionOutbox,
    ProjectionStatus,
)


@dataclass
class RecordingProjectionTarget:
    name: str
    fail_times: int = 0
    applied: list[tuple[str, str]] = field(default_factory=list)

    def project(self, event: CanonicalEvent) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError(f"{self.name} projection unavailable")

        key = (event.aggregate_type, event.aggregate_id)
        if key not in self.applied:
            self.applied.append(key)


def _event(event_type: str, aggregate_type: str, aggregate_id: str) -> CanonicalEvent:
    tenant_id = uuid4()
    return CanonicalEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload={
            "tenant_id": str(tenant_id),
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
        },
    )


@pytest.mark.integration
def test_postgres_write_survives_neo4j_and_vector_projection_failures_then_replays() -> (
    None
):
    neo4j = RecordingProjectionTarget("neo4j_graph", fail_times=1)
    vector = RecordingProjectionTarget("vector_index", fail_times=1)
    outbox = InMemoryProjectionOutbox()
    rebuilder = CrossStoreProjectionRebuilder(outbox, [neo4j, vector], max_attempts=3)
    event = _event("source_corpus.upserted", "SourceCorpus", "corpus-123")

    rebuilder.enqueue(event)

    assert rebuilder.replay_pending() == 0
    assert outbox.get_event(event.event_id) == event
    assert (
        outbox.attempt_for(event.event_id, "neo4j_graph").status
        == ProjectionStatus.FAILED
    )
    assert (
        outbox.attempt_for(event.event_id, "vector_index").status
        == ProjectionStatus.FAILED
    )

    assert rebuilder.replay_pending() == 2
    assert (
        outbox.attempt_for(event.event_id, "neo4j_graph").status
        == ProjectionStatus.APPLIED
    )
    assert (
        outbox.attempt_for(event.event_id, "vector_index").status
        == ProjectionStatus.APPLIED
    )

    assert rebuilder.rebuild_event(event.event_id) == 2
    assert neo4j.applied == [("SourceCorpus", "corpus-123")]
    assert vector.applied == [("SourceCorpus", "corpus-123")]


@pytest.mark.integration
def test_document_upload_succeeds_but_embedding_generation_failure_is_inspectable() -> (
    None
):
    object_store = RecordingProjectionTarget("object_store")
    embedding = RecordingProjectionTarget("embedding_store", fail_times=1)
    rebuilder = CrossStoreProjectionRebuilder(
        InMemoryProjectionOutbox(),
        [object_store, embedding],
        max_attempts=3,
    )
    event = _event("document.uploaded", "Document", "doc-456")

    rebuilder.enqueue(event)

    assert rebuilder.replay_pending() == 1
    assert object_store.applied == [("Document", "doc-456")]
    failed = rebuilder.inspect_failed_projections()
    assert [(attempt.target, attempt.status) for attempt in failed] == [
        ("embedding_store", ProjectionStatus.FAILED)
    ]

    assert rebuilder.replay_pending() == 1
    assert rebuilder.inspect_failed_projections() == []


@pytest.mark.integration
def test_metadata_write_failure_after_derived_indexing_is_reported_as_orphan_projection() -> (
    None
):
    tenant_id = uuid4()
    vector_observation = DerivedProjectionObservation(
        target="vector_index",
        tenant_id=tenant_id,
        aggregate_type="DocumentMetadata",
        aggregate_id="doc-metadata-789",
    )
    rebuilder = CrossStoreProjectionRebuilder(
        InMemoryProjectionOutbox(),
        [RecordingProjectionTarget("vector_index")],
    )

    assert rebuilder.find_orphaned_derived_projections([vector_observation]) == [
        vector_observation
    ]

    canonical_event = CanonicalEvent(
        tenant_id=tenant_id,
        event_type="document.metadata.committed",
        aggregate_type="DocumentMetadata",
        aggregate_id="doc-metadata-789",
        payload={"tenant_id": str(tenant_id), "object_key": "uploads/doc-metadata-789"},
    )
    rebuilder.enqueue(canonical_event)

    assert rebuilder.find_orphaned_derived_projections([vector_observation]) == []


@pytest.mark.integration
def test_dead_letter_projection_inspection_exposes_failed_target_and_error() -> None:
    neo4j = RecordingProjectionTarget("neo4j_graph", fail_times=2)
    rebuilder = CrossStoreProjectionRebuilder(
        InMemoryProjectionOutbox(),
        [neo4j],
        max_attempts=2,
    )
    event = _event("source_corpus.upserted", "SourceCorpus", "corpus-dead-letter")

    rebuilder.enqueue(event)

    assert rebuilder.replay_pending() == 0
    assert rebuilder.replay_pending() == 0

    failed = rebuilder.inspect_failed_projections()
    assert len(failed) == 1
    assert failed[0].target == "neo4j_graph"
    assert failed[0].status == ProjectionStatus.DEAD_LETTER
    assert "neo4j_graph projection unavailable" in (failed[0].last_error or "")
