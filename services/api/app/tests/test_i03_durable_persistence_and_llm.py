import pytest

from app.core.config import Settings
from app.models.schemas import Account


def _sqlite_url(path):
    return f"sqlite:///{path}"


def test_sqlite_database_round_trips_records_and_enforces_tenant_scope(monkeypatch, tmp_path):
    from app.core import database

    db_file = tmp_path / "fabric_api.db"
    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url=_sqlite_url(db_file),
        llm_provider="layer4",
        seed_demo_data=False,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)

    durable = database.create_database()
    account = Account(
        id="acc-alpha",
        tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        name="Alpha Manufacturing",
        industry="manufacturing",
    )

    durable.accounts.insert(account.id, account)

    assert durable.accounts.get("acc-alpha", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") == account
    assert durable.accounts.get("acc-alpha", tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") is None
    assert durable.accounts.list(tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") == [account]
    assert durable.accounts.list(tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") == []
    assert durable.accounts.update("acc-alpha", tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", summary="leak") is None

    updated = durable.accounts.update("acc-alpha", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", summary="safe update")
    assert updated is not None
    assert updated.summary == "safe update"
    durable.close()

    reopened = database.SQLiteDatabase(_sqlite_url(db_file))
    persisted = reopened.accounts.get("acc-alpha", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert persisted is not None
    assert persisted.summary == "safe update"
    assert reopened.accounts.get("acc-alpha", tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") is None
    reopened.close()


def test_sqlite_database_allows_same_id_per_tenant_and_deletes_only_request_tenant(
    monkeypatch, tmp_path
):
    from app.core import database

    db_file = tmp_path / "fabric_api.db"
    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url=_sqlite_url(db_file),
        llm_provider="layer4",
        seed_demo_data=False,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)

    durable = database.create_database()
    alpha = Account(
        id="shared-account-id",
        tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        name="Alpha Manufacturing",
        industry="manufacturing",
    )
    beta = Account(
        id="shared-account-id",
        tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        name="Beta Healthcare",
        industry="healthcare",
    )

    durable.accounts.insert(alpha.id, alpha)
    durable.accounts.insert(beta.id, beta)

    assert durable.accounts.get("shared-account-id", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") == alpha
    assert durable.accounts.get("shared-account-id", tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") == beta
    assert durable.accounts.delete("shared-account-id", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") is True
    assert durable.accounts.get("shared-account-id", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") is None
    assert durable.accounts.get("shared-account-id", tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") == beta
    durable.close()


def test_database_factory_rejects_unsupported_durable_backend(monkeypatch):
    from app.core import database

    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url="postgresql://fabric:example@localhost:5432/fabric",
        llm_provider="layer4",
        seed_demo_data=False,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)

    with pytest.raises(database.UnsupportedDatabaseURL, match="supports sqlite"):
        database.create_database()


def test_production_like_settings_reject_demo_seed_data_even_with_durable_database():
    with pytest.raises(Exception, match="seed_demo_data must be false"):
        Settings(
            app_env="production",
            mock_persistence=False,
            database_url="sqlite:////var/lib/fabric_4l/api.db",
            llm_provider="layer4",
            seed_demo_data=True,
            secret_key="x" * 48,
            cors_origins=["https://app.example.com"],
        )


def test_orchestrator_execute_step_requires_layer4_delegation(monkeypatch):
    from app.services import agent_orchestrator

    calls = {}

    class FakeLayer4Client:
        provider_name = "layer4"

        def execute_step(self, *, tenant_id, run_id, step_name, tool_name):
            calls.update({
                "tenant_id": tenant_id,
                "run_id": run_id,
                "step_name": step_name,
                "tool_name": tool_name,
            })
            return {"delegated": True}

    orchestrator = agent_orchestrator.AgentOrchestrator(layer4_client=FakeLayer4Client())
    run = orchestrator.create_run(tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", workflow_type="roi")

    updated = orchestrator.execute_step(run.id, "draft", tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert calls["run_id"] == run.id
    assert updated.output["provider"] == "layer4"
    assert updated.output["layer4"] == {"delegated": True}


def test_layer4_client_raises_unavailable_on_transport_error(monkeypatch):
    from app.services.agent_orchestrator import Layer4OrchestrationClient, Layer4UnavailableError
    import httpx

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "Client", FakeClient)

    client = Layer4OrchestrationClient(base_url="http://layer4")
    with pytest.raises(Layer4UnavailableError):
        client.execute_step(tenant_id="t", run_id="r", step_name="s", tool_name=None)
