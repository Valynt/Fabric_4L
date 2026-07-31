from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFTEST_PATH = REPO_ROOT / "tests" / "backend_integrated" / "conftest.py"


def load_backend_validation_conftest():
    spec = importlib.util.spec_from_file_location("release_smoke_backend_conftest", CONFTEST_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_backend_validation_headers_use_signed_user_identity(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "release-smoke-jwt-secret-minimum-32-characters")
    module = load_backend_validation_conftest()
    seed_ids = module.SeedIds(
        tenant_a="00000000-0000-4000-8000-000000000001",
        tenant_b="00000000-0000-4000-8000-000000000002",
        user_admin="00000000-0000-4000-8000-000000000003",
        user_reviewer="00000000-0000-4000-8000-000000000004",
        account_id="00000000-0000-4000-8000-000000000005",
        document_id="00000000-0000-4000-8000-000000000006",
        value_pack_id="value-pack-test",
        benchmark_id="benchmark-test",
        evidence_id="evidence-test",
        formula_id="formula-test",
        crm_connection_id="crm-test",
    )

    headers = module.BackendValidationHarness(seed_ids).headers(
        tenant_id=seed_ids.tenant_b,
        user_id=seed_ids.user_reviewer,
        role="analyst",
    )

    assert "X-Service-Auth" not in headers
    assert "X-Dev-Tenant-ID" not in headers
    assert "X-Dev-User-ID" not in headers
    assert headers["X-Tenant-ID"] == seed_ids.tenant_b
    assert headers["X-User-ID"] == seed_ids.user_reviewer
    claims = jwt.decode(
        headers["Authorization"].removeprefix("Bearer "),
        "release-smoke-jwt-secret-minimum-32-characters",
        algorithms=["HS256"],
        audience="value-fabric-services",
        issuer="value-fabric-internal",
    )
    assert UUID(claims["tenant_id"]) == UUID(seed_ids.tenant_b)
    assert claims["sub"] == seed_ids.user_reviewer
    assert claims["roles"] == ["analyst"]


@pytest.mark.asyncio
async def test_seed_graph_uses_validation_auth_seed_instead_of_super_admin_tenant_route(
    monkeypatch,
):
    module = load_backend_validation_conftest()
    seed_ids = module.SeedIds(
        tenant_a="00000000-0000-4000-8000-000000000001",
        tenant_b="00000000-0000-4000-8000-000000000002",
        user_admin="00000000-0000-4000-8000-000000000003",
        user_reviewer="00000000-0000-4000-8000-000000000004",
        account_id="00000000-0000-4000-8000-000000000005",
        document_id="00000000-0000-4000-8000-000000000006",
        value_pack_id="value-pack-test",
        benchmark_id="benchmark-test",
        evidence_id="evidence-test",
        formula_id="formula-test",
        crm_connection_id="crm-test",
    )
    harness = module.BackendValidationHarness(seed_ids)
    calls: list[dict[str, object]] = []

    async def fake_request(layer, method, path, **kwargs):
        calls.append({"layer": layer, "method": method, "path": path, **kwargs})
        if path == "/v1/validation/seed/auth-context":
            return {"tenant": {"id": seed_ids.tenant_a}}, SimpleNamespace(status_code=200)
        if path == "/v1/accounts":
            return {"id": seed_ids.account_id}, SimpleNamespace(status_code=201)
        if path == "/api/v1/ingestion/sources":
            return {"source_id": seed_ids.document_id}, SimpleNamespace(status_code=201)
        raise AssertionError(f"unexpected request: {method} {path}")

    monkeypatch.setattr(harness, "request", fake_request)

    seeded = await harness.create_seed_graph()

    assert seeded["tenant"] == {"id": seed_ids.tenant_a}
    assert all(call["path"] != "/v1/tenants" for call in calls)
    seed_call = calls[0]
    assert seed_call["path"] == "/v1/validation/seed/auth-context"
    assert seed_call["json"] == {
        "tenant_id": seed_ids.tenant_a,
        "tenant_name": f"Fabric Backend Validation Tenant {module.RUN_ID}",
        "tenant_slug": f"backend-validation-{module.RUN_SLUG_SUFFIX}-a",
        "service_account_id": "backend-integrated-validation",
    }
    assert seed_call["extra_headers"] == {"X-Privileged-Reason": "validation-seed"}
