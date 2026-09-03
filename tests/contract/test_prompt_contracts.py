"""Contract tests for agent-registry prompt metadata.

Validates every prompt contract JSON:
- conforms to contracts/agent-registry/schemas/prompt.schema.json
- the referenced prompt file exists and its SHA-256 matches content_hash
- declared eval baselines point to existing files with the expected shape
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from .schema_assertions import assert_matches_schema


CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "agent-registry"
PROMPTS_DIR = CONTRACTS_DIR / "prompts"
SCHEMA_PATH = CONTRACTS_DIR / "schemas" / "prompt.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_from_contract(rel_path: str, contract_path: Path) -> Path:
    return (contract_path.parent / rel_path).resolve()


def _inline_external_refs(schema: dict, base_dir: Path) -> dict:
    """Resolve top-level relative $ref files into an inline schema.

    schema_assertions only supports '#/...' internal refs, so agent-registry
    schemas that reference ./base-contract.schema.json must be inlined before
    validation.
    """
    result = dict(schema)
    inlined: list[dict] = []

    for sub in result.get("allOf", []):
        ref = sub.get("$ref")
        if isinstance(ref, str) and not ref.startswith("#/"):
            ref_path = (base_dir / ref).resolve()
            referenced = _load_json(ref_path)
            referenced.pop("$schema", None)
            referenced.pop("$id", None)
            inlined.append(referenced)
        else:
            inlined.append(sub)

    result["allOf"] = inlined
    return result


@pytest.fixture(scope="module")
def prompt_schema() -> dict:
    schema = _load_json(SCHEMA_PATH)
    return _inline_external_refs(schema, SCHEMA_PATH.parent)


@pytest.fixture(scope="module")
def prompt_contracts() -> list[Path]:
    return sorted(PROMPTS_DIR.glob("*.json"))


@pytest.mark.contract_static
def test_prompt_contracts_are_present(prompt_contracts: list[Path]) -> None:
    assert prompt_contracts, f"No prompt contract JSONs found in {PROMPTS_DIR}"


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(PROMPTS_DIR.glob("*.json")))
def test_prompt_contract_matches_schema(contract_path: Path, prompt_schema: dict) -> None:
    contract = _load_json(contract_path)
    assert_matches_schema(contract, prompt_schema)


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(PROMPTS_DIR.glob("*.json")))
def test_prompt_contract_referenced_file_exists_and_hash_matches(contract_path: Path) -> None:
    contract = _load_json(contract_path)
    rel_path = contract["prompt_path"]
    prompt_file = _resolve_from_contract(rel_path, contract_path)

    assert prompt_file.exists(), (
        f"Prompt file referenced by {contract_path.name} does not exist: {prompt_file}"
    )

    # content_hash is optional-but-validated (schema does not require it and the
    # CI gate warns rather than fails when missing). Only verify the hash when a
    # contract has declared one, so tests stay aligned with the rollout policy.
    content_hash = contract.get("content_hash")
    if content_hash is None:
        return

    digest = hashlib.sha256(prompt_file.read_bytes()).hexdigest()
    assert digest == content_hash, (
        f"Content hash mismatch for {contract_path.name}. "
        f"Expected {content_hash}, computed {digest}. "
        "Bump the prompt version and update the changelog if this change is intentional."
    )


@pytest.mark.contract_static
@pytest.mark.parametrize("contract_path", sorted(PROMPTS_DIR.glob("*.json")))
def test_prompt_contract_eval_baseline_points_to_existing_file(contract_path: Path) -> None:
    contract = _load_json(contract_path)
    # eval_baseline is optional-but-validated (schema does not require it and the
    # CI gate warns rather than fails when missing). Only verify the baseline when
    # a contract has declared one, so tests stay aligned with the rollout policy.
    baseline = contract.get("eval_baseline")
    if baseline is None:
        return

    rel_path = baseline.get("baseline_file")
    assert rel_path, f"{contract_path.name} eval_baseline missing baseline_file"

    baseline_path = _resolve_from_contract(rel_path, contract_path)
    assert baseline_path.exists(), (
        f"Eval baseline file referenced by {contract_path.name} does not exist: {baseline_path}"
    )

    artifact = _load_json(baseline_path)
    required = {"prompt_id", "version", "content_hash", "score", "eval_set_id", "recorded_at"}
    missing = required - set(artifact)
    assert not missing, (
        f"Eval baseline {baseline_path} missing required fields: {sorted(missing)}"
    )

    assert artifact["prompt_id"] == contract["id"]
    assert artifact["version"] == contract["version"]
    assert artifact["content_hash"] == contract.get("content_hash")
