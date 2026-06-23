"""Suite 8 — Release-Environment Smoke Validation."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.release_smoke]


@pytest.mark.asyncio
async def test_release_environment_health_endpoints(backend):
    health = {}
    for layer in ("l1", "l2", "l3", "l4", "l5", "l6"):
        path, body = await backend.first_healthy(layer)
        health[layer] = {"path": path, "body": body}
    assert set(health) == {"l1", "l2", "l3", "l4", "l5", "l6"}
    assert all(value["path"] for value in health.values()), health
    _assert_release_traceability_and_no_skip_guard()


@pytest.mark.asyncio
async def test_release_environment_auth_flow(backend, seed_ids):
    profile, response = await backend.request("l4", "GET", "/v1/auth/session", expected=(200, 401, 403))
    if response.status_code == 200:
        assert seed_ids.user_admin in str(profile) or "user" in str(profile).lower(), profile
    else:
        assert response.status_code in {401, 403}, "Release auth smoke must fail closed when no session/token is present."


@pytest.mark.asyncio
async def test_release_environment_account_creation(backend, seed_ids):
    seeded = await backend.create_seed_graph()
    assert seed_ids.account_id in str(seeded)
    reloaded = await backend.assert_persisted("l4", f"/v1/accounts/{seed_ids.account_id}", seed_ids.account_id)
    assert seed_ids.tenant_a in str(reloaded) or seed_ids.account_id in str(reloaded)


@pytest.mark.asyncio
async def test_release_environment_ingestion_smoke(backend, seed_ids):
    await backend.create_seed_graph()
    source = await backend.assert_persisted("l1", f"/api/v1/ingestion/sources/{backend.seed_source_id}", backend.seed_source_id)
    assert seed_ids.account_id in str(source)


@pytest.mark.asyncio
async def test_release_environment_calculator_smoke(backend, seed_ids):
    await backend.create_seed_graph()
    result, _ = await backend.request(
        "l4",
        "POST",
        "/v1/analysis/roi",
        json={"account_id": seed_ids.account_id, "variables": {"annual_benefit": 500000, "implementation_cost": 125000}, "formula_id": seed_ids.formula_id},
        expected=(200, 201),
        extra_headers={"X-Validation-Mode": "smoke", "X-Fabric-Smoke-Test": "true"},
    )
    assert any(token in str(result).lower() for token in ("roi", "payback", "calculation", "result")), result


@pytest.mark.asyncio
async def test_release_environment_business_case_generation_smoke(backend, seed_ids):
    await backend.create_seed_graph()
    case, _ = await backend.request(
        "l4",
        "POST",
        "/v1/cases",
        json={"account_id": seed_ids.account_id, "evidence_ids": [seed_ids.evidence_id], "approval_status": "draft"},
        expected=(200, 201, 202),
        extra_headers={"X-Validation-Mode": "smoke", "X-Fabric-Smoke-Test": "true"},
    )
    assert seed_ids.account_id in str(case)
    assert any(token in str(case).lower() for token in ("case", "business", "draft")), case


@pytest.mark.asyncio
async def test_release_environment_tenant_isolation_smoke(backend, seed_ids):
    await backend.create_seed_graph()
    await backend.assert_cross_tenant_denied("l4", f"/v1/accounts/{seed_ids.account_id}")


@pytest.mark.asyncio
async def test_release_environment_export_gate_smoke(backend, seed_ids):
    await backend.create_seed_graph()
    case, _ = await backend.request(
        "l4",
        "POST",
        "/v1/cases",
        json={"account_id": seed_ids.account_id, "approval_status": "draft"},
        expected=(200, 201, 202),
        extra_headers={"X-Validation-Mode": "smoke", "X-Fabric-Smoke-Test": "true"},
    )
    case_id = case.get("id") or case.get("case_id") or seed_ids.account_id
    await backend.request("l4", "GET", f"/v1/cases/{case_id}/export", expected=(401, 403, 409, 423))


def _assert_release_traceability_and_no_skip_guard() -> None:
    matrix = Path("docs/validation/backend_integrated/backend_integrated_traceability_matrix.md")
    assert matrix.exists(), "Backend-integrated validation must have a committed traceability matrix."
    suite_dir = Path("tests/backend_integrated")
    forbidden_tokens = (
        "pytest" + ".skip",
        "@pytest.mark." + "skip",
        "@pytest.mark." + "skipif",
        "@pytest.mark." + "xfail",
        "unittest" + ".skip",
    )
    offenders: list[str] = []
    for path in sorted(suite_dir.glob("test_*.py")):
        text = path.read_text()
        for token in forbidden_tokens:
            if token in text:
                offenders.append(f"{path}:{token}")
    assert not offenders, "Backend-integrated production gates must not be skipped or xfailed: " + ", ".join(offenders)
    makefile = Path("Makefile").read_text()
    assert "test-backend-integrated-validation" in makefile
    assert "test-backend-integrated-release-smoke" in makefile
