"""Contracts for fail-safe OpenAPI contract-stack execution."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-openapi-contract-tests.sh"
COMPOSE = ROOT / "infra" / "compose" / "docker-compose.backend-integrated.yml"


def test_contract_runner_preserves_failure_diagnostics_and_cleans_up() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert "trap cleanup EXIT" in script
    assert 'docker compose -f "$COMPOSE_FILE" ps --all || true' in script
    assert 'docker compose -f "$COMPOSE_FILE" logs --no-color || true' in script
    assert 'docker compose -f "$COMPOSE_FILE" down -v || true' in script
    assert 'exit "$status"' in script


def test_contract_runner_uses_one_canonical_compose_file() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert 'COMPOSE_FILE="infra/compose/docker-compose.backend-integrated.yml"' in script
    assert "docker-compose.backend-integrated.yml up" not in script


def test_contract_runner_executes_static_and_live_l1_l6_contracts() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert '-m "contract_static or contract_static_no_service"' in script
    assert "RUN_RUNTIME_CONTRACTS=1" in script
    for layer in range(1, 7):
        assert f"LAYER{layer}_API_URL=http://localhost:800{layer}" in script


def test_layer3_contract_environment_sets_cache_redis_url() -> None:
    """Layer 3 must not fall back to the settings default for CACHE_REDIS_URL.

    Layer 3 settings read ``cache_redis_url`` (alias ``CACHE_REDIS_URL``) for its
    cache and governance/rate-limiter Redis clients, defaulting to
    ``redis://localhost:6379/0``. Inside the container that points at the container
    itself, so the fail-closed tenant kill switch cannot reach Redis and every
    tenant-scoped endpoint returns 503 ``tenant_status_unavailable`` (the
    ``Run Contract Tests`` gate failure). Every stack that runs runtime contract
    tests against this service must therefore define ``CACHE_REDIS_URL`` pointing
    at the same Redis reachable from the container as ``REDIS_URL``.
    """
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    layer3_env = compose["services"]["layer3"]["environment"]

    redis_url = layer3_env["REDIS_URL"]
    assert redis_url.startswith("redis://")
    # No localhost loopback: inside the container it is not the host's Redis.
    assert "localhost" not in redis_url
    assert layer3_env["CACHE_REDIS_URL"] == redis_url


def test_layer4_contract_service_mounts_all_imported_source_packages() -> None:
    compose = (ROOT / "infra" / "compose" / "docker-compose.contract.yml").read_text(
        encoding="utf-8"
    )
    layer4 = compose.split("\n  layer4:", 1)[1].split("\n  layer5:", 1)[0]

    assert "PYTHONPATH: /app:/app/src" in layer4
    assert 'ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT: "true"' in layer4
    assert "../../packages/platform-contract/src/python/canonical:/app/canonical:ro" in layer4
    assert "layer4_agents.api.main:app" in (
        ROOT / "services" / "layer4-agents" / "Dockerfile"
    ).read_text(encoding="utf-8")
