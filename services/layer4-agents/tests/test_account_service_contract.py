from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from layer4_agents.models.account import Account, CRMProvider, SyncStatus
from layer4_agents.services.account_service import AccountService, get_account_service

TENANT = "550e8400-e29b-41d4-a716-446655440000"
ACCOUNT_ID = UUID("5f7ed580-763c-4adb-9b4d-4c79e5152548")


class Result:
    def __init__(self, *, scalar=None, scalars=(), rows=()):
        self.value = scalar
        self.values = list(scalars)
        self.rows = list(rows)

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)

    def all(self):
        return self.rows


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.queries = []
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1

    async def refresh(self, value):
        self.refreshed.append(value)

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0)


def test_account_tenant_column_matches_canonical_uuid_schema() -> None:
    assert Account.__table__.c.tenant_id.type.as_uuid is True


@pytest.mark.asyncio
async def test_create_account_generates_manual_id_and_normalizes_name() -> None:
    db = DB([Result(scalar=None)])
    svc = AccountService(db)
    account = await svc.create_account(
        provider=CRMProvider.MANUAL,
        provider_record_id=None,
        name="  ACME Corp  ",
        tenant_id=TENANT,
        domain="acme.test",
        industry="Software",
        region="NA",
        company_size=100,
        annual_revenue=1_000_000,
        headquarters="NYC",
        website="https://acme.test",
        owner_id="owner",
        owner_name="Owner",
        owner_email="owner@acme.test",
        stage="customer",
        segment="enterprise",
        account_id=ACCOUNT_ID,
    )
    assert account.id == ACCOUNT_ID
    assert account.provider_record_id.startswith("manual-")
    assert account.normalized_name == "acme corp"
    assert account.tenant_id == UUID(TENANT)
    assert account.sync_status == SyncStatus.PENDING.value
    assert db.added == [account] and db.commits == 1 and db.refreshed == [account]


@pytest.mark.asyncio
async def test_create_account_rejects_missing_external_id_and_duplicate() -> None:
    svc = AccountService(DB())
    with pytest.raises(ValueError, match="provider_record_id is required"):
        await svc.create_account(
            provider=CRMProvider.SALESFORCE,
            provider_record_id=None,
            name="Acme",
            tenant_id=TENANT,
        )
    svc = AccountService(DB([Result(scalar=object())]))
    with pytest.raises(ValueError, match="Account already exists"):
        await svc.create_account(
            provider=CRMProvider.HUBSPOT,
            provider_record_id="record",
            name="Acme",
            tenant_id=TENANT,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["list_accounts", "search_accounts"])
async def test_list_and_search_apply_all_filters_sorting_and_pagination(method) -> None:
    accounts = [object(), object()]
    db = DB([Result(scalars=accounts), Result(scalar=2)])
    svc = AccountService(db)
    kwargs = {
        "provider": CRMProvider.SALESFORCE,
        "stage": "customer",
        "industry": "Software",
        "region": "NA",
        "segment": "enterprise",
        "owner_id": "owner",
        "sync_status": SyncStatus.SYNCED,
        "page": 3,
        "page_size": 10,
        "sort_by": "name",
        "sort_order": "asc",
        "tenant_id": TENANT,
    }
    if method == "search_accounts":
        kwargs["query_str"] = "ACME"
    result, total = await getattr(svc, method)(**kwargs)
    assert result == accounts and total == 2
    rendered = str(db.queries[0])
    for column in (
        "tenant_id",
        "provider",
        "stage",
        "industry",
        "region",
        "segment",
        "owner_id",
        "sync_status",
    ):
        assert column in rendered
    if method == "search_accounts":
        assert "lower" in rendered.lower()
    assert "ORDER BY" in rendered and "LIMIT" in rendered and "OFFSET" in rendered


@pytest.mark.asyncio
async def test_list_and_search_default_to_updated_desc_without_filters() -> None:
    db = DB([Result(scalars=[]), Result(scalar=0), Result(scalars=[]), Result(scalar=0)])
    svc = AccountService(db)
    assert await svc.list_accounts(sort_by="not_a_column") == ([], 0)
    assert await svc.search_accounts() == ([], 0)
    assert all("updated_at DESC" in str(query) for query in (db.queries[0], db.queries[2]))


@pytest.mark.asyncio
async def test_account_lookups_optionally_scope_tenant() -> None:
    first, second, third, fourth = object(), object(), object(), object()
    db = DB(
        [
            Result(scalar=first),
            Result(scalar=second),
            Result(scalar=third),
            Result(scalar=fourth),
        ]
    )
    svc = AccountService(db)
    assert await svc.get_account(ACCOUNT_ID) is first
    assert await svc.get_account(ACCOUNT_ID, tenant_id=TENANT) is second
    assert await svc.get_account_by_provider_id(CRMProvider.HUBSPOT, "record") is third
    assert (
        await svc.get_account_by_provider_id(CRMProvider.HUBSPOT, "record", tenant_id=TENANT)
        is fourth
    )
    assert "AND accounts.tenant_id" not in str(db.queries[0])
    assert "AND accounts.tenant_id" in str(db.queries[1])
    assert "AND accounts.tenant_id" not in str(db.queries[2])
    assert "AND accounts.tenant_id" in str(db.queries[3])


@pytest.mark.asyncio
async def test_account_activity_maps_results_and_handles_errors(monkeypatch) -> None:
    account = SimpleNamespace(provider_record_id="crm-record")
    svc = AccountService(DB())

    async def found(*_args, **_kwargs):
        return account

    svc.get_account = found

    class Tool:
        async def execute(self, input_data):
            assert input_data.prospect_id == "crm-record" and input_data.limit == 7
            return SimpleNamespace(
                interactions=[
                    {
                        "id": "i1",
                        "type": "call",
                        "date": "2026-07-01",
                        "subject": "Review",
                        "duration_minutes": 30,
                        "notes": "Notes",
                        "outcome": "next step",
                    },
                    {},
                ],
                total_count=2,
                summary="Two interactions",
            )

    monkeypatch.setattr("layer4_agents.services.account_service.FetchInteractionHistoryTool", Tool)
    result = await svc.get_account_activity(ACCOUNT_ID, limit=7, since_days=10, tenant_id=TENANT)
    assert result.account_id == ACCOUNT_ID and result.total_count == 2
    assert result.interactions[0]["duration_minutes"] == 30
    assert result.interactions[1]["type"] == "unknown"

    class Broken:
        async def execute(self, _input_data):
            raise RuntimeError("offline")

    monkeypatch.setattr(
        "layer4_agents.services.account_service.FetchInteractionHistoryTool", Broken
    )
    result = await svc.get_account_activity(ACCOUNT_ID)
    assert result.total_count == 0 and result.summary == "Activity data unavailable"

    class Cancelled:
        async def execute(self, _input_data):
            raise asyncio.CancelledError

    monkeypatch.setattr(
        "layer4_agents.services.account_service.FetchInteractionHistoryTool", Cancelled
    )
    with pytest.raises(asyncio.CancelledError):
        await svc.get_account_activity(ACCOUNT_ID)

    async def missing(*_args, **_kwargs):
        return None

    svc.get_account = missing
    with pytest.raises(ValueError, match="Account not found"):
        await svc.get_account_activity(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_sync_status_queries() -> None:
    status = object()
    statuses = [object(), object()]
    db = DB([Result(scalar=status), Result(scalars=statuses)])
    svc = AccountService(db)
    assert await svc.get_sync_status(CRMProvider.SALESFORCE, TENANT) is status
    assert await svc.get_all_sync_status(TENANT) == statuses
    assert all("tenant_id" in str(query) for query in db.queries)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "account_ids", "force_refresh", "stats", "expected_status", "expected_calls"),
    [
        (
            CRMProvider.SALESFORCE,
            None,
            False,
            [{"updated": 3, "failed": 0, "errors": []}],
            "completed",
            1,
        ),
        (
            CRMProvider.HUBSPOT,
            None,
            True,
            [{"updated": 2, "failed": 1, "errors": ["x"]}],
            "partial",
            1,
        ),
        (
            None,
            ["a"],
            False,
            [{"updated": 1, "failed": 0}, {"updated": 2, "failed": 1}],
            "partial",
            2,
        ),
        (
            None,
            None,
            True,
            [{"updated": 1, "failed": 0}, {"updated": 2, "failed": 0}],
            "completed",
            2,
        ),
    ],
)
async def test_trigger_sync_modes(
    monkeypatch, provider, account_ids, force_refresh, stats, expected_status, expected_calls
) -> None:
    calls = []

    class Sync:
        def __init__(self, db):
            assert db is not None

        async def sync_provider(self, prov, **kwargs):
            calls.append((prov, kwargs))
            return stats[len(calls) - 1]

    monkeypatch.setattr("layer4_agents.services.account_service.CRMSyncService", Sync)
    svc = AccountService(DB())
    result = await svc.trigger_sync(
        TENANT,
        provider=provider,
        account_ids=account_ids,
        force_refresh=force_refresh,
    )
    assert result.status == expected_status and len(calls) == expected_calls
    assert all(call[1]["tenant_id"] == TENANT for call in calls)
    assert all(call[1]["incremental"] is (not force_refresh) for call in calls)
    if provider or account_ids:
        assert all(call[1].get("account_ids") == account_ids for call in calls)
    else:
        assert all("account_ids" not in call[1] for call in calls)


@pytest.mark.asyncio
async def test_trigger_sync_requires_tenant_and_refresh_delegates(monkeypatch) -> None:
    svc = AccountService(DB())
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.trigger_sync("")

    class Sync:
        def __init__(self, _db):
            pass

        async def refresh_single_account(self, account_id, tenant_id):
            return account_id, tenant_id

    monkeypatch.setattr("layer4_agents.services.account_service.CRMSyncService", Sync)
    assert await svc.refresh_account(ACCOUNT_ID, TENANT) == (ACCOUNT_ID, TENANT)


@pytest.mark.asyncio
async def test_filter_options_are_tenant_scoped_deduplicated_and_normalized() -> None:
    db = DB(
        [
            Result(rows=[("Software",), (None,)]),
            Result(rows=[("customer",), (None,)]),
            Result(rows=[("NA",), (None,)]),
            Result(rows=[("enterprise",), (None,)]),
            Result(rows=[("owner", "Owner"), ("unknown", None), (None, "ignored")]),
        ]
    )
    svc = AccountService(db)
    result = await svc.get_filter_options(tenant_id=TENANT)
    assert result.industries == ["Software"]
    assert result.stages == ["customer"]
    assert result.regions == ["NA"]
    assert result.segments == ["enterprise"]
    assert result.owners == [{"id": "owner", "name": "Owner"}, {"id": "unknown", "name": "Unknown"}]
    assert set(result.providers) == {provider.value for provider in CRMProvider}
    assert all("tenant_id" in str(query) for query in db.queries)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.get_filter_options(tenant_id="")


@pytest.mark.asyncio
async def test_factory_returns_service() -> None:
    db = DB()
    svc = await get_account_service(db)
    assert isinstance(svc, AccountService) and svc.db is db
