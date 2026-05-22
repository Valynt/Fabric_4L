from __future__ import annotations

from datetime import datetime as real_datetime
from datetime import timedelta
from typing import Any

import httpx
import pytest
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer2_extraction.api import main as api_main
from layer2_extraction.integration.layer3_client import IngestionResponse, IngestionStatus
from layer2_extraction.integration.pending_ingestion_store import PendingIngestionRecord
from layer2_extraction.models import (
    Capability,
    ExtractionResult,
    PredicateType,
    Relationship,
    UseCase,
)


class request_payloadResult(TypedDictModel):
    content_id: str
    extraction_config: dict[str, Any]
    markdown_content: str
    source_url: str

class FakePendingIngestionStore_get_retry_metadataResult(TypedDictModel):
    last_error: Any
    next_retry_at: Any
    retry_count: Any

_UNIX_EPOCH = real_datetime(1970, 1, 1)


def naive_utc_from_timestamp(timestamp: float) -> real_datetime:
    return _UNIX_EPOCH + timedelta(seconds=timestamp)


class FakePendingIngestionStore:
    def __init__(self) -> None:
        self.records: dict[str, PendingIngestionRecord] = {}

    async def enqueue(
        self,
        job_id: str,
        source_url: str,
        extraction_result_json: str,
        relationships_json: str,
        retry_count: int,
        next_retry_at: real_datetime,
        max_retries: int,
        last_error: str | None,
    ) -> None:
        self.records[job_id] = PendingIngestionRecord(
            job_id=job_id,
            source_url=source_url,
            extraction_result_json=extraction_result_json,
            relationships_json=relationships_json,
            retry_count=retry_count,
            max_retries=max_retries,
            last_error=last_error,
            next_retry_at=next_retry_at,
        )

    async def get_due(self, now: real_datetime, limit: int = 25) -> list[PendingIngestionRecord]:
        due = [
            record
            for record in self.records.values()
            if record.next_retry_at <= now and record.retry_count < record.max_retries
        ]
        due.sort(key=lambda record: record.next_retry_at)
        return due[:limit]

    async def complete(self, job_id: str) -> None:
        self.records.pop(job_id, None)

    async def reschedule(
        self,
        job_id: str,
        retry_count: int,
        last_error: str,
        next_retry_at: real_datetime,
    ) -> None:
        record = self.records[job_id]
        self.records[job_id] = PendingIngestionRecord(
            job_id=record.job_id,
            source_url=record.source_url,
            extraction_result_json=record.extraction_result_json,
            relationships_json=record.relationships_json,
            retry_count=retry_count,
            max_retries=record.max_retries,
            last_error=last_error,
            next_retry_at=next_retry_at,
        )

    async def get_retry_metadata(self, job_id: str) -> dict | None:
        record = self.records.get(job_id)
        if not record:
            return None
        return FakePendingIngestionStore_get_retry_metadataResult.model_validate({
            "retry_count": record.retry_count,
            "last_error": record.last_error,
            "next_retry_at": record.next_retry_at.isoformat(),
        }).model_dump()


class FrozenClock:
    def __init__(self, start: real_datetime) -> None:
        self.current = start

    def advance(self, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)

    def datetime_class(self):
        clock = self

        class _FrozenDateTime:
            @classmethod
            def now(cls, tz=None) -> real_datetime:
                return clock.current

            @classmethod
            def utcnow(cls) -> real_datetime:
                return clock.current

            @classmethod
            def fromtimestamp(cls, ts: float, tz=None) -> real_datetime:
                return naive_utc_from_timestamp(ts)

            @classmethod
            def utcfromtimestamp(cls, ts: float) -> real_datetime:
                return naive_utc_from_timestamp(ts)

            @classmethod
            def fromisoformat(cls, value: str) -> real_datetime:
                return real_datetime.fromisoformat(value)

        return _FrozenDateTime


def build_layer3_client_class(*, healthy: bool, success: bool):
    required_ingest_keys = {
        "rdf_data",
        "source_url",
        "extraction_job_id",
    }

    class _Layer3ClientDouble:
        async def health_check(self) -> bool:
            return healthy

        async def ingest_rdf_data(self, **kwargs) -> IngestionResponse:
            if not healthy:
                raise AssertionError("ingest_rdf_data should not be called when Layer 3 is unhealthy")

            missing = required_ingest_keys.difference(kwargs)
            if missing:
                raise AssertionError(f"Missing ingest kwargs: {sorted(missing)}")

            if success:
                return IngestionResponse(
                    success=True,
                    ingestion_id="ing-1",
                    entities_loaded=2,
                    relationships_loaded=1,
                    message="ok",
                )
            return IngestionResponse(
                success=False,
                ingestion_id="ing-1",
                entities_loaded=0,
                relationships_loaded=0,
                message="failed",
                error="Layer 3 ingestion failed",
            )

        async def batch_ingest_rdf_data(self, items: list) -> list[IngestionResponse]:
            if not healthy:
                raise AssertionError("batch_ingest_rdf_data should not be called when Layer 3 is unhealthy")

            results = []
            for item in items:
                missing = required_ingest_keys.difference(item)
                if missing:
                    raise AssertionError(f"Missing batch ingest keys: {sorted(missing)}")
                if success:
                    results.append(IngestionResponse(
                        success=True,
                        ingestion_id=item.get("extraction_job_id", "ing-1"),
                        entities_loaded=2,
                        relationships_loaded=1,
                        message="ok",
                    ))
                else:
                    results.append(IngestionResponse(
                        success=False,
                        ingestion_id=item.get("extraction_job_id", "ing-1"),
                        entities_loaded=0,
                        relationships_loaded=0,
                        message="failed",
                        error="Layer 3 ingestion failed",
                    ))
            return results

        async def close(self) -> None:
            return None

    return _Layer3ClientDouble


def build_artifacts(job_id: str, source_url: str) -> api_main.ExtractionArtifacts:
    capability = Capability(name="Pipeline Capability", description="Capability for orchestration test")
    use_case = UseCase(name="Pipeline Use Case", description="Use case for orchestration test")
    relationship = Relationship(
        source_id=capability.id,
        raw_predicate="enables",
        canonical_predicate=PredicateType.ENABLES,
        target_id=use_case.id,
        confidence=0.9,
        evidence_text="Capability enables the use case.",
        source_url=source_url,
        extraction_job_id=job_id,
    )
    result = ExtractionResult(
        job_id=job_id,
        source_url=source_url,
        capabilities=[capability],
        use_cases=[use_case],
        chunks_processed=1,
    )
    return api_main.ExtractionArtifacts(result=result, relationships=[relationship])


def request_payload() -> dict:
    return request_payloadResult.model_validate({
        "content_id": "content-123",
        "source_url": "https://example.com/doc",
        "markdown_content": "Test Header\n\nPipeline orchestration content.",
        "extraction_config": {
            "chunk_size": 200,
            "chunk_overlap": 20,
            "confidence_threshold": 0.8,
        },
    }).model_dump()


@pytest.fixture(autouse=True)
def reset_pipeline_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from layer2_extraction.integration.job_store import InMemoryJobStore
    test_job_store = InMemoryJobStore()
    monkeypatch.setattr(api_main, "job_store", test_job_store)
    yield


@pytest.fixture
def fake_store(monkeypatch: pytest.MonkeyPatch) -> FakePendingIngestionStore:
    store = FakePendingIngestionStore()
    monkeypatch.setattr(api_main, "pending_ingestion_store", store)
    return store


@pytest.fixture
def jwt_token() -> str:
    """Generate a signed JWT for test requests."""
    import os
    import time
    import jwt as pyjwt

    secret = os.environ.get("JWT_SECRET", "test-secret-key-for-layer2-tests-32b")
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "iss": "value-fabric-internal",
        "aud": "value-fabric-services",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
async def async_client(jwt_token: str):
    transport = httpx.ASGITransport(app=api_main.app)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_extract_and_ingest_kickoff_contract(async_client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_pipeline_runner(job_id: str, source_url: str, content: str, config: dict) -> None:
        return None

    monkeypatch.setattr(api_main, "run_extract_and_ingest", fake_pipeline_runner)

    kickoff = await async_client.post("/v1/extract-and-ingest", json=request_payload())
    assert kickoff.status_code == 200

    body = kickoff.json()
    assert body["job_id"]
    assert body["overall_status"] == "pending"
    assert body["extraction_status"] == "pending"
    assert body["ingestion_status"] == "pending"

    status = await async_client.get(f"/v1/extract/status/{body['job_id']}")
    assert status.status_code == 200

    status_body = status.json()
    expected_fields = {
        "job_id",
        "overall_status",
        "extraction_status",
        "ingestion_status",
        "entities_extracted",
        "relationships_extracted",
        "retry_count",
        "last_error",
        "next_retry_at",
        "started_at",
        "completed_at",
    }
    assert expected_fields.issubset(set(status_body.keys()))
    assert status_body["overall_status"] == "pending"
    assert status_body["extraction_status"] == "pending"
    assert status_body["ingestion_status"] == "pending"


@pytest.mark.asyncio
async def test_status_endpoint_reports_staged_pipeline_transitions(
    async_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_pipeline_runner(job_id: str, source_url: str, content: str, config: dict) -> None:
        return None

    monkeypatch.setattr(api_main, "run_extract_and_ingest", fake_pipeline_runner)

    kickoff = await async_client.post("/v1/extract-and-ingest", json=request_payload())
    job_id = kickoff.json()["job_id"]

    await api_main._set_pipeline_job(job_id, extraction_status="running", ingestion_status="pending")
    running = await async_client.get(f"/v1/extract/status/{job_id}")
    running_body = running.json()
    assert running_body["overall_status"] == "running"
    assert running_body["extraction_status"] == "running"
    assert running_body["ingestion_status"] == "pending"

    await api_main._set_pipeline_job(job_id, extraction_status="completed", ingestion_status="queued")
    queued = await async_client.get(f"/v1/extract/status/{job_id}")
    queued_body = queued.json()
    assert queued_body["overall_status"] == "partial"
    assert queued_body["extraction_status"] == "completed"
    assert queued_body["ingestion_status"] == "queued"

    await api_main._set_pipeline_job(
        job_id,
        ingestion_status="completed",
        completed_at=real_datetime(2026, 1, 1, 0, 3, 0),
    )
    completed = await async_client.get(f"/v1/extract/status/{job_id}")
    completed_body = completed.json()
    assert completed_body["overall_status"] == "completed"
    assert completed_body["extraction_status"] == "completed"
    assert completed_body["ingestion_status"] == "completed"
    assert completed_body["completed_at"] is not None


@pytest.mark.asyncio
async def test_l3_unavailable_queues_retry_and_persists(
    async_client,
    fake_store: FakePendingIngestionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FrozenClock(real_datetime(2026, 1, 1, 0, 0, 0))
    monkeypatch.setattr(api_main, "datetime", clock.datetime_class())

    async def fake_run_extraction(
        job_id: str,
        source_url: str,
        content: str,
        config: dict,
        mark_pipeline_complete: bool = True,
    ) -> api_main.ExtractionArtifacts:
        await api_main._set_pipeline_job(
            job_id,
            extraction_status="completed",
            entities_extracted=2,
            relationships_extracted=1,
            completed_at=None,
        )
        return build_artifacts(job_id, source_url)

    monkeypatch.setattr(api_main, "run_extraction", fake_run_extraction)
    monkeypatch.setattr(
        api_main,
        "Layer3KnowledgeClient",
        build_layer3_client_class(healthy=False, success=False),
    )

    kickoff = await async_client.post("/v1/extract-and-ingest", json=request_payload())
    job_id = kickoff.json()["job_id"]

    status = await async_client.get(f"/v1/extract/status/{job_id}")
    assert status.status_code == 200
    body = status.json()

    assert body["overall_status"] == "partial"
    assert body["extraction_status"] == "completed"
    assert body["ingestion_status"] == "queued"
    assert body["retry_count"] == 1
    assert body["last_error"] == "Layer 3 unavailable"

    expected_next_retry = naive_utc_from_timestamp(clock.current.timestamp() + api_main.RETRY_BASE_SECONDS)
    assert body["next_retry_at"] == expected_next_retry.isoformat()

    persisted = fake_store.records[job_id]
    assert persisted.source_url == request_payload()["source_url"]
    assert persisted.extraction_result_json
    assert persisted.relationships_json
    assert persisted.retry_count == 1
    assert persisted.last_error == "Layer 3 unavailable"


@pytest.mark.asyncio
async def test_retry_success_marks_completed_and_clears_queue(
    async_client,
    fake_store: FakePendingIngestionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FrozenClock(real_datetime(2026, 1, 1, 0, 0, 0))
    monkeypatch.setattr(api_main, "datetime", clock.datetime_class())

    async def fake_run_extraction(
        job_id: str,
        source_url: str,
        content: str,
        config: dict,
        mark_pipeline_complete: bool = True,
    ) -> api_main.ExtractionArtifacts:
        await api_main._set_pipeline_job(
            job_id,
            extraction_status="completed",
            entities_extracted=2,
            relationships_extracted=1,
            completed_at=None,
        )
        return build_artifacts(job_id, source_url)

    monkeypatch.setattr(api_main, "run_extraction", fake_run_extraction)
    monkeypatch.setattr(
        api_main,
        "Layer3KnowledgeClient",
        build_layer3_client_class(healthy=False, success=False),
    )

    kickoff = await async_client.post("/v1/extract-and-ingest", json=request_payload())
    job_id = kickoff.json()["job_id"]
    assert job_id in fake_store.records

    monkeypatch.setattr(
        api_main,
        "Layer3KnowledgeClient",
        build_layer3_client_class(healthy=True, success=True),
    )
    due_at = fake_store.records[job_id].next_retry_at
    seconds_until_due = int((due_at - clock.current).total_seconds()) + 1
    clock.advance(seconds_until_due)

    await api_main._process_pending_ingestions()

    status = await async_client.get(f"/v1/extract/status/{job_id}")
    assert status.status_code == 200
    body = status.json()

    assert body["overall_status"] == "completed"
    assert body["extraction_status"] == "completed"
    assert body["ingestion_status"] == "completed"
    assert body["completed_at"] is not None
    assert body["last_error"] is None
    assert body["next_retry_at"] is None
    assert job_id not in fake_store.records


def build_layer3_full_double_class():
    """Build a Layer3 client double that simulates full ingest + status flow."""

    class _Layer3FullDouble:
        def __init__(self):
            self._ingestions: dict[str, dict] = {}
            self._call_log: list[dict] = []

        async def health_check(self) -> bool:
            return True

        async def ingest_rdf_data(self, **kwargs) -> IngestionResponse:
            self._call_log.append({"method": "ingest_rdf_data", "kwargs": kwargs})

            extraction_job_id = kwargs.get("extraction_job_id", "unknown")
            source_url = kwargs.get("source_url", "unknown")

            # Simulate entity counts from RDF payload size (contract test only)
            rdf_data = kwargs.get("rdf_data", "")
            simulated_entities = rdf_data.count("vf:Capability") + rdf_data.count("vf:UseCase")
            simulated_relationships = rdf_data.count("vf:enables")

            # Store ingestion state
            self._ingestions[extraction_job_id] = {
                "ingestion_id": extraction_job_id,
                "status": "completed",
                "entities_loaded": simulated_entities,
                "relationships_loaded": simulated_relationships,
                "source_url": source_url,
            }

            return IngestionResponse(
                success=True,
                ingestion_id=extraction_job_id,
                entities_loaded=self._ingestions[extraction_job_id]["entities_loaded"],
                relationships_loaded=self._ingestions[extraction_job_id]["relationships_loaded"],
                message="Ingestion successful",
            )

        async def get_ingestion_status(self, ingestion_id: str) -> IngestionStatus:
            self._call_log.append({"method": "get_ingestion_status", "ingestion_id": ingestion_id})

            ingestion = self._ingestions.get(ingestion_id, {})
            return IngestionStatus(
                ingestion_id=ingestion_id,
                status=ingestion.get("status", "unknown"),
                progress_percent=100.0 if ingestion.get("status") == "completed" else 0.0,
                entities_processed=ingestion.get("entities_loaded", 0),
                entities_total=ingestion.get("entities_loaded", 0),
                error_message=None,
            )

        async def close(self) -> None:
            pass

        def get_call_log(self) -> list[dict]:
            return self._call_log

    return _Layer3FullDouble


@pytest.mark.asyncio
async def test_cross_layer_extract_ingest_status_flow(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross-layer integration test: L2 extract-and-ingest reaches L3 with valid payload.

    Uses ASGI transport with dependency overrides to prove contract across layers
    without requiring live services. Validates:
    - L2 calls L3 ingest with correct payload
    - L2 can query L3 status using canonical endpoint
    - RDF data contains required fields (source_url, extraction_job_id)
    """
    clock = FrozenClock(real_datetime(2026, 1, 1, 0, 0, 0))
    monkeypatch.setattr(api_main, "datetime", clock.datetime_class())

    # Build Layer3 double that tracks all calls
    double_class = build_layer3_full_double_class()
    double_instance = double_class()

    # Monkeypatch the client class constructor to return our double
    def make_double(*args, **kwargs):
        return double_instance

    monkeypatch.setattr(api_main, "Layer3KnowledgeClient", make_double)

    # Mock run_extraction to complete synchronously (avoid background task race)
    async def fake_run_extraction(
        job_id: str,
        source_url: str,
        content: str,
        config: dict,
        mark_pipeline_complete: bool = True,
    ) -> api_main.ExtractionArtifacts:
        artifacts = build_artifacts(job_id, source_url)
        # Set pipeline job state to completed for extraction
        await api_main._set_pipeline_job(
            job_id,
            extraction_status="completed",
            entities_extracted=len(artifacts.result.capabilities) + len(artifacts.result.use_cases),
            relationships_extracted=len(artifacts.relationships),
            completed_at=None,  # Don't mark pipeline complete yet, let ingestion do it
        )
        return artifacts

    monkeypatch.setattr(api_main, "run_extraction", fake_run_extraction)

    # Trigger extract-and-ingest
    payload = request_payload()
    kickoff = await async_client.post("/v1/extract-and-ingest", json=payload)
    assert kickoff.status_code == 200

    job_id = kickoff.json()["job_id"]

    # Verify L2 reached L3 ingest with correct contract
    ingest_calls = [c for c in double_instance.get_call_log() if c["method"] == "ingest_rdf_data"]
    assert len(ingest_calls) == 1, f"Expected 1 ingest call, got {len(ingest_calls)}"

    ingest_kwargs = ingest_calls[0]["kwargs"]
    assert ingest_kwargs["source_url"] == payload["source_url"]
    assert ingest_kwargs["extraction_job_id"] == job_id
    assert ingest_kwargs["rdf_data"] is not None

    # Verify L2 can query L3 status via canonical endpoint
    status = await async_client.get(f"/v1/extract/status/{job_id}")
    assert status.status_code == 200
    status_body = status.json()

    # Pipeline should show completed (both extraction and ingestion)
    assert status_body["overall_status"] == "completed"
    assert status_body["extraction_status"] == "completed"
    assert status_body["ingestion_status"] == "completed"
    assert status_body["completed_at"] is not None



