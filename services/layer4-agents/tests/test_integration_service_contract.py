from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

import layer4_agents.services.integration_service as module
from layer4_agents.models.account import CRMProvider
from layer4_agents.models.crm_sync_job import CRMSyncJobStatus
from layer4_agents.models.integration import Integration
from layer4_agents.services.integration_service import (
    IntegrationNotFoundError,
    IntegrationService,
    IntegrationValidationError,
)

TENANT = "550e8400-e29b-41d4-a716-446655440000"
JOB_ID = UUID("b109f3a2-b206-4a6f-a79f-c9b270d28d94")


class Result:
    def __init__(self, *, scalar=None, scalars=()):
        self.value = scalar
        self.values = list(scalars)

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.queries = []
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    def add(self, value):
        self.added.append(value)

    async def delete(self, value):
        self.deleted.append(value)

    async def commit(self):
        self.commits += 1

    async def refresh(self, value):
        if value.__class__.__name__ == "CRMSyncJob" and value.id is None:
            value.id = JOB_ID
        self.refreshed.append(value)

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0)


async def no_observation(*_args, **_kwargs):
    return None


@pytest.mark.parametrize(
    ("environment", "flag", "allowed"),
    [
        (None, None, True),
        ("test", None, True),
        ("production", None, False),
        ("production", "yes", True),
        ("production", "0", False),
    ],
)
def test_manual_salesforce_configuration_policy(monkeypatch, environment, flag, allowed) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)
    if flag is None:
        monkeypatch.delenv("ALLOW_SALESFORCE_MANUAL_CONFIG", raising=False)
    else:
        monkeypatch.setenv("ALLOW_SALESFORCE_MANUAL_CONFIG", flag)
    assert IntegrationService._manual_salesforce_config_allowed() is allowed


@pytest.mark.asyncio
async def test_list_get_and_delete_integrations_are_tenant_scoped() -> None:
    integration = object()
    db = DB(
        [
            Result(scalars=[integration]),
            Result(scalars=[]),
            Result(scalar=integration),
            Result(scalar=None),
            Result(scalar=integration),
        ]
    )
    svc = IntegrationService(db)
    assert await svc.list_integrations(TENANT) == [integration]
    assert await svc.list_integrations(TENANT, CRMProvider.HUBSPOT) == []
    assert await svc.get_integration(TENANT, CRMProvider.HUBSPOT) is integration
    assert not await svc.delete_integration(TENANT, CRMProvider.HUBSPOT)
    assert await svc.delete_integration(TENANT, CRMProvider.HUBSPOT, user_id="user")
    assert db.deleted == [integration] and db.commits == 1
    assert all("tenant_id" in str(query) for query in db.queries)


@pytest.mark.asyncio
async def test_create_integration_encrypts_credentials_and_observes_idle(monkeypatch) -> None:
    db = DB([Result(scalar=None)])
    observations = []

    async def observe(*args, **kwargs):
        observations.append((args, kwargs))

    async def encrypt(value, *, key_id):
        assert json.loads(value)["api_key"] == "key"
        assert len(json.loads(value)["webhook_token"]) == 64
        return b"encrypted"

    monkeypatch.setattr(module, "apply_observation", observe)
    monkeypatch.setattr(module.EncryptionService, "encrypt", encrypt)
    svc = IntegrationService(db)
    integration, created = await svc.create_or_update_integration(
        TENANT,
        CRMProvider.HUBSPOT,
        True,
        {"api_key": "key"},
        instance_url="https://api.hubspot.com",
        user_id="user",
    )
    assert created and integration in db.added
    assert integration.credentials_encrypted == b"encrypted"
    assert integration.created_by == integration.updated_by == "user"
    assert observations and db.commits == 1 and db.refreshed == [integration]


@pytest.mark.asyncio
async def test_update_integration_preserves_salesforce_values_and_webhook(monkeypatch) -> None:
    existing = Integration(
        tenant_id=TENANT,
        provider=CRMProvider.SALESFORCE,
        enabled=True,
        credentials_encrypted=b"old",
        encryption_key_id="old-key",
        instance_url="https://tenant.salesforce.com",
        sync_interval_minutes=60,
        sync_batch_size=100,
    )
    db = DB([Result(scalar=existing)])
    decrypts = [
        {"api_key": "old-token", "instance_url": existing.instance_url},
        {"webhook_token": "preserved"},
    ]

    async def decrypt(_integration):
        return decrypts.pop(0)

    encrypted_payloads = []

    async def encrypt(value, *, key_id):
        encrypted_payloads.append((json.loads(value), key_id))
        return b"new"

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(
        module.IntegrationService, "decrypt_credentials", lambda self, value: decrypt(value)
    )
    monkeypatch.setattr(module.EncryptionService, "encrypt", encrypt)
    monkeypatch.setattr(module, "apply_observation", no_observation)
    integration, created = await IntegrationService(db).create_or_update_integration(
        TENANT,
        CRMProvider.SALESFORCE,
        True,
        {},
        user_id="user",
        salesforce_org_id="org",
    )
    assert not created and integration is existing
    assert encrypted_payloads[0][0]["api_key"] == "old-token"
    assert encrypted_payloads[0][0]["webhook_token"] == "preserved"
    assert existing.instance_url == "https://tenant.salesforce.com"
    assert existing.salesforce_org_id == "org" and existing.updated_by == "user"


@pytest.mark.asyncio
async def test_salesforce_manual_policy_rejects_create_and_credential_update(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_SALESFORCE_MANUAL_CONFIG", raising=False)
    create = IntegrationService(DB([Result(scalar=None)]))
    with pytest.raises(IntegrationValidationError, match="Use the OAuth connect flow"):
        await create.create_or_update_integration(
            TENANT, CRMProvider.SALESFORCE, True, {"api_key": "key"}
        )
    existing = SimpleNamespace()
    update = IntegrationService(DB([Result(scalar=existing)]))
    with pytest.raises(IntegrationValidationError, match="OAuth reconnect flow"):
        await update.create_or_update_integration(
            TENANT, CRMProvider.SALESFORCE, True, {"api_key": "key"}
        )


@pytest.mark.asyncio
async def test_connection_contracts_not_configured_disabled_success_error_and_cancel(
    monkeypatch,
) -> None:
    svc = IntegrationService(DB())

    async def missing(*_args):
        return None

    svc.get_integration = missing
    result = await svc.test_connection(TENANT, CRMProvider.HUBSPOT)
    assert not result.success and result.error_code == "NOT_CONFIGURED"

    disabled = SimpleNamespace(enabled=False)

    async def disabled_lookup(*_args):
        return disabled

    svc.get_integration = disabled_lookup
    result = await svc.test_connection(TENANT, CRMProvider.HUBSPOT)
    assert not result.success and result.error_code == "DISABLED"

    integration = SimpleNamespace(enabled=True, credentials_encrypted=b"x", encryption_key_id="v1")

    async def found(*_args):
        return integration

    svc.get_integration = found
    monkeypatch.setattr(
        module.EncryptionService,
        "decrypt",
        lambda *_args: asyncio.sleep(0, result='{"api_key":"key"}'),
    )

    class Connector:
        async def test_connection(self):
            return {"success": True, "message": "Connected"}

    monkeypatch.setattr(module, "get_connector", lambda *_args: Connector())
    assert (await svc.test_connection(TENANT, CRMProvider.HUBSPOT)).success

    class Broken:
        async def test_connection(self):
            raise RuntimeError("offline")

    monkeypatch.setattr(module, "get_connector", lambda *_args: Broken())
    assert (
        await svc.test_connection(TENANT, CRMProvider.HUBSPOT)
    ).error_code == "CONNECTION_FAILED"

    class Cancelled:
        async def test_connection(self):
            raise asyncio.CancelledError

    monkeypatch.setattr(module, "get_connector", lambda *_args: Cancelled())
    with pytest.raises(asyncio.CancelledError):
        await svc.test_connection(TENANT, CRMProvider.HUBSPOT)


class Response:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.text = "response"

    def json(self):
        return self._data


class Client:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []
        self.error = None

    async def get(self, url, **kwargs):
        if self.error:
            raise self.error
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "success", "error_code"),
    [(200, True, None), (401, False, "AUTH_FAILED"), (503, False, "API_ERROR_503")],
)
async def test_salesforce_connection_status_contracts(status, success, error_code) -> None:
    client = Client([Response(status, {"records": [{"Name": "Acme"}]})])
    result = await IntegrationService(None)._test_salesforce_connection(
        client, {"api_key": "token"}, "https://tenant.salesforce.com"
    )
    assert result.success is success and result.error_code == error_code
    if success:
        assert result.details["organization"] == "Acme"
        assert client.calls[0][1]["headers"]["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_salesforce_connection_validates_inputs_and_transport_errors() -> None:
    svc = IntegrationService(None)
    assert (
        await svc._test_salesforce_connection(Client(), {}, None)
    ).error_code == "MISSING_CREDENTIALS"
    assert (
        await svc._test_salesforce_connection(Client(), {"api_key": "token"}, None)
    ).error_code == "MISSING_INSTANCE_URL"
    client = Client()
    client.error = httpx.TimeoutException("timeout")
    assert (
        await svc._test_salesforce_connection(client, {"api_key": "token"}, "https://x.test")
    ).error_code == "TIMEOUT"
    client.error = httpx.NetworkError("offline")
    assert (
        await svc._test_salesforce_connection(client, {"api_key": "token"}, "https://x.test")
    ).error_code == "NETWORK_ERROR"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "success", "error_code"),
    [(200, True, None), (401, False, "AUTH_FAILED"), (429, False, "API_ERROR_429")],
)
async def test_hubspot_connection_status_contracts(status, success, error_code) -> None:
    client = Client([Response(status, {"portalName": "Acme"})])
    result = await IntegrationService(None)._test_hubspot_connection(client, {"api_key": "token"})
    assert result.success is success and result.error_code == error_code
    if success:
        assert result.details["portal_name"] == "Acme"


@pytest.mark.asyncio
async def test_hubspot_connection_validates_inputs_and_transport_errors() -> None:
    svc = IntegrationService(None)
    assert (await svc._test_hubspot_connection(Client(), {})).error_code == "MISSING_CREDENTIALS"
    client = Client()
    client.error = httpx.TimeoutException("timeout")
    assert (
        await svc._test_hubspot_connection(client, {"api_key": "token"})
    ).error_code == "TIMEOUT"
    client.error = httpx.NetworkError("offline")
    assert (
        await svc._test_hubspot_connection(client, {"api_key": "token"})
    ).error_code == "NETWORK_ERROR"


@pytest.mark.asyncio
async def test_crm_connection_dispatches_provider(monkeypatch) -> None:
    calls = []

    class AsyncClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    svc = IntegrationService(None)

    async def salesforce(*_args):
        return {"provider": "salesforce"}

    async def hubspot(*_args):
        return {"provider": "hubspot"}

    svc._test_salesforce_connection = salesforce
    svc._test_hubspot_connection = hubspot
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    assert (await svc._test_crm_connection(CRMProvider.SALESFORCE, {}, None))[
        "provider"
    ] == "salesforce"
    assert (await svc._test_crm_connection(CRMProvider.HUBSPOT, {}, None))["provider"] == "hubspot"
    other = SimpleNamespace(value="other")
    assert (await svc._test_crm_connection(other, {}, None)).error_code == "UNSUPPORTED_PROVIDER"


@pytest.mark.asyncio
async def test_trigger_sync_validates_state_queues_job_and_handles_enqueue_failure(
    monkeypatch,
) -> None:
    svc = IntegrationService(DB())

    async def missing(*_args):
        return None

    svc.get_integration = missing
    with pytest.raises(IntegrationNotFoundError):
        await svc.trigger_sync(TENANT, CRMProvider.HUBSPOT)

    disabled = SimpleNamespace(enabled=False)

    async def disabled_lookup(*_args):
        return disabled

    svc.get_integration = disabled_lookup
    with pytest.raises(IntegrationValidationError, match="disabled"):
        await svc.trigger_sync(TENANT, CRMProvider.HUBSPOT)

    integration = SimpleNamespace(enabled=True, last_error_message=None)
    db = DB()
    svc = IntegrationService(db)

    async def found(*_args):
        return integration

    svc.get_integration = found
    monkeypatch.setattr(module, "apply_observation", no_observation)
    queued = []

    async def enqueue(**kwargs):
        queued.append(kwargs)

    monkeypatch.setattr(module, "enqueue_crm_sync_job", enqueue)
    result = await svc.trigger_sync(TENANT, CRMProvider.HUBSPOT, "user")
    assert result.status == "queued" and result.job_id == str(JOB_ID)
    assert queued[0]["tenant_id"] == TENANT and db.added[0].status == CRMSyncJobStatus.QUEUED

    async def fail(**_kwargs):
        raise RuntimeError("redis offline")

    monkeypatch.setattr(module, "enqueue_crm_sync_job", fail)
    with pytest.raises(IntegrationValidationError, match="Unable to queue"):
        await svc.trigger_sync(TENANT, CRMProvider.HUBSPOT)
    failed_job = db.added[-1]
    assert failed_job.status == CRMSyncJobStatus.FAILED
    assert "redis offline" in failed_job.error_summary
    assert "redis offline" in integration.last_error_message


@pytest.mark.asyncio
async def test_sync_job_queries_are_tenant_and_provider_scoped() -> None:
    jobs = [object()]
    job = object()
    db = DB([Result(scalars=jobs), Result(scalar=job)])
    svc = IntegrationService(db)
    assert await svc.list_sync_jobs(TENANT, CRMProvider.SALESFORCE, limit=3) == jobs
    assert await svc.get_sync_job(TENANT, CRMProvider.SALESFORCE, str(JOB_ID)) is job
    assert all("tenant_id" in str(query) and "provider" in str(query) for query in db.queries)


@pytest.mark.asyncio
async def test_decrypt_credentials_enforces_tenant_and_decodes_json(monkeypatch) -> None:
    integration = SimpleNamespace(
        tenant_id=TENANT, credentials_encrypted=b"x", encryption_key_id="v1"
    )
    svc = IntegrationService(None)
    with pytest.raises(IntegrationValidationError, match="does not match"):
        await svc.decrypt_credentials(integration, tenant_id="other")
    monkeypatch.setattr(
        module.EncryptionService,
        "decrypt",
        lambda *_args: asyncio.sleep(0, result='{"api_key":"key"}'),
    )
    assert await svc.decrypt_credentials(integration, tenant_id=TENANT) == {"api_key": "key"}
