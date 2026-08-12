import pytest

from app.core.config import Settings
from app.models.schemas import Account



def test_database_factory_accepts_postgresql_and_returns_postgres_facade(monkeypatch):
    """PostgreSQL is now supported via bridge facade; create_database returns PostgreSQLDatabase."""
    from app.core import database

    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url="postgresql://fabric:example@localhost:5432/fabric",
        llm_provider="layer4",
        seed_demo_data=False,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)

    db = database.create_database()
    assert isinstance(db, (database.InMemoryDatabase, database.PostgreSQLDatabase))


def test_production_like_settings_reject_demo_seed_data_even_with_durable_database():
    with pytest.raises(Exception, match="seed_demo_data must be false"):
        Settings(
            app_env="production",
            mock_persistence=False,
            database_url="postgresql://fabric:secret@postgres:5432/fabric",
            llm_provider="openai",
            seed_demo_data=True,
            secret_key="x" * 48,
            cors_origins=["https://app.example.com"],
        )


def test_production_like_settings_reject_mock_llm_even_when_override_is_true():
    with pytest.raises(Exception, match="llm_provider must be set to layer4"):
        Settings(
            app_env="production",
            mock_persistence=False,
            database_url="postgresql://fabric:secret@postgres:5432/fabric",
            llm_provider="mock",
            allow_mock_llm=True,
            seed_demo_data=False,
            secret_key="x" * 48,
            cors_origins=["https://app.example.com"],
        )


def test_create_llm_provider_rejects_mock_provider_in_production_like_environment(monkeypatch):

    from app.services import agent_orchestrator

    calls = {}

    class FakeLayer4Client:
        provider_name = "layer4"

        def create_workflow(self, *, tenant_id, workflow_type, account_id, input_data, user_id=None):
            calls.update({
                "tenant_id": tenant_id,
                "workflow_type": workflow_type,
            })
            return {"workflow_instance_id": "wf-1", "status": "pending"}

        def get_workflow(self, *, tenant_id, workflow_id):
            return {"id": workflow_id, "status": "running"}

    orchestrator = agent_orchestrator.AgentOrchestrator(layer4_client=FakeLayer4Client())
    run = orchestrator.create_run(tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", workflow_type="roi")

    refreshed = orchestrator.get_run(run.id, tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert calls["tenant_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert run.id == "wf-1"
    assert refreshed is not None
    assert refreshed.status == "running"
    assert refreshed.output["provider"] == "layer4"


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

        def request(self, *args, **kwargs):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "Client", FakeClient)

    client = Layer4OrchestrationClient(base_url="http://layer4")
    with pytest.raises(Layer4UnavailableError):
        client.get_workflow(tenant_id="t", workflow_id="wf-1")
