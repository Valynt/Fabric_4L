from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import layer4_agents.services.stripe_client as stripe_module
import layer4_agents.services.usage_service as module
from layer4_agents.models.billing import UsageEventStatus
from layer4_agents.services.usage_service import UsageService, UsageValidationError


class Result:
    def __init__(self, *, value=None, values=(), row=None):
        self.value = value
        self.values = list(values)
        self.row = row

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)

    def all(self):
        return self.values

    def one(self):
        return self.row


class DB:
    def __init__(self, results=(), flush_errors=()):
        self.results = list(results)
        self.flush_errors = list(flush_errors)
        self.added = []
        self.rollbacks = self.flushes = 0

    async def execute(self, _query):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    def add_all(self, values):
        self.added.extend(values)

    async def flush(self):
        self.flushes += 1
        if self.flush_errors:
            error = self.flush_errors.pop(0)
            if error:
                raise error

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_ingest_validation_and_success(monkeypatch) -> None:
    service = UsageService(DB(), None)
    with pytest.raises(UsageValidationError) as exc:
        await service.ingest_event("id", "customer", "event", "metric")
    assert exc.value.field == "tenant_id"

    service = UsageService(DB(), "tenant")
    for args, field in [
        (("", "c", "e", "m", 1), "event_id"),
        (("id", "", "e", "m", 1), "customer_id"),
        (("id", "c", "", "m", 1), "event_name"),
        (("id", "c", "e", "", 1), "metric_name"),
        (("id", "c", "e", "m", -1), "quantity"),
    ]:
        with pytest.raises(UsageValidationError) as exc:
            await service.ingest_event(*args)
        assert exc.value.field == field

    monkeypatch.setattr(service, "_report_to_stripe", lambda **_kwargs: _value({"id": "stripe"}))
    event = await service.ingest_event("id", "customer", "event", "tokens", metadata={"x": 1})
    assert event.tenant_id == "tenant" and event._stripe_response == {"id": "stripe"}


@pytest.mark.asyncio
async def test_ingest_duplicate_and_database_failure(monkeypatch) -> None:
    duplicate = SimpleNamespace()
    db = DB(flush_errors=[IntegrityError("x", {}, None)])
    service = UsageService(db, "tenant")
    monkeypatch.setattr(service, "_get_event_by_idempotency", lambda _id: _value(duplicate))
    assert await service.ingest_event("id", "c", "e", "m") is duplicate
    assert duplicate._stripe_response["reason"] == "duplicate" and db.rollbacks == 1

    db = DB(flush_errors=[SQLAlchemyError("db")])
    with pytest.raises(SQLAlchemyError):
        await UsageService(db, "tenant").ingest_event("id", "c", "e", "m")
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_batch_validation_duplicates_success_and_fallback(monkeypatch) -> None:
    with pytest.raises(UsageValidationError, match="Batch size"):
        await UsageService(DB(), "tenant").ingest_batch([{}] * 1001)
    with pytest.raises(UsageValidationError, match="tenant_id"):
        await UsageService(DB(), None).ingest_batch([])

    service = UsageService(DB(), "tenant")
    invalid = await service.ingest_batch([{"event_id": "bad"}])
    assert invalid.errors == 1 and invalid.created == 0

    valid = {
        "event_id": "one",
        "customer_id": "customer",
        "event_name": "event",
        "metric_name": "tokens",
    }
    monkeypatch.setattr(service, "_get_existing_event_ids", lambda _ids: _value({"one"}))
    duplicate = await service.ingest_batch([valid])
    assert duplicate.duplicates == 1 and duplicate.created == 0

    monkeypatch.setattr(service, "_get_existing_event_ids", lambda _ids: _value(set()))
    created = await service.ingest_batch([valid | {"event_id": "two"}])
    assert created.created == 1

    db = DB(flush_errors=[IntegrityError("x", {}, None)])
    service = UsageService(db, "tenant")
    monkeypatch.setattr(service, "_get_existing_event_ids", lambda _ids: _value(set()))
    monkeypatch.setattr(service, "ingest_event", lambda *_args, **_kwargs: _value(object()))
    fallback = await service.ingest_batch([valid])
    assert fallback.created == 1 and db.rollbacks == 1


@pytest.mark.asyncio
async def test_queries_and_processing_contracts() -> None:
    now = datetime.now(UTC)
    row = SimpleNamespace(total_quantity=4, event_count=2, first_event=now, last_event=now)
    event = SimpleNamespace(status=UsageEventStatus.PENDING, processed_at=None)
    db = DB(
        [
            Result(row=row),
            Result(values=[event]),
            Result(values=[event]),
            Result(value=event),
        ]
    )
    service = UsageService(db, "tenant")
    summary = await service.get_usage_summary("customer", "tokens", now, now)
    assert summary.total_quantity == 4 and summary.event_count == 2
    assert await service.list_customer_usage("customer", "tokens", now, now, limit=5000) == [event]
    assert await service.mark_events_processed([]) == 0
    assert await service.mark_events_processed(["id"]) == 1
    assert event.status == UsageEventStatus.PROCESSED and event.processed_at is not None
    assert await service._get_event_by_idempotency("id") is event
    assert await UsageService(DB(), None)._get_event_by_idempotency("id") is None

    for method, args in [
        (UsageService(DB(), None).get_usage_summary, ("c", "m")),
        (UsageService(DB(), None).list_customer_usage, ("c",)),
        (UsageService(DB(), None).mark_events_processed, (["id"],)),
    ]:
        with pytest.raises(UsageValidationError):
            await method(*args)


@pytest.mark.asyncio
async def test_stripe_reporting_and_sync(monkeypatch) -> None:
    service = UsageService(DB(), "tenant")
    monkeypatch.setattr(module, "AUTO_REPORT_TO_STRIPE", False)
    assert await service._report_to_stripe("c", "m", 1, "id") is None
    monkeypatch.setattr(module, "AUTO_REPORT_TO_STRIPE", True)
    monkeypatch.setattr(service, "_get_stripe_customer_id", lambda _id: _value(None))
    assert await service._report_to_stripe("c", "m", 1, "id") is None
    monkeypatch.setattr(service, "_get_stripe_customer_id", lambda _id: _value("cus"))
    monkeypatch.setattr(stripe_module, "report_meter_event", lambda **_kwargs: {"status": "ok"})
    assert (await service._report_to_stripe("c", "m", 1, "id"))["status"] == "ok"

    service = UsageService(DB(), None)
    with pytest.raises(UsageValidationError):
        await service.sync_to_stripe("c")
    service = UsageService(DB(), "tenant")
    monkeypatch.setattr(service, "_get_stripe_customer_id", lambda _id: _value(None))
    missing = await service.sync_to_stripe("c")
    assert missing.synced == 0 and "No Stripe" in missing.error

    monkeypatch.setattr(service, "_get_stripe_customer_id", lambda _id: _value("cus"))
    service.db.results = [Result(values=[])]
    empty = await service.sync_to_stripe("c")
    assert empty.synced == 0 and empty.message == "No pending events to sync"

    metric = SimpleNamespace(metric_name="tokens", total_quantity=5, event_count=2)
    events = [SimpleNamespace(status=None, processed_at=None)]
    service.db.results = [Result(values=[metric]), Result(values=events)]
    synced = await service.sync_to_stripe("c", "tokens")
    assert synced.synced == 2 and synced.metrics[0]["stripe_status"] == "ok"


async def _value(value):
    return value
