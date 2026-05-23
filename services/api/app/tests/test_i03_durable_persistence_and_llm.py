import pytest

from app.core.config import Settings
from app.models.schemas import Account



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

    with pytest.raises(
        database.UnsupportedDatabaseURL,
        match="PostgreSQL persistence is required but not yet implemented",
    ):
        database.create_database()


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
    with pytest.raises(Exception, match="llm_provider=mock is disabled"):
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
