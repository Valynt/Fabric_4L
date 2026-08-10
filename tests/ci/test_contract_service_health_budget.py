"""Regression contract for slow cold-start contract services."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_CHECK = REPO_ROOT / "scripts" / "check-contract-services.py"


def test_contract_service_health_budget_allows_cold_layer4_startup() -> None:
    namespace: dict[str, object] = {"__name__": "contract_health_check"}
    exec(compile(HEALTH_CHECK.read_bytes(), str(HEALTH_CHECK), "exec"), namespace)

    assert namespace["MAX_RETRIES"] * namespace["DELAY"] >= 120
