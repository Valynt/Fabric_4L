"""Unit tests for the agent operating-contract loader."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from layer4_agents.agents import operating_contract as operating_contract_module
from layer4_agents.agents.base import BaseAgent
from layer4_agents.agents.operating_contract import (
    AgentOperatingContract,
    _default_manifest_path,
    load_operating_contract,
)


# Re-export exception raised by BaseAgent when strict-mode loading fails.
from layer4_agents.agents.base import AgentExecutionError


class _TestAgent(BaseAgent):
    """Concrete agent subclass used only for contract-loading tests."""

    agent_type = "AuditOrchestrator"

    def get_capabilities(self) -> list[Any]:
        return []

    async def execute(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"result": "ok"}


class _UnknownAgent(BaseAgent):
    """Agent with no registered operating contract."""

    agent_type = "UnknownAgent"

    def get_capabilities(self) -> list[Any]:
        return []

    async def execute(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"result": "ok"}


def _write_contract(tmp_path: Path, name: str, **overrides: Any) -> Path:
    """Write a complete operating-contract JSON and return its path.

    ``overrides`` replace top-level keys in the base payload so tests can vary
    one field at a time without repeating the full contract literal.
    """
    payload: dict[str, Any] = {
        "$schema": "../../schemas/agent-contract.schema.json",
        "kind": "agent_contract",
        "apiVersion": "v1",
        "id": name,
        "version": "1.0.0",
        "agent_type": name,
        "risk_class": "low",
        "tools": ["search_web"],
        "memory_scopes": ["working"],
        "permissions": {
            "read_paths": ["contracts/"],
            "write_paths": [],
            "network": ["internal_only"],
            "isolation_level": "tenant_strict",
        },
        "eval_target": {"suite_id": "default-suite", "min_score": 0.5},
    }
    payload.update(overrides)
    path = tmp_path / f"{name}.contract.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_operating_contract_by_manifest() -> None:
    """Load a known agent contract from the canonical registry manifest.

    The canonical registry is an explicit dependency of this test: the manifest
    path is resolved and asserted up front so a missing or renamed registry
    entry fails here with a clear message rather than surfacing as an opaque
    loader error.
    """
    manifest_path = _default_manifest_path()
    assert manifest_path.exists(), f"canonical agent registry manifest missing: {manifest_path}"

    contract = load_operating_contract("AuditOrchestrator", manifest_path=manifest_path)
    assert contract is not None
    assert contract.agent_type == "AuditOrchestrator"
    assert isinstance(contract.tools, list)
    assert all(isinstance(t, str) for t in contract.tools)
    assert isinstance(contract.memory_scopes, list)
    assert all(isinstance(s, str) for s in contract.memory_scopes)
    assert isinstance(contract.permissions.read_paths, list)
    assert isinstance(contract.permissions.write_paths, list)
    assert isinstance(contract.permissions.isolation_level, str) and contract.permissions.isolation_level
    assert isinstance(contract.eval_target.suite_id, str) and contract.eval_target.suite_id


def test_env_override_contract_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AGENT_OPERATING_CONTRACT_PATH__<agent_type> overrides the manifest lookup."""
    custom = _write_contract(
        tmp_path,
        "CustomAgent",
        id="custom-override",
        version="1.2.3",
        eval_target={"suite_id": "custom-suite", "min_score": 0.5},
    )

    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH__CustomAgent", str(custom))
    contract = load_operating_contract("CustomAgent")
    assert contract is not None
    assert contract.id == "custom-override"
    assert contract.version == "1.2.3"
    assert contract.tools == ["search_web"]


def test_generic_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic AGENT_OPERATING_CONTRACT_PATH applies to any agent type."""
    custom = _write_contract(
        tmp_path,
        "AuditOrchestrator",
        id="audit-generic-override",
        version="9.9.9",
        risk_class="critical",
        tools=[],
        memory_scopes=[],
        permissions={"read_paths": [], "write_paths": [], "network": [], "isolation_level": "tenant_strict"},
        eval_target={"suite_id": "x", "min_score": 0.0},
    )

    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH", str(custom))
    contract = load_operating_contract("AuditOrchestrator")
    assert contract is not None
    assert contract.id == "audit-generic-override"
    assert contract.version == "9.9.9"


def test_specific_env_beats_generic_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Agent-specific override wins over the generic path override."""
    overrides: dict[str, Any] = {
        "risk_class": "critical",
        "tools": [],
        "memory_scopes": [],
        "permissions": {"read_paths": [], "write_paths": [], "network": [], "isolation_level": "tenant_strict"},
        "eval_target": {"suite_id": "x", "min_score": 0.0},
    }
    generic = _write_contract(
        tmp_path, "AuditOrchestrator", id="audit-generic", version="1.0.0", **overrides
    )
    specific = _write_contract(
        tmp_path, "specific", agent_type="AuditOrchestrator", id="audit-specific", version="2.0.0", **overrides
    )

    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH", str(generic))
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH__AuditOrchestrator", str(specific))
    contract = load_operating_contract("AuditOrchestrator")
    assert contract is not None
    assert contract.version == "2.0.0"


def test_strict_mode_missing_agent_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strict mode fails closed for unregistered agents."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "strict")
    with pytest.raises(Exception):
        load_operating_contract("DefinitelyNotRegistered")


def test_strict_mode_package_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strict mode raises when the contract package cannot be imported."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "strict")
    monkeypatch.setattr(operating_contract_module, "AgentOperatingContract", None)
    with pytest.raises(RuntimeError):
        load_operating_contract("AuditOrchestrator")


def test_warn_mode_package_unavailable_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Warning mode logs and returns None when the contract package is unavailable."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "warn")
    monkeypatch.setattr(operating_contract_module, "AgentOperatingContract", None)
    caplog.set_level(logging.WARNING)
    contract = load_operating_contract("AuditOrchestrator")
    assert contract is None
    assert "package unavailable" in caplog.text


def test_warn_mode_missing_agent_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Warning mode returns None and logs a warning for unknown agents."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "warn")
    caplog.set_level(logging.WARNING)
    contract = load_operating_contract("DefinitelyNotRegistered")
    assert contract is None
    assert "Could not load operating contract" in caplog.text


def test_invalid_contract_schema_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A contract that does not satisfy the Pydantic model raises an error in strict mode."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "strict")
    bad = tmp_path / "BadAgent.contract.json"
    bad.write_text(
        json.dumps(
            {
                "kind": "agent_contract",
                "apiVersion": "v1",
                "id": "bad",
                # Missing required fields on purpose.
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH__BadAgent", str(bad))
    with pytest.raises(Exception):
        load_operating_contract("BadAgent")


def test_base_agent_loads_operating_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BaseAgent._load_operating_contract() loads the contract into self.contract."""
    custom = _write_contract(tmp_path, "AuditOrchestrator")
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH__AuditOrchestrator", str(custom))

    agent = _TestAgent()
    agent._load_operating_contract()
    assert agent.contract is not None
    assert agent.contract.agent_type == "AuditOrchestrator"
    assert "operating_contract" in agent.state.metadata
    tools = agent.state.metadata["operating_contract"]["tools"]
    assert isinstance(tools, list)
    assert all(isinstance(t, str) for t in tools)


def test_initialize_loads_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public async initialize() loads the ABOM manifest and operating contract."""
    manifest = BaseAgent._default_manifest_dir() / "orchestration_controller.abom.json"
    assert manifest.exists(), f"ABOM manifest missing: {manifest}"
    custom = _write_contract(tmp_path, "AuditOrchestrator")
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_PATH__AuditOrchestrator", str(custom))

    agent = _TestAgent(config={"manifest_path": str(manifest)})
    asyncio.run(agent.initialize())

    assert agent.abom is not None
    assert "abom_hash" in agent.state.metadata
    assert agent.contract is not None
    assert agent.contract.agent_type == "AuditOrchestrator"
    assert "operating_contract" in agent.state.metadata
    tools = agent.state.metadata["operating_contract"]["tools"]
    assert isinstance(tools, list)
    assert all(isinstance(t, str) for t in tools)


def test_base_agent_strict_mode_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """BaseAgent raises AgentExecutionError in strict mode for an unknown agent."""
    monkeypatch.setenv("AGENT_OPERATING_CONTRACT_MODE", "strict")
    agent = _UnknownAgent()
    with pytest.raises(AgentExecutionError):
        agent._load_operating_contract()
