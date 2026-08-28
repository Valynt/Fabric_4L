"""Contracts for fail-safe OpenAPI contract-stack execution."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-openapi-contract-tests.sh"


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
