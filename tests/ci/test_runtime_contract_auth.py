"""Static contracts for authenticated live runtime-contract requests."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr-checks.yml"
RUNTIME_TEST = REPO_ROOT / "tests" / "contract" / "test_layer_integration.py"


def _runtime_suite_environment() -> dict[str, str]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["runtime-contract-checks"]["steps"]
    step = next(item for item in steps if item.get("name") == "Run runtime contract marker suite")
    return step["env"]


def test_runtime_suite_receives_valid_service_identity() -> None:
    environment = _runtime_suite_environment()

    assert len(environment["SERVICE_AUTH_SECRET"]) >= 32
    assert environment["RUNTIME_CONTRACT_TENANT_ID"] == "00000000-0000-4000-8000-000000000001"


def test_runtime_contract_uses_canonical_authenticated_workflow_route() -> None:
    source = RUNTIME_TEST.read_text(encoding="utf-8")

    assert '"X-Service-Auth": SERVICE_AUTH_SECRET' in source
    assert 'f"{L4_URL}/v1/workflows"' in source
    assert 'f"{L4_URL}/v1/workflows/ingestion"' not in source


def test_runtime_diagnostics_follow_the_runtime_suite() -> None:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["runtime-contract-checks"]["steps"]
    names = [item.get("name") for item in steps]

    assert names.index("Capture runtime contract service diagnostics") > names.index(
        "Run runtime contract marker suite"
    )


def test_runtime_job_provides_every_required_compose_input() -> None:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    environment = document["jobs"]["runtime-contract-checks"]["env"]
    compose = (REPO_ROOT / "infra" / "compose" / "docker-compose.full.yml").read_text(
        encoding="utf-8"
    )
    import re

    required = set(re.findall(r"\$\{([A-Z0-9_]+):\?", compose))
    assert required <= set(environment)
