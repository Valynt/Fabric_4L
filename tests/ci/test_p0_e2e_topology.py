"""Static contracts for the required P0 backend-integrated topology."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr-checks.yml"
COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.e2e.yml"


def test_p0_stack_provides_real_layer1_and_layer4_services() -> None:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = document["services"]

    assert {"layer1", "layer1-migrate", "layer4", "migrate"} <= services.keys()
    assert services["layer1"]["ports"] == ["8001:8000"]
    assert (
        services["layer1"]["depends_on"]["layer1-migrate"]["condition"]
        == "service_completed_successfully"
    )
    assert (
        services["layer1-migrate"]["depends_on"]["migrate"]["condition"]
        == "service_completed_successfully"
    )


def test_p0_frontend_routes_layer1_directly_and_defaults_to_layer4() -> None:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    environment = document["jobs"]["p0-e2e-gate"]["env"]

    assert environment["VITE_AUTH_PROVIDER"] == "legacy"
    assert environment["VITE_PROXY_DEBUG_DIRECT_LAYERS"] == "true"
    assert environment["VITE_PROXY_L1_URL"] == "http://localhost:8001"
    assert environment["VITE_PROXY_L4_URL"] == "http://localhost:8004"
    assert environment["VITE_PROXY_API_GATEWAY_URL"] == "http://localhost:8004"


def test_p0_seed_uses_the_server_privileged_reason() -> None:
    seed_constants = (
        REPO_ROOT / "apps" / "web" / "e2e" / "fixtures" / "seed-constants.ts"
    ).read_text(encoding="utf-8")

    assert "E2E_SEED_PRIVILEGED_REASON = 'validation-seed'" in seed_constants
