"""Contract tests for agent-registry operating contracts.

Validates every operating contract JSON:
- conforms to contracts/agent-registry/schemas/agent-contract.schema.json
- the referenced file exists and matches the declared agent_type
- every declared tool appears in the central tool registry
- required capabilities are a subset of the agent's manifest capabilities
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .schema_assertions import assert_matches_schema
from .test_prompt_contracts import _inline_external_refs, _load_json


CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "agent-registry"
AGENTS_DIR = CONTRACTS_DIR / "agents"
SCHEMA_PATH = CONTRACTS_DIR / "schemas" / "agent-contract.schema.json"
TOOL_REGISTRY_PATH = CONTRACTS_DIR / "tools" / "manifest.json"
MANIFEST_PATH = AGENTS_DIR / "manifest.json"


@pytest.fixture(scope="module")
def agent_contract_schema() -> dict:
    schema = _load_json(SCHEMA_PATH)
    return _inline_external_refs(schema, SCHEMA_PATH.parent)


@pytest.fixture(scope="module")
def agent_contracts() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.contract.json"))


@pytest.fixture(scope="module")
def tool_names() -> set[str]:
    registry = _load_json(TOOL_REGISTRY_PATH)
    return {tool["name"] for tool in registry.get("tools", [])}


@pytest.fixture(scope="module")
def manifest_agents() -> dict[str, dict]:
    manifest = _load_json(MANIFEST_PATH)
    return {agent["agent_type"]: agent for agent in manifest.get("agents", [])}


@pytest.mark.contract_static
def test_agent_contracts_are_present(agent_contracts: list[Path]) -> None:
    assert agent_contracts, f"No operating contract JSONs found in {AGENTS_DIR}"


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(AGENTS_DIR.glob("*.contract.json")))
def test_agent_contract_matches_schema(contract_path: Path, agent_contract_schema: dict) -> None:
    contract = _load_json(contract_path)
    assert_matches_schema(contract, agent_contract_schema)


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(AGENTS_DIR.glob("*.contract.json")))
def test_agent_contract_references_valid_agent_type(
    contract_path: Path, manifest_agents: dict[str, dict]
) -> None:
    contract = _load_json(contract_path)
    agent_type = contract["agent_type"]
    assert agent_type in manifest_agents, (
        f"{contract_path.name} declares unknown agent_type {agent_type}; "
        f"expected one of {sorted(manifest_agents)}"
    )


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(AGENTS_DIR.glob("*.contract.json")))
def test_agent_contract_manifest_points_to_contract_file(contract_path: Path) -> None:
    contract = _load_json(contract_path)
    agent_type = contract["agent_type"]
    manifest = _load_json(MANIFEST_PATH)
    manifest_agent = next(
        (a for a in manifest.get("agents", []) if a["agent_type"] == agent_type), None
    )
    assert manifest_agent is not None, f"No manifest entry for {agent_type}"
    assert "operating_contract_path" in manifest_agent, (
        f"Manifest entry for {agent_type} missing operating_contract_path"
    )
    expected_path = (AGENTS_DIR / manifest_agent["operating_contract_path"]).resolve()
    assert expected_path == contract_path.resolve(), (
        f"Manifest operating_contract_path for {agent_type} does not point to "
        f"{contract_path.name}: {expected_path}"
    )


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(AGENTS_DIR.glob("*.contract.json")))
def test_agent_contract_tools_are_in_registry(
    contract_path: Path, tool_names: set[str]
) -> None:
    contract = _load_json(contract_path)
    unknown = set(contract.get("tools", [])) - tool_names
    assert not unknown, (
        f"{contract_path.name} references unknown tools: {sorted(unknown)}; "
        f"valid tools are {sorted(tool_names)}"
    )


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(AGENTS_DIR.glob("*.contract.json")))
def test_agent_contract_eval_capabilities_are_declared_capabilities(
    contract_path: Path, manifest_agents: dict[str, dict]
) -> None:
    contract = _load_json(contract_path)
    agent_type = contract["agent_type"]
    manifest_agent = manifest_agents[agent_type]
    allowed_capabilities = set(manifest_agent.get("capabilities", []))
    required = set(contract.get("eval_target", {}).get("required_capabilities", []))
    unknown = required - allowed_capabilities
    assert not unknown, (
        f"{contract_path.name} eval_target.required_capabilities contains "
        f"capabilities not declared in manifest for {agent_type}: {sorted(unknown)}"
    )
