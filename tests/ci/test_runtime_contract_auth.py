"""Static contracts for authenticated live runtime-contract requests."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr-checks.yml"
RUNTIME_TEST = REPO_ROOT / "tests" / "contract" / "test_layer_integration.py"
LAYER3_MAIN = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "main.py"
FULL_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.full.yml"


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
    assert '"use_case_ids": [' in source
    assert '"entity_type": "Company"' in source
    assert '"rdf_data":' in source
    assert '"entities": [' not in source
    assert '"source_id":' in source
    assert '"extraction_job_id":' in source


def test_layer3_governance_uses_the_runtime_redis_service() -> None:
    source = LAYER3_MAIN.read_text(encoding="utf-8")
    compose = FULL_COMPOSE.read_text(encoding="utf-8")
    layer3 = compose.split("\n  layer3-knowledge:", 1)[1].split("\n  layer4-agents:", 1)[0]

    assert "redis.asyncio" in source
    assert "RedisRateLimiter" in source
    assert "rate_limiter=redis_rate_limiter" in source
    assert "CACHE_REDIS_URL=" in layer3


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
