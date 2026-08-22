from __future__ import annotations

from unittest.mock import Mock

import pytest

import layer4_agents.model_registry_client as module
from layer4_agents.model_registry_client import ModelRegistryClient, ModelSpec, RegistryUnavailable


@pytest.mark.asyncio
async def test_registry_result_is_returned_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ModelRegistryClient("https://registry.test")
    expected = ModelSpec(id="canonical", source="registry", version="1")

    async def fetch(_model_id: str) -> ModelSpec:
        return expected

    monkeypatch.setattr(client, "_fetch_from_registry", fetch)
    assert await client.get_model("requested") is expected
    assert client.get_fallback_stats()["fallback_count"] == 0


@pytest.mark.asyncio
async def test_registry_fallback_is_observable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALLBACK_MODEL", "safe-fallback")
    monkeypatch.setenv("GATEWAY_BOOTSTRAP_MODE", "true")
    warning = Mock()
    monkeypatch.setattr(module.audit_log, "warning", warning)
    client = ModelRegistryClient("https://registry.test")

    model = await client.get_model("requested")

    assert model == ModelSpec(
        id="safe-fallback",
        source="bootstrap",
        metadata={
            "requested": "requested",
            "fallback_reason": "registry_unavailable",
            "degraded": True,
        },
    )
    assert client.get_fallback_stats().model_dump() == {
        "fallback_count": 1,
        "fallback_model": "safe-fallback",
        "strict_mode": False,
        "registry_url": "https://registry.test",
    }
    warning.assert_called_once()


@pytest.mark.asyncio
async def test_registry_without_fallback_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FALLBACK_MODEL", raising=False)
    monkeypatch.delenv("GATEWAY_BOOTSTRAP_MODE", raising=False)
    error = Mock()
    monkeypatch.setattr(module.audit_log, "error", error)
    client = ModelRegistryClient()
    with pytest.raises(RegistryUnavailable):
        await client.get_model("requested")
    error.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_model_without_bootstrap_mode_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FALLBACK_MODEL", "fallback")
    monkeypatch.delenv("GATEWAY_BOOTSTRAP_MODE", raising=False)
    error = Mock()
    monkeypatch.setattr(module.audit_log, "error", error)
    with pytest.raises(RegistryUnavailable):
        await ModelRegistryClient().get_model("requested")
    error.assert_called_once()
