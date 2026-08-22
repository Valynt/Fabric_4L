from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from layer4_agents.config.settings import Settings
from layer4_agents.services.governed_llm_client import (
    GovernedLLMClient,
    ModelResolutionError,
)


@pytest.mark.parametrize("provider", ["together", "openai", "anthropic", " OpenAI "])
def test_supported_llm_provider_is_normalized(provider: str) -> None:
    settings = Settings(llm_provider=provider)
    assert settings.llm_provider in {"together", "openai", "anthropic"}


def test_unknown_llm_provider_is_rejected_during_settings_construction() -> None:
    with pytest.raises(ValidationError, match="implicit provider fallback is prohibited"):
        Settings(llm_provider="typo-provider")


def test_unresolvable_task_model_fails_closed(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "runtime.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "models": {"openai": {"conversation": "gpt-test"}},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LAYER4_LLM_PROVIDER", raising=False)
    client = GovernedLLMClient(
        provider=object(),
        provider_name="openai",
        runtime_config_path=config,
    )

    assert client._resolve_model("conversation") == "gpt-test"
    with pytest.raises(ModelResolutionError, match="No model configured"):
        client._resolve_model("unregistered-task")


def test_governed_llm_client_normalizes_provider_whitespace(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "runtime.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "models": {"openai": {"conversation": "gpt-test"}},
                }
            }
        ),
        encoding="utf-8",
    )
    # Test 1: provider_name with whitespace
    client = GovernedLLMClient(
        provider=object(),
        provider_name=" OpenAI ",
        runtime_config_path=config,
    )
    assert client._provider_name == "openai"
    monkeypatch.delenv("LAYER4_LLM_PROVIDER", raising=False)
    assert client._resolve_model("conversation") == "gpt-test"

    # Test 2: LAYER4_LLM_PROVIDER env var with whitespace
    monkeypatch.setenv("LAYER4_LLM_PROVIDER", " OpenAI ")
    assert client._resolve_model("conversation") == "gpt-test"

