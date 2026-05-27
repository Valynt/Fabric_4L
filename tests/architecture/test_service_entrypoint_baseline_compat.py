"""Compatibility guardrails for maintained service entrypoints.

These tests are intentionally static and fail-fast: they assert that baseline
framework wiring remains present before deeper refactors land.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


SERVICE_BASELINES: dict[str, dict[str, object]] = {
    "layer1": {
        "path": "services/layer1-ingestion/src/api/main.py",
        "all_of": [
            "GovernanceMiddleware",
            "register_exception_handlers(app)",
            "RedisRateLimiter",
            "add_security_middleware",
            "governance_context",
        ],
        "any_health_marker": ["@app.get(\"/health\")", "register_health_endpoint(app"],
    },
    "layer2": {
        "path": "services/layer2-extraction/src/layer2_extraction/api/main.py",
        "all_of": [
            "create_fabric_app(",
            "register_health_endpoint(app",
            "register_exception_handlers(app)",
            "RequestContext",
            "register_fabric_auth_from_env(app",
        ],
    },
    "layer3": {
        "path": "services/layer3-knowledge/src/api/main.py",
        "all_of": [
            "add_governance_middleware",
            "add_request_id_middleware",
            "add_security_validation_middleware",
            "add_rate_limiting(app",
            "RequestValidationError",
        ],
    },
    "layer4": {
        "path": "services/layer4-agents/src/api/main.py",
        "all_of": [
            "create_fabric_app(",
            "register_health_endpoint(app",
            "register_exception_handlers(app)",
            "add_security_middleware",
            "install_metrics_middleware",
        ],
    },
    "layer5": {
        "path": "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
        "all_of": [
            "create_fabric_app(",
            "register_exception_handlers",
            "configure_structured_logging()",
            "tenant_id",
            "schema_revision",
        ],
    },
    "layer6": {
        "path": "services/layer6-benchmarks/src/api/main.py",
        "all_of": [
            "create_fabric_app(",
            "register_health_endpoint(",
            "register_exception_handlers(app)",
            "RequestContext",
            "add_security_middleware",
        ],
    },
    "api": {
        "path": "services/api/app/main.py",
        "all_of": [
            "create_fabric_app(",
            "register_health_endpoint(app",
            "EnforcementRolloutConfig(",
            "rate_limiting=EnforcementControlConfig",
            "idempotency=EnforcementControlConfig",
            "AuditMiddleware",
        ],
    },
}


@pytest.mark.parametrize("service_name,baseline", SERVICE_BASELINES.items())
def test_entrypoint_baseline_contract_markers_present(
    service_name: str, baseline: dict[str, object]
) -> None:
    """Fail fast on framework drift across middleware/security/tenant/error hooks."""
    file_path = REPO_ROOT / str(baseline["path"])
    source = file_path.read_text(encoding="utf-8")

    missing_all = [token for token in baseline.get("all_of", []) if token not in source]
    assert not missing_all, (
        f"{service_name} entrypoint drift detected in {file_path}: missing required markers {missing_all}."
    )

    any_health_marker = baseline.get("any_health_marker")
    if any_health_marker:
        assert any(token in source for token in any_health_marker), (
            f"{service_name} entrypoint drift detected in {file_path}: expected one health marker from "
            f"{any_health_marker}."
        )


def test_api_gateway_rollout_policies_remain_explicit() -> None:
    """Fail fast if API gateway stops declaring explicit rollout modes."""
    source = (REPO_ROOT / "services/api/app/main.py").read_text(encoding="utf-8")
    assert "tenant_enforcement=EnforcementControlConfig" in source
    assert "rate_limiting=EnforcementControlConfig" in source
    assert "idempotency=EnforcementControlConfig" in source


def test_all_maintained_entrypoints_are_covered() -> None:
    """Fail fast if inventory coverage drifts from maintained service list."""
    expected = {
        "services/layer1-ingestion/src/api/main.py",
        "services/layer2-extraction/src/layer2_extraction/api/main.py",
        "services/layer3-knowledge/src/api/main.py",
        "services/layer4-agents/src/api/main.py",
        "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
        "services/layer6-benchmarks/src/api/main.py",
        "services/api/app/main.py",
    }
    covered = {str(defn["path"]) for defn in SERVICE_BASELINES.values()}
    assert covered == expected
