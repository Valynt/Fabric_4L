import sys
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.models.schemas import Account


def test_database_factory_rejects_unsupported_durable_backend(monkeypatch):
    from app.core import database

    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url="postgresql://fabric:example@localhost:5432/fabric",
        llm_provider="mock",
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
    from app.services import agent_orchestrator

    settings = SimpleNamespace(
        llm_provider="mock",
        llm_model=None,
        is_production_like=True,
    )
    monkeypatch.setattr(agent_orchestrator, "get_settings", lambda: settings)

    with pytest.raises(agent_orchestrator.ProductionLLMNotConfigured, match="Mock LLM provider"):
        agent_orchestrator.create_llm_provider()


def test_create_llm_provider_wires_openai_adapter_without_calling_network(monkeypatch):
    from app.services import agent_orchestrator

    captured = {}

    class FakeOpenAI:
        def __init__(self, api_key, timeout):
            captured["api_key"] = api_key
            captured["timeout"] = timeout

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = SimpleNamespace(
        llm_provider="openai",
        llm_model="gpt-test",
        is_production_like=True,
    )
    monkeypatch.setattr(agent_orchestrator, "get_settings", lambda: settings)

    provider = agent_orchestrator.create_llm_provider()

    assert provider.provider_name == "openai"
    assert provider.model == "gpt-test"
    assert captured == {"api_key": "test-key", "timeout": 60.0}
